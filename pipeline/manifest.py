from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ManifestEntry:
    uuid: str
    html_sha256: str | None
    blob_name: str
    deleted: bool
    deleted_at: str | None = None
    title: str = ""
    country_code: str = ""


class ManifestStore:
    def __init__(self, state_dir: Path):
        self.path = state_dir / "manifest.json"
        state_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, ManifestEntry]:
        if not self.path.exists():
            return {}
        return self.from_payload(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, entries: dict[str, ManifestEntry]) -> None:
        self.path.write_text(self.to_json(entries), encoding="utf-8")

    @staticmethod
    def to_payload(entries: dict[str, ManifestEntry]) -> dict[str, Any]:
        return {
            "version": 1,
            "documents": {
                uuid: asdict(entry)
                for uuid, entry in sorted(entries.items())
            },
        }

    @classmethod
    def to_json(cls, entries: dict[str, ManifestEntry]) -> str:
        return json.dumps(
            cls.to_payload(entries), ensure_ascii=False, indent=2
        )

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> dict[str, ManifestEntry]:
        return {
            uuid: ManifestEntry(**entry)
            for uuid, entry in payload.get("documents", {}).items()
        }
