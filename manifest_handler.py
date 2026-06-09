import json

from config.app_config import Config
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient

CONNECTION_STR = Config.CONNECTION_STR
CONTAINER = Config.BLOB_CONTAINER_NAME
PREFIX = "manifests/"


def _get_blob_service():
    return BlobServiceClient.from_connection_string(CONNECTION_STR)


def write_manifest(page_ids: list[str]) -> str:
    service = _get_blob_service()
    container = service.get_container_client(CONTAINER)

    run_id = datetime.now(timezone.utc).isoformat().replace(":", "-")

    manifest = {
        "run_id": run_id,
        "page_ids": page_ids,
    }

    blob_name = f"{PREFIX}{run_id}.json"

    container.upload_blob(
        name=blob_name, data=json.dumps(manifest, indent=2), overwrite=True
    )

    container.upload_blob(
        name=f"{PREFIX}latest.json", data=json.dumps(manifest, indent=2), overwrite=True
    )

    return blob_name


def read_latest_manifest() -> dict | None:
    service = _get_blob_service()
    container = service.get_container_client(CONTAINER)

    try:
        blob = container.download_blob(f"{PREFIX}latest.json")
        return json.loads(blob.readall())
    except Exception:
        return None


def diff_manifests(previous: dict | None, current_page_ids: list[str]):
    previous_ids = set(previous["page_ids"]) if previous else set()
    current_ids = set(current_page_ids)

    deleted = previous_ids - current_ids
    added = current_ids - previous_ids
    unchanged = current_ids & previous_ids

    return {
        "deleted": list(deleted),
        "added": list(added),
        "unchanged": list(unchanged),
    }
