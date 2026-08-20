"""Core data models shared between ingestion, detection, and output.

These are the only types the three layers agree on. Ingestion produces `CertEvent`
and knows nothing else; detection consumes `CertEvent` and produces `Finding`; output
only knows how to serialize `Finding`.
"""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError("datetime must be in UTC")
    return value


class CertEvent(BaseModel):
    serial_number: str
    signature_algo: str
    issuer_country: str | None = None
    issuer_organisation: str | None = None
    issuer_common_name: str
    validity_not_before: datetime
    validity_not_after: datetime
    domains: list[str]
    source: str
    cert_index: int | None = None
    is_precert: bool

    @field_validator("validity_not_before", "validity_not_after")
    @classmethod
    def _validate_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)

class DomainVerdict(BaseModel):
    domain: str
    matched_watch_target: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    reasons: list[str]



class Finding(BaseModel):
    schema_version: Literal["1"] = "1"
    detected_at: datetime
    cert: CertEvent
    verdicts: list[DomainVerdict]
    score: float = Field(ge=0.0, le=1.0)
    skipped_domains: list[str] = [] 
