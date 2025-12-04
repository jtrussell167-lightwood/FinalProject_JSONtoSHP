import json

json_path = r"C:\Users\jruss69\Downloads\newno_tax.json"

with open(json_path, 'r', encoding='utf-8') as f:
    j = json.load(f)

j.keys()

columns = meta["view"]["columns"]

for i, c in enumerate(columns):
    print(i, c["name"])

import arcpy
import json
import os

arcpy.env.overwriteOutput = True

json_path = r"C:\Users\jruss69\Downloads\newno_tax.json"

out_folder = r"C:\Users\jruss69\Downloads\Proj1_JSONtoShp\output"
out_name = "newno_tax_features.shp"
out_fc = os.path.join(out_folder, out_name)

with open(json_path, 'r', encoding='utf-8') as f:
    j = json.load(f)

data = j["data"]
meta = j["meta"]
columns = meta["view"]["columns"]

geom_index = None
for i, col in enumerate(columns):
    if col["name"] == "the_geom":
        geom_index = i
        break

if geom_index is None:
    raise Exception("Could not find 'the_geom' column.")

print("the_geom index:", geom_index)

sample_wkt = data[0][geom_index]
up = str(sample_wkt).strip().upper()

if "POLYGON" in up:
    geom_type = "POLYGON"
elif up.startswith("POINT"):
    geom_type = "POINT"
else:
    raise Exception(f"Unrecognized WKT geometry type: {sample_wkt[:40]}")

print("Detected geometry type:", geom_type)

fields = []
field_lookup = {}
field_counter = 0

num_cols = len(data[0])

for i in range(num_cols):
    if i == geom_index:
        continue  

    fname = f"f{field_counter}"   
    fields.append((fname, "TEXT", i))

    if i < len(columns):
        orig_name = columns[i]["name"]
    else:
        orig_name = f"col_{i}"

    field_lookup[fname] = orig_name
    field_counter += 1

lookup_path = os.path.join(out_folder, "newno_field_lookup.txt")
with open(lookup_path, "w") as f:
    for k, v in field_lookup.items():
        f.write(f"{k} = {v}\n")

print("Field lookup saved at:", lookup_path)

if arcpy.Exists(out_fc):
    arcpy.Delete_management(out_fc)

sr = arcpy.SpatialReference(4326)

arcpy.CreateFeatureclass_management(
    out_path=out_folder,
    out_name=out_name,
    geometry_type=geom_type,
    spatial_reference=sr
)

for fname, ftype, idx in fields:
    arcpy.AddField_management(out_fc, fname, ftype, field_length=255)

with arcpy.da.InsertCursor(out_fc, ["SHAPE@"] + [f[0] for f in fields]) as cur:
    for row in data:
        if len(row) <= geom_index:
            continue

        wkt = row[geom_index]
        if not isinstance(wkt, str):
            continue

        geom = arcpy.FromWKT(wkt, sr)

        attrs = []
        for _, _, idx in fields:
            val = row[idx] if idx < len(row) else ""
            if val is None:
                val = ""
            attrs.append(val)

        cur.insertRow([geom] + attrs)

print("DONE — shapefile created at:", out_fc)



