# App Configuration
import os
from dotenv import load_dotenv

class Config:
    load_dotenv()
    PORTAL_URL = os.environ.get("PORTAL_URL", "")
    TENANT_ID = os.environ.get("TENANT_ID", "")
    LANDING = os.environ.get("LANDING", "")
    SEARCH_URL = f"{PORTAL_URL}/api/v1/guide/search"

    USERNAME = os.environ.get("USERNAME", "")
    PASSWORD = os.environ.get("PASSWORD", "")

    RESOURCE_URI = os.environ.get("RESOURCE_URI", "")
    AZURE_API_KEY = os.environ.get("AZURE_API_KEY", "")
    OAI_API_KEY = os.environ.get("OAI_API_KEY", "")
    CONNECTION_STR = os.environ.get("CONNECTION_STR", "")
    SERVICE_NAME = os.environ.get("SERVICE_NAME", "")
    MODEL_NAME = os.environ.get("MODEL_NAME", "")
    BLOB_CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME", "")
    INDEXER_NAME = os.environ.get("INDEXER_NAME", "")
    INDEX_NAME = os.environ.get("INDEX_NAME", "")
    SKILLSET_NAME = os.environ.get("SKILLSET_NAME", "")
    DATASOURCE_NAME = os.environ.get("DATASOURCE_NAME", "")
    DEPLOYMENT_ID = os.environ.get("DEPLOYMENT_ID", "")