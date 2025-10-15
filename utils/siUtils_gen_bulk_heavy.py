import sys
import json
import math
import datetime

SRC = '../refs/phmdemo-hanna-barbera-cohort.json'
OUTFILE = 'hb_bulk_TST_II____.ndjson'
INDEX = 'hb_characters'

def clean_values(v):
    """
    cleans NaN/Inf, empty strings, nested lists/dicts, and coerces appearances to int.
    also forces strict JSON (allow_nan=False) so bad values can’t sneak in.
    """
    # floats: NaN/Inf/-Inf –> None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    # ints/bools/None: fine for pandas/numpy handling
    if isinstance(v, (int, bool)) or v is None:
        return v
    # datetimes: convert —> ISO8601
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    # strings: strip; empty —> None; "NaN"/"Infinity" —> None
    if isinstance(v, str):
        s = v.strip()
        if s == '' or s.lower in {'nan', 'infinity', '-infinity', 'inf', '-inf'}:
            return None
        return s
    # lists: clean each list
    if isinstance(v, list):
        return [clean_values(x) for x in v]
    # dicts: clean recursively
    if isinstance(v, dict):
        return {k: clean_values(val) for k, val in v.items()}
    # everything else —> stringify
    return str(v)

def coerce_int(x):
    if x is None:
        return None
    # accept numeric strings like '12345'
    try:
        return int(float(str(x)))
    except Exception as e_coerce_int:
        print(f'there was an ERROR with a numeric string conversion: {e_coerce_int}')
        return None

def load_and_flatten(src):
    raw = json.load(open(src, 'r', encoding='utf-8'))
    docs = []
    for series, chars in raw.items():
        for name, a in chars.items():
            a = clean_values(a or {})
            doc = {
                'series': series,
                'character': name,
                'gender': a.get('gender'),
                'age': a.get('age'),
                'ethnicity': a.get('ethnicity'),
                'species': a.get('species'),
                'occupation': a.get('occupation'),
                'location': a.get('location'),
                'appearances': coerce_int(a.get('appearances', '')),
            }
            # final clean pass on the flat doc
            docs.append(clean_values(doc))
    return docs

def write_ndjson(docs):
    with open(ndjson, 'w', encoding='utf-8') as f:
        for i, d in enumerate(docs, 1):
            f.write(json.dumps({'index':{'_index':'hb_characters', '_id':i}}) + '\n')
            f.write(json.dumps(d) + '\n')

    print(f'wrote {len(docs)} docs to {ndjson}')

