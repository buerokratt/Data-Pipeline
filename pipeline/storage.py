from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings

from .manifest import ManifestEntry, ManifestStore


class BlobStorage:
    def __init__(self, connection_str: str, container_name: str, document_prefix: str):
        self.service = BlobServiceClient.from_connection_string(connection_str)
        self.container = self.service.get_container_client(container_name)
        self.document_prefix = document_prefix.rstrip("/") + "/"

    def ensure_container(self) -> None:
        try:
            self.container.create_container()
        except Exception as exc:
            if "ContainerAlreadyExists" not in str(exc):
                raise

    def list_document_blobs(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}

        for blob in self.container.list_blobs(
            name_starts_with=self.document_prefix
        ):
            name = blob.name

            filename = name[len(self.document_prefix):]

            if "/" in filename or not filename.endswith(".json"):
                continue

            document_uuid = filename[:-5]

            if not _looks_like_uuid(document_uuid):
                continue

            metadata = {
                k.lower(): v
                for k, v in (blob.metadata or {}).items()
            }

            html_sha = metadata.get("html_sha256")
            deleted = metadata.get("deleted", "false").lower() == "true"

            if not html_sha:
                try:
                    payload = self.read_json(name)

                    html_sha = payload.get("_pipeline", {}).get(
                        "html_content_sha256"
                    )

                    if "deleted" not in metadata:
                        deleted = bool(payload.get("deleted", False))

                except Exception:
                    html_sha = None

            result[document_uuid] = {
                "blob_name": name,
                "html_sha256": html_sha,
                "deleted": deleted,
            }

        return result

    def read_manifest(self, manifest_blob_name: str) -> dict[str, ManifestEntry] | None:
        """Read the previous run's manifest from Blob Storage"""
        try:
            payload = self.read_json(manifest_blob_name)
        except Exception as exc:
            if _is_blob_not_found(exc):
                return None
            raise

        return ManifestStore.from_payload(payload)

    def write_manifest(
        self,
        manifest_blob_name: str,
        entries: dict[str, ManifestEntry],
    ) -> None:
        data = ManifestStore.to_json(entries).encode("utf-8")
        self.container.upload_blob(
            name=manifest_blob_name,
            data=data,
            overwrite=True,
            content_settings=ContentSettings(
                content_type="application/json",
                content_encoding="utf-8",
            ),
        )

    def upload_json(
        self,
        blob_name: str,
        payload: dict[str, Any],
        *,
        html_sha256: str | None,
        deleted: bool,
        deleted_at: str | None,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        metadata = {"deleted": str(deleted).lower()}

        if html_sha256:
            metadata["html_sha256"] = html_sha256

        if deleted_at:
            metadata["deleted_at"] = deleted_at

        self.container.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            metadata=metadata,
            content_settings=ContentSettings(
                content_type="application/json",
                content_encoding="utf-8",
            ),
        )

    def read_json(self, blob_name: str) -> dict[str, Any]:
        data = self.container.download_blob(blob_name).readall()
        return json.loads(data.decode("utf-8"))

    def delete_expired_documents(self, retention_days: int = 7) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_blobs: list[str] = []

        for blob in self.container.list_blobs(
            name_starts_with=self.document_prefix
        ):
            name = blob.name

            filename = name[len(self.document_prefix):]

            if "/" in filename or not filename.endswith(".json"):
                continue

            document_uuid = filename[:-5]

            if not _looks_like_uuid(document_uuid):
                continue

            metadata = {
                k.lower(): v
                for k, v in (blob.metadata or {}).items()
            }

            if metadata.get("deleted", "false").lower() != "true":
                continue

            deleted_at_raw = metadata.get("deleted_at")

            if not deleted_at_raw:
                continue

            try:
                deleted_at = datetime.fromisoformat(
                    deleted_at_raw.replace("Z", "+00:00")
                )
            except ValueError:
                continue

            if deleted_at < cutoff:
                self.container.delete_blob(name)
                deleted_blobs.append(name)

        return deleted_blobs


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _is_blob_not_found(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    error_code = getattr(exc, "error_code", None)
    
    return status_code == 404 or str(error_code).lower() in {"blobnotfound", "resourcenotfound"}
