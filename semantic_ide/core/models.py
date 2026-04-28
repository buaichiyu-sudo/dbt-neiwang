from typing import Any, Literal
from pydantic import BaseModel, Field


class Intent(BaseModel):
    intent_summary: str
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    time_grain: str = "day"
    complexity: Literal["Low", "Medium", "High"] = "Low"
    risk_flags: list[str] = Field(default_factory=list)
    recommended_layer: Literal["ADS", "DWS", "DWD"] = "ADS"
    reasoning_brief: str = ""


class ValidationResult(BaseModel):
    ok: bool
    error_code: str | None = None
    message: str = ""


class GenerationResult(BaseModel):
    sql: str
    yml: str
    raw: dict[str, Any] = Field(default_factory=dict)
