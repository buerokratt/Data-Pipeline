import json

from datetime import datetime, timezone, timedelta
from azure.storage.blob import BlobServiceClient

from config.app_config import Config

PORTAL_URL = Config.PORTAL_URL

CONNECTION_STR = Config.CONNECTION_STR
CONTAINER = Config.BLOB_CONTAINER_NAME

DOC_PREFIX = "documents/"


def build_article_blob(parsed_doc, chunks):
    return {
        "page_id": parsed_doc.page_id,
        "title": parsed_doc.title,
        "deleted": False,
        "deleted_at": None,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "title": parsed_doc.title,
                "section_heading": c.section_heading,
                "chunk": c.content,
                "source_url": parsed_doc.source_url,
            }
            for c in chunks
        ],
    }


def get_container():
    service = BlobServiceClient.from_connection_string(CONNECTION_STR)

    return service.get_container_client(CONTAINER)


def upload_article_blob(page_id: str, payload: dict):

    container = get_container()

    blob_name = f"{DOC_PREFIX}{page_id}.json"

    container.upload_blob(
        name=blob_name, data=json.dumps(payload, ensure_ascii=False), overwrite=True
    )


def read_article_blob(page_id: str):

    container = get_container()

    blob_name = f"{DOC_PREFIX}{page_id}.json"

    try:

        blob = container.download_blob(blob_name)

        return json.loads(blob.readall())

    except Exception:
        return None


def mark_blob_deleted(page_id: str):

    blob = read_article_blob(page_id)

    if not blob:
        return

    blob["deleted"] = True
    blob["deleted_at"] = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )

    upload_article_blob(page_id, blob)


def purge_deleted_blobs(retention_days=7):

    container = get_container()

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=retention_days)
    )

    deleted_count = 0

    for blob in container.list_blobs(name_starts_with=DOC_PREFIX):
        data = json.loads(
            container
            .download_blob(blob.name)
            .readall()
        )

        if not data.get("deleted"):
            continue

        deleted_at = data.get("deleted_at")

        if not deleted_at:
            continue

        deleted_time = datetime.fromisoformat(
            deleted_at.replace("Z", "+00:00")
        )

        if deleted_time < cutoff:
            container.delete_blob(blob.name)
            deleted_count += 1

    return deleted_count
