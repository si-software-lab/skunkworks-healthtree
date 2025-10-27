# api/schemas.py
from pydantic import BaseModel
from typing import Optional

class MetricDef(BaseModel):
    numerator_def: str
    denominator_def: Optional[str] = None
    notes: Optional[str] = None