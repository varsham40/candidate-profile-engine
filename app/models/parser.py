from typing import Any
from pydantic import BaseModel


class ParserOutput(BaseModel):
    source: str
    source_type: str
    content: Any
    metadata: dict = {}
