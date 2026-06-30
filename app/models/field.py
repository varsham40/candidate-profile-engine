from typing import Any, List
from pydantic import BaseModel, Field

from models.source import Provenance


class CandidateField(BaseModel):
    value: Any = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: List[Provenance] = []
    field_type: str = "exact"
    is_verified: bool = False
