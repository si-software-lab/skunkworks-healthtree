from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

DATA = Path("data/metric_defs.json")
DATA.parent.mkdir(parents=True, exist_ok=True)
if not DATA.exists():
    DATA.write_text(json.dumps({"metrics": {}}, indent=2))

class MetricDef(BaseModel):
    numerator_def: str
    denominator_def: str | None = None
    notes: str | None = None

app = FastAPI(title="Metrics Registry")

@app.get("/metrics")
def list_metrics():
    return json.loads(DATA.read_text())

@app.put("/metrics/{name}")
def upsert_metric(name: str, body: MetricDef):
    doc = json.loads(DATA.read_text())
    doc["metrics"][name] = body.model_dump()
    DATA.write_text(json.dumps(doc, indent=2))
    return {"ok": True, "name": name, "def": body.model_dump()}