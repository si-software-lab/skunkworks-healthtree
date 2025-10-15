from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Wolfram Scorer (stub)")

class Event(BaseModel):
    event_id: Optional[str] = None
    license_status: Optional[str] = None
    type: Optional[str] = None

class ScoreResponse(BaseModel):
    risk_score: float
    explanations: List[str]

@app.post("/score", response_model=ScoreResponse)
def score(evt: Event):
    risk = 0.2
    if (evt.license_status or "").lower() in {"expired","revoked"}:
        risk = 0.9
    return ScoreResponse(risk_score=risk, explanations=["license status heuristic"])
