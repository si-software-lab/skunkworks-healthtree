# use this file (siUtils_gen_bulk_lite.py) for basic json convertion if not feeding into pandas/numpy
# use siUtils_gen_bulk_heavy.py to clean values from dtypes that break pandas/numpy

import json, sys
src = input("What is the path from the content root to the json file you'd like to convert into ndjson? </> ")
ndjson = "hb_bulk_tst.ndjson"

raw = json.load(open(src, "r", encoding="utf-8"))
docs = []
for series, chars in raw.items():
    for name, a in chars.items():
        d = {
            "series": series,
            "character": name,
            "gender": a.get("gender"),
            "age": a.get("age"),
            "ethnicity": a.get("ethnicity"),
            "species": a.get("species"),
            "occupation": a.get("occupation"),
            "location": a.get("location"),
            "appearances": int(a["appearances"]) if str(a.get("appearances","")).isdigit() else None,
        }
        docs.append(d)

with open(ndjson, "w", encoding="utf-8") as f:
    for i, d in enumerate(docs, 1):
        f.write(json.dumps({"index":{"_index":"hb_characters","_id":i}}) + "\n")
        f.write(json.dumps(d) + "\n")

print(f"wrote {len(docs)} docs -> {ndjson}")