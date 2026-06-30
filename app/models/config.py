from typing import List, Dict, Optional
from pydantic import BaseModel


class ProjectionConfig(BaseModel):
    fields: List[str]
    include_confidence: bool = True
    include_provenance: bool = False
    null_handling: str = "exclude"
    field_mapping: Optional[Dict[str, str]] = None
