from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


@dataclass(frozen=True)
class AppConfig:
    api_endpoint: str
    api_token: str
    resource_uri: str
    deployment_id: str
    model_name: str
    oai_api_key: str
    blob_container_name: str
    connection_str: str
    service_name: str
    index_name: str
    datasource_name: str
    skillset_name: str
    indexer_name: str
    azure_api_key: str
    chunk_size: int = 4000
    chunk_overlap: int = 400
    api_page_size: int = 100
    api_timeout_seconds: int = 60
    manifest_blob_name: str = "manifest.json"
    document_prefix: str = "documents/"
    state_dir: Path = ROOT_DIR / "data" / "state"

    @property
    def search_endpoint(self) -> str:
        return f"https://{self.service_name}.search.windows.net"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            api_endpoint=_required("API_ENDPOINT").rstrip("/"),
            api_token=_required("API_TOKEN"),
            resource_uri=_required("RESOURCE_URI").rstrip("/"),
            deployment_id=_required("DEPLOYMENT_ID"),
            model_name=_required("MODEL_NAME"),
            oai_api_key=_required("OAI_API_KEY"),
            blob_container_name=_required("BLOB_CONTAINER_NAME"),
            connection_str=_required("CONNECTION_STR"),
            service_name=_required("SERVICE_NAME"),
            index_name=_required("INDEX_NAME"),
            datasource_name=_required("DATASOURCE_NAME"),
            skillset_name=_required("SKILLSET_NAME"),
            indexer_name=_required("INDEXER_NAME"),
            azure_api_key=_required("AZURE_API_KEY"),
            chunk_size=_int("CHUNK_SIZE", 4000),
            chunk_overlap=_int("CHUNK_OVERLAP", 400),
            api_page_size=_int("API_PAGE_SIZE", 100),
            api_timeout_seconds=_int("API_TIMEOUT_SECONDS", 60),
            manifest_blob_name=os.getenv("MANIFEST_BLOB_NAME", "manifest.json"),
            document_prefix=os.getenv("DOCUMENT_PREFIX", "documents/"),
            state_dir=Path(os.getenv("STATE_DIR", str(ROOT_DIR / "data" / "state"))),
        )

    def ensure_state_dir(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
