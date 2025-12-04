import json

json_path = r"C:\Users\jruss69\Downloads\no_tax.json"

with open(json_path, 'r', encoding='utf-8') as f:
    j = json.load(f)

j.keys()


meta = j["meta"]
meta


columns = meta["view"]["columns"]

for i, c in enumerate(columns):
    print(i, c["name"])


row0 = j["data"][0]
row0[36]


import arcpy
import json
import os

arcpy.env.overwriteOutput = True

json_path = r"C:\Users\jruss69\Downloads\no_tax.json"

out_folder = r"C:\Users\jruss69\Downloads\Proj1_JSONtoShp\output"
out_name = "no_tax_points.shp"
out_fc = os.path.join(out_folder, out_name)

with open(json_path, 'r', encoding='utf-8') as f:
    j = json.load(f)

data = j["data"]
meta = j["meta"]

columns = meta["view"]["columns"]

geom_index = 36  

fields = []
used_names = set()

for i, col in enumerate(columns):
    name = col["name"]

    if i == geom_index:
        continue

    clean = "".join(ch if ch.isalnum() else "_" for ch in name)
    clean = clean[:10]  

    if clean.lower() == "id":
        clean = "id_1"

    base = clean
    count = 1
    while clean in used_names:
        suffix = f"_{count}"
        clean = (base[:10-len(suffix)] + suffix)
        count += 1

    used_names.add(clean)

    fields.append((clean, "TEXT", i))

if arcpy.Exists(out_fc):
    arcpy.Delete_management(out_fc)

sr = arcpy.SpatialReference(4326)  # WGS84

arcpy.CreateFeatureclass_management(
    out_path=out_folder,
    out_name=out_name,
    geometry_type="POINT",
    spatial_reference=sr
)

for fname, ftype, idx in fields:
    arcpy.AddField_management(out_fc, fname, ftype, field_length=255)

with arcpy.da.InsertCursor(out_fc, ["SHAPE@"] + [f[0] for f in fields]) as cur:
    for row in data:
        wkt = row[geom_index]
        if not wkt:
            continue

        geom = arcpy.FromWKT(wkt, sr)

        attributes = []
        for _, _, idx in fields:
            val = row[idx]
            if val is None:
                val = ""
            attributes.append(val)

        cur.insertRow([geom] + attributes)

print("DONE — shapefile created at:", out_fc)





