import os, json
from fastapi import FastAPI, Body
from typing import Any, Dict, List
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Person, Measurement, ConditionOccurrence
from transform import MappingAgent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./omop.db")

app = FastAPI(title="FHIR US Core -> OMOP Agent", version="0.1.0")

# Load mapping at startup
with open(os.path.join(os.path.dirname(__file__), "mapping_uscore_to_omop.json")) as f:
    mapping_spec = json.load(f)
agent = MappingAgent(mapping_spec)

engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/transform")
def transform_resource(resource: Dict[str, Any] = Body(...)):
    """Accept a single FHIR resource and return planned OMOP rows (no DB write)."""
    results = agent.execute(resource)
    return {"rows": [{"table": t, "values": v} for t, v in results]}

@app.post("/ingest")
def ingest_resources(resources: List[Dict[str, Any]] = Body(...)):
    """Bulk-ingest FHIR resources list -> persist mapped OMOP rows."""
    rows_written = 0
    with Session(engine) as sess:
        for r in resources:
            for table, values in agent.execute(r):
                if table == "person":
                    sess.merge(Person(**values))
                elif table == "measurement":
                    sess.merge(Measurement(**values))
                elif table == "condition_occurrence":
                    sess.merge(ConditionOccurrence(**values))
                else:
                    continue
                rows_written += 1
        sess.commit()
    return {"status": "ingested", "rows_written": rows_written}

@app.get("/export/{table}")
def export_table(table: str):
    """Export an OMOP table's rows as JSON (for verification)."""
    with Session(engine) as sess:
        if table == "person":
            data = [dict(
                person_id=o.person_id,
                gender_concept_id=o.gender_concept_id,
                year_of_birth=o.year_of_birth,
                month_of_birth=o.month_of_birth,
                day_of_birth=o.day_of_birth
            ) for o in sess.query(Person).all()]
        elif table == "measurement":
            data = [dict(
                measurement_id=o.measurement_id,
                person_id=o.person_id,
                measurement_concept_id=o.measurement_concept_id,
                measurement_date=str(o.measurement_date) if o.measurement_date else None,
                measurement_datetime=str(o.measurement_datetime) if o.measurement_datetime else None,
                value_as_number=o.value_as_number,
                unit_concept_id=o.unit_concept_id
            ) for o in sess.query(Measurement).all()]
        elif table == "condition_occurrence":
            data = [dict(
                condition_occurrence_id=o.condition_occurrence_id,
                person_id=o.person_id,
                condition_concept_id=o.condition_concept_id,
                condition_start_date=str(o.condition_start_date) if o.condition_start_date else None,
                condition_start_datetime=str(o.condition_start_datetime) if o.condition_start_datetime else None
            ) for o in sess.query(ConditionOccurrence).all()]
        else:
            return {"error": "unknown table"}
    return {"table": table, "rows": data}
