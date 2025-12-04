
import arcpy
import json
import os


class Toolbox(object):
    def __init__(self):
        self.label = "Ward Tools"
        self.alias = "wards"
        self.tools = [WardJSONToFeatures]


class WardJSONToFeatures(object):
    def __init__(self):
        self.label = "Ward JSON to Features"
        self.description = (
            "Converts a ward JSON file containing WKT geometries in 'the_geom' "
            "into a polygon (or point) feature class with generic attribute fields."
        )

    def getParameterInfo(self):
        """Define parameters for the tool UI."""

        in_json = arcpy.Parameter(
            displayName="Input Ward JSON File",
            name="in_json",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        in_json.filter.list = ["json"]

        out_fc = arcpy.Parameter(
            displayName="Output Feature Class",
            name="out_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        return [in_json, out_fc]

    def execute(self, parameters, messages):
        """Main execution code for the ward tool."""

        in_json = parameters[0].valueAsText
        out_fc = parameters[1].valueAsText

        messages.addMessage(f"Reading ward JSON: {in_json}")
        messages.addMessage(f"Creating feature class: {out_fc}")

        with open(in_json, "r", encoding="utf-8") as f:
            j = json.load(f)

        data = j["data"]
        meta = j["meta"]
        columns = meta["view"]["columns"]

        if not data:
            raise RuntimeError("JSON 'data' array is empty.")

        geom_index = None
        for i, col in enumerate(columns):
            if col["name"] == "the_geom":
                geom_index = i
                break

        if geom_index is None:
            raise RuntimeError("Could not find 'the_geom' column in meta['view']['columns'].")

        messages.addMessage(f"'the_geom' index: {geom_index}")

        sample_wkt = data[0][geom_index]
        up = str(sample_wkt).strip().upper()

        if "POLYGON" in up:
            geom_type = "POLYGON"
        elif up.startswith("POINT"):
            geom_type = "POINT"
        else:
            raise RuntimeError(f"Unrecognized WKT geometry type in the_geom: {sample_wkt[:40]}")

        messages.addMessage(f"Detected geometry type: {geom_type}")

        fields = []         
        field_lookup = {}    
        field_counter = 0

        num_cols = len(data[0])

        for i in range(num_cols):
            if i == geom_index:
                continue  

            fname = f"f{field_counter}"   
            fields.append((fname, i))

            if i < len(columns):
                orig_name = columns[i]["name"]
            else:
                orig_name = f"col_{i}"

            field_lookup[fname] = orig_name
            field_counter += 1

        messages.addMessage(f"Output fields: {fields}")

        
        out_folder, out_name = os.path.split(out_fc)
        lookup_path = os.path.join(out_folder, f"{out_name}_field_lookup.txt")

        try:
            with open(lookup_path, "w", encoding="utf-8") as f:
                for k, v in field_lookup.items():
                    f.write(f"{k} = {v}\n")
            messages.addMessage(f"Field lookup written to: {lookup_path}")
        except Exception as e:
            messages.addWarningMessage(f"Could not write lookup file: {e}")

        
        if arcpy.Exists(out_fc):
            arcpy.Delete_management(out_fc)

        sr = arcpy.SpatialReference(4326)  # WGS 84

        arcpy.CreateFeatureclass_management(
            out_folder,
            out_name,
            geom_type,
            spatial_reference=sr,
        )

        for fname, _ in fields:
            arcpy.AddField_management(out_fc, fname, "TEXT", field_length=255)

      
        insert_fields = ["SHAPE@"] + [f[0] for f in fields]

        with arcpy.da.InsertCursor(out_fc, insert_fields) as cur:
            for row in data:
                if len(row) <= geom_index:
                    continue

                wkt = row[geom_index]
                if not isinstance(wkt, str):
                    continue

                geom = arcpy.FromWKT(wkt, sr)

                attrs = []
                for _, idx in fields:
                    val = row[idx] if idx < len(row) else ""
                    if val is None:
                        val = ""
                    attrs.append(val)

                cur.insertRow([geom] + attrs)

        messages.addMessage("DONE – ward feature class created.")
        messages.addMessage(out_fc)
