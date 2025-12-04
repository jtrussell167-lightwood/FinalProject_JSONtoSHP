"""
Script documentation

- Tool parameters are accessed using arcpy.GetParameter() or 
                                     arcpy.GetParameterAsText()
- Update derived parameter values using arcpy.SetParameter() or
                                        arcpy.SetParameterAsText()
"""


import arcpy
import json
import os


class Toolbox(object):
    def __init__(self):
        self.label = "Grass Cutting Tools"
        self.alias = "grass"
        
        self.tools = [GrassCuttingJSONToPoints]


class GrassCuttingJSONToPoints(object):
    def __init__(self):
        self.label = "Grass Cutting JSON to Points"
        self.description = (
            "Converts a JSON file containing WKT POINT geometries and attributes "
            "into a point feature class."
        )

    
    def getParameterInfo(self):
        """Define the parameters for the tool UI."""

        in_json = arcpy.Parameter(
            displayName="Input JSON File",
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
        """Main execution code for the tool."""

        in_json = parameters[0].valueAsText
        out_fc = parameters[1].valueAsText

        arcpy.AddMessage(f"Reading JSON: {in_json}")
        arcpy.AddMessage(f"Creating feature class: {out_fc}")

        
        with open(in_json, "r", encoding="utf-8") as f:
            j = json.load(f)

        data = j["data"]
        meta = j["meta"]
        columns = meta["view"]["columns"]

        if not data:
            raise RuntimeError("JSON 'data' array is empty.")

        sample_row = data[0]

        
        geom_index = None
        for i, val in enumerate(sample_row):
            if isinstance(val, str) and val.strip().upper().startswith("POINT"):
                geom_index = i
                break

        if geom_index is None:
            raise RuntimeError("Could not find a WKT POINT column in the first row.")

        messages.addMessage(f"Detected geometry column index: {geom_index}")

        
        fields = []  
        used_names_lower = set()
        num_cols = len(sample_row)

        for i in range(num_cols):
            if i == geom_index:
                continue  

            
            if i < len(columns):
                orig_name = columns[i]["name"]
            else:
                orig_name = f"col_{i}"

            
            clean = "".join(ch if ch.isalnum() else "_" for ch in orig_name)
            if not clean:
                clean = f"f{i}"
            clean = clean[:10]  

            
            if clean.lower() == "id":
                clean = "id_1"

            
            base = clean
            count = 1
            while clean.lower() in used_names_lower:
                suffix = f"_{count}"
                clean = (base[:10 - len(suffix)] + suffix)
                count += 1

            used_names_lower.add(clean.lower())
            fields.append((clean, i))

        messages.addMessage(f"Output fields: {fields}")

        
        out_path, out_name = os.path.split(out_fc)

        if arcpy.Exists(out_fc):
            arcpy.Delete_management(out_fc)

        sr = arcpy.SpatialReference(4326)  

        arcpy.CreateFeatureclass_management(
            out_path,
            out_name,
            "POINT",
            spatial_reference=sr,
        )

        
        for fname, idx in fields:
            arcpy.AddField_management(out_fc, fname, "TEXT", field_length=255)

        
        insert_fields = ["SHAPE@"] + [f[0] for f in fields]

        with arcpy.da.InsertCursor(out_fc, insert_fields) as cur:
            for row in data:
                if len(row) <= geom_index:
                    continue

                wkt = row[geom_index]
                if not isinstance(wkt, str) or not wkt.strip().upper().startswith("POINT"):
                    continue

                geom = arcpy.FromWKT(wkt, sr)

                attrs = []
                for _, idx in fields:
                    val = row[idx] if idx < len(row) else ""
                    if val is None:
                        val = ""
                    attrs.append(val)

                cur.insertRow([geom] + attrs)

        messages.addMessage("DONE – feature class created.")
        messages.addMessage(out_fc)
