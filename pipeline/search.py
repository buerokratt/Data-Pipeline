from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient


def trigger_indexer(
    service_name: str,
    api_key: str,
    indexer_name: str,
) -> None:
    endpoint = f"https://{service_name}.search.windows.net"
    client = SearchIndexerClient(endpoint, AzureKeyCredential(api_key))
    
    try:
        client.run_indexer(indexer_name)
    finally:
        client.close()
