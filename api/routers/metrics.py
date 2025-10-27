# api/routers/metrics.py
from fastapi import APIRouter, HTTPException
from api.schemas import MetricDef
from pathlib import Path
import json

router = APIRouter()

DATA = Path("data/metric_defs.json")
DATA.parent.mkdir(parents=True, exist_ok=True)
if not DATA.exists():
    DATA.write_text(json.dumps({"metrics": {}}, indent=2))

@router.get("/", response_model=dict)
def list_metrics():
    try:
        return json.loads(DATA.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{name}", response_model=dict)
def upsert_metric(name: str, body: MetricDef):
    try:
        doc = json.loads(DATA.read_text())
        doc["metrics"][name] = body.model_dump()
        DATA.write_text(json.dumps(doc, indent=2))
        return {"ok": True, "name": name, "def": body.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))