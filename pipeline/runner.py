from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.app_config import AppConfig

from .api_client import DocumentApiClient
from .manifest import ManifestEntry, ManifestStore
from .models import DocumentSummary, FetchDecision
from .parser import make_deleted_document, parse_document
from .search import trigger_indexer
from .storage import BlobStorage

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, config: AppConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.api = DocumentApiClient(
            config.api_endpoint,
            config.api_token,
            page_size=config.api_page_size,
            timeout=config.api_timeout_seconds,
        )
        self.storage = BlobStorage(
            config.connection_str, 
            config.blob_container_name, 
            config.document_prefix
        )
        self.manifest_store = ManifestStore(config.state_dir)

    def run(self) -> int:
        previous_manifest = self.storage.read_manifest(self.config.manifest_blob_name)
        if previous_manifest is None:
            previous_manifest = self.manifest_store.load()

        remote_docs = self.api.list_documents()

        remote_by_uuid = {doc.uuid: doc for doc in remote_docs}

        container_state = self.storage.list_document_blobs()
        decisions = self._plan(remote_docs, previous_manifest, container_state)

        self._log_plan(decisions)

        if self.dry_run:
            logger.info("DRY RUN: no blobs will be uploaded and no indexer will be triggered.")
            return 0

        self.storage.ensure_container()

        next_manifest = dict(previous_manifest)

        for decision in decisions:
            if decision.action == "fetch":
                doc = remote_by_uuid[decision.uuid]
                payload = self.api.fetch_html(decision.uuid)

                actual_hash = payload.get("contentSha256")
                expected_hash = doc.html_sha256

                if expected_hash and actual_hash and expected_hash != actual_hash:
                    raise RuntimeError(
                        f"Hash mismatch for {decision.uuid}: "
                        f"list={expected_hash}, fetch={actual_hash}"
                    )

                parsed = parse_document(
                    payload,
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    source_url=doc.source_url,
                )
                parsed["deleted_at"] = None
                blob_name = f"{self.config.document_prefix.rstrip('/')}/{doc.uuid}.json"

                self.storage.upload_json(
                    blob_name,
                    parsed,
                    html_sha256=expected_hash or actual_hash,
                    deleted=False,
                    deleted_at=None,
                )

                next_manifest[doc.uuid] = ManifestEntry(
                    uuid=doc.uuid,
                    html_sha256=expected_hash or actual_hash,
                    blob_name=blob_name,
                    deleted=False,
                    deleted_at=None,
                    title=parsed["title"],
                    country_code=parsed["target_market"],
                )

            elif decision.action == "deleted":
                old = previous_manifest.get(decision.uuid)

                old_blob = (
                    f"{self.config.document_prefix.rstrip('/')}/{decision.uuid}.json"
                )

                old_payload: dict[str, Any] = {}

                if old:
                    old_payload["title"] = old.title
                    old_payload["target_market"] = old.country_code
                else:
                    try:
                        old_payload = self.storage.read_json(old_blob)
                    except Exception:
                        pass

                deleted_at = datetime.now(timezone.utc).isoformat()

                tombstone = make_deleted_document(
                    document_id=decision.uuid,
                    title=old_payload.get("title", ""),
                    country_code=old_payload.get("target_market", ""),
                    deleted_at=deleted_at,
                )

                self.storage.upload_json(
                    old_blob,
                    tombstone,
                    html_sha256=None,
                    deleted=True,
                    deleted_at=deleted_at,
                )

                next_manifest[decision.uuid] = ManifestEntry(
                    uuid=decision.uuid,
                    html_sha256=None,
                    blob_name=old_blob,
                    deleted=True,
                    deleted_at=deleted_at,
                    title=tombstone["title"],
                    country_code=tombstone["target_market"],
                )

        for doc in remote_docs:
            if doc.uuid not in next_manifest:
                state = container_state.get(doc.uuid)

                next_manifest[doc.uuid] = ManifestEntry(
                    uuid=doc.uuid,
                    html_sha256=(
                        state.get("html_sha256") 
                        if state 
                        else doc.html_sha256
                    ),
                    blob_name=(
                        state["blob_name"] 
                        if state 
                        else f"{self.config.document_prefix.rstrip('/')}/{doc.uuid}.json"
                    ),
                    deleted=False,
                    deleted_at=None,
                    title=doc.title,
                    country_code=doc.country_code,
                )

        self.storage.write_manifest(self.config.manifest_blob_name, next_manifest)
        self.manifest_store.save(next_manifest)

        # Expire blobs that were deleted more than 7 days ago and rewrite manifest
        expired_blobs = self.storage.delete_expired_documents(retention_days=7)

        for blob_name in expired_blobs:
            uuid = blob_name.rsplit("/", 1)[-1][:-5]
            next_manifest.pop(uuid, None)

        self.storage.write_manifest(
            self.config.manifest_blob_name,
            next_manifest,
        )

        if decisions:
            # Trigger indexer
            trigger_indexer(
                self.config.service_name,
                self.config.azure_api_key,
                self.config.indexer_name,
            )
            logger.info("Triggered Azure AI Search indexer: %s", self.config.indexer_name)
        else:
            logger.info("No changes detected; indexer was not triggered.")

        return 0
    

    def _plan(
        self,
        remote_docs: list[DocumentSummary],
        previous_manifest: dict[str, ManifestEntry],
        container_state: dict[str, dict[str, Any]],
    ) -> list[FetchDecision]:
        decisions: list[FetchDecision] = []
        remote_ids = {doc.uuid for doc in remote_docs}

        for doc in remote_docs:
            if not doc.has_html:
                decisions.append(
                    FetchDecision(doc.uuid, "skip", "API reports hasHtml=false")
                )
                continue

            state = container_state.get(doc.uuid)
            previous = previous_manifest.get(doc.uuid)

            stored_hash = (
                state.get("html_sha256") if state else None
            ) or (previous.html_sha256 if previous and not previous.deleted else None)

            if not state:
                decisions.append(
                    FetchDecision(doc.uuid, "fetch", "UUID not present in blob container")
                )
            elif state.get("deleted"):
                decisions.append(
                    FetchDecision(doc.uuid, "fetch", "Existing blob is a deleted tombstone")
                )
            elif stored_hash != doc.html_sha256:
                decisions.append(
                    FetchDecision(doc.uuid, "fetch", "htmlContentSha256 changed")
                )
            else:
                decisions.append(
                    FetchDecision(doc.uuid, "unchanged", "UUID and hash unchanged")
                )

        # Anything that existed in the previous successful manifest, or is physically present as a document blob, but is absent from the current API listing gets a tombstone
        candidates = set(previous_manifest) | set(container_state)
        for uuid in candidates:
            if uuid in remote_ids:
                continue

            previous = previous_manifest.get(uuid)
            state = container_state.get(uuid)
            already_deleted = (
                (previous.deleted if previous else False)
                or (state.get("deleted", False) if state else False)
            )
            if not already_deleted:
                decisions.append(
                    FetchDecision(
                        uuid,
                        "deleted",
                        "UUID no longer present in API listing",
                    )
                )

        return decisions
    

    @staticmethod
    def _log_plan(decisions: list[FetchDecision]) -> None:
        counts: dict[str, int] = {}
        for decision in decisions:
            counts[decision.action] = counts.get(decision.action, 0) + 1

        logger.info("Plan: %s", counts)
        for decision in decisions:
            logger.info(
                "  %-9s %s - %s",
                decision.action,
                decision.uuid,
                decision.reason,
            )
