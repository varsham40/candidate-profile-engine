from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_name: str
    source_type: str
    reliability_score: float = Field(default=0.0, ge=0.0, le=1.0)


class Provenance(BaseModel):
    source_metadata: SourceMetadata
    raw_value: str
    normalized_value: str | None = None
