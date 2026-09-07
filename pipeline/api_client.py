from __future__ import annotations

import logging
from typing import Any

import requests

from .models import DocumentSummary

logger = logging.getLogger(__name__)


class DocumentApiClient:
    def __init__(self, endpoint: str, token: str, page_size: int = 100, timeout: int = 60):
        self.base_url = endpoint.rstrip("/")
        self.page_size = page_size
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    def list_documents(self) -> list[DocumentSummary]:
        url = f"{self.base_url}/document/documents"
        offset = 0
        all_docs: list[DocumentSummary] = []

        while True:
            response = self.session.get(
                url,
                params={"limit": self.page_size, "offset": offset},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()

            items = payload.get("documents", [])
            all_docs.extend(self._to_summary(item) for item in items)

            returned_limit = int(payload.get("limit", self.page_size))
            logger.info(
                "Listed page: offset=%s, returned=%s, total_so_far=%s",
                offset,
                len(items),
                len(all_docs),
            )

            if not items or len(items) < returned_limit:
                break

            offset += returned_limit

        by_uuid: dict[str, DocumentSummary] = {}
        for doc in all_docs:
            if doc.uuid in by_uuid:
                raise RuntimeError(f"Duplicate document UUID from API: {doc.uuid}")
            by_uuid[doc.uuid] = doc

        return list(by_uuid.values())

    def fetch_html(self, document_uuid: str) -> dict[str, Any]:
        url = f"{self.base_url}/document/documents/{document_uuid}/html"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        if payload.get("documentUuid") != document_uuid:
            raise RuntimeError(
                f"API returned documentUuid={payload.get('documentUuid')!r} "
                f"for requested UUID={document_uuid!r}"
            )
        return payload

    @staticmethod
    def _to_summary(item: dict[str, Any]) -> DocumentSummary:
        return DocumentSummary(
            uuid=item["uuid"],
            html_sha256=item.get("htmlContentSha256"),
            has_html=bool(item.get("hasHtml")),
            country_code=item.get("countryCode", ""),
            title=item.get("originalFileName", ""),
            source_url=item.get("url", ""),
            html_file_name=item.get("htmlFileName", ""),
            raw=item,
        )
