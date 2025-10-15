import json, re
from datetime import datetime
from dateutil import parser as dtparser
from typing import Any, Dict, List, Tuple, Optional

# Minimal JSONPath-ish extractor supporting simple paths and array indices
def jget(payload: dict, path: str) -> Any:
    if not path or not path.startswith("$."):
        return None
    parts = re.split(r"\.(?![^\[]*\])", path[2:])  # split on dots not inside brackets
    cur = payload
    for p in parts:
        m = re.match(r"(.+?)\[(\d+)\]$", p)
        if m:
            key, idx = m.group(1), int(m.group(2))
            cur = (cur or {}).get(key, [])
            if isinstance(cur, list) and len(cur) > idx:
                cur = cur[idx]
            else:
                return None
        else:
            cur = (cur or {}).get(p)
        if cur is None:
            return None
    return cur

# Transform helpers (stubs; replace with vocabulary lookups later)
def uuid_as_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    # quick deterministic hash to int range
    return abs(hash(str(val))) % (2**31 - 1)

def gender_to_concept(val: str) -> Optional[int]:
    mapping = {"male": 8507, "female": 8532, "other": 8551, "unknown": 8551}
    return mapping.get((val or "").lower())

def date_year(val: str) -> Optional[int]:
    if not val: return None
    try:
        return dtparser.parse(val).year
    except: return None

def date_month(val: str) -> Optional[int]:
    if not val: return None
    try:
        return dtparser.parse(val).month
    except: return None

def date_day(val: str) -> Optional[int]:
    if not val: return None
    try:
        return dtparser.parse(val).day
    except: return None

def to_date(val: str):
    try:
        return dtparser.parse(val).date()
    except:
        return None

def to_datetime(val: str):
    try:
        return dtparser.parse(val)
    except:
        return None

def fhir_ref_to_person_id(ref: str) -> Optional[int]:
    # expects 'Patient/<id>'
    if not ref:
        return None
    parts = str(ref).split("/")
    if len(parts) == 2 and parts[0].lower() == "patient":
        return uuid_as_int(parts[1])
    return None

# Placeholder concept mappers (replace with real vocab services)
def loinc_to_concept(code: str) -> Optional[int]:
    if not code: return None
    return 100000 + (abs(hash(code)) % 100000)

def ucum_to_concept(code: str) -> Optional[int]:
    if not code: return None
    return 300000 + (abs(hash(code)) % 100000)

def snomed_to_concept(code: str) -> Optional[int]:
    if not code: return None
    return 200000 + (abs(hash(code)) % 100000)

# Evaluate simple boolean expressions like "x in ['a','b']"
def simple_match(expr: str, payload: dict) -> bool:
    try:
        if " in " in expr:
            left, right = expr.split(" in ", 1)
            left = left.strip()
            right = right.strip()
            if left.startswith("$."):
                v = jget(payload, left)
            else:
                return False
            arr = json.loads(right.replace("'", '"'))
            return v in arr
        return False
    except Exception:
        return False

class MappingAgent:
    def __init__(self, mapping_spec: Dict[str, Any]):
        self.mapping_spec = mapping_spec

    def plan(self, resource: dict) -> List[Tuple[str, Dict[str, Any]]]:
        plans = []
        for name, m in self.mapping_spec.items():
            if resource.get("resourceType") != m.get("resourceType"):
                continue
            match_expr = m.get("match")
            if match_expr and not simple_match(match_expr, resource):
                continue
            plans.append((m.get("omop_table"), m))
        return plans

    def execute(self, resource: dict) -> List[Tuple[str, Dict[str, Any]]]:
        results = []
        for table, spec in self.plan(resource):
            row: Dict[str, Any] = {}
            for rule in spec.get("rules", []):
                src = rule.get("from")
                omop_field = rule["omop_field"]
                val = jget(resource, src) if src else None
                transform = rule.get("transform")
                if transform:
                    fn = globals().get(transform)
                    val = fn(val) if fn else val
                row[omop_field] = val
            results.append((table, row))
        return results
