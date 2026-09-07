from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentSummary:
    uuid: str
    html_sha256: str | None
    has_html: bool
    country_code: str
    title: str
    source_url: str
    html_file_name: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class FetchDecision:
    uuid: str
    action: str  # fetch / unchanged / deleted / skip
    reason: str
