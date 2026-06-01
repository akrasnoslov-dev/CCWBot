from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    source: str

    def as_dict(self) -> dict[str, str]:
        return {
            "start": isoformat_utc(self.start),
            "end": isoformat_utc(self.end),
            "source": self.source,
        }


@dataclass
class CollectorStatus:
    name: str
    status: str
    error: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "status": self.status, "error": self.error}


@dataclass
class DetectorResult:
    id: str
    severity: str
    status: str
    summary: str
    evidence_refs: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "status": self.status,
            "summary": self.summary,
            "evidence_refs": self.evidence_refs,
            "metrics": self.metrics,
        }


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
