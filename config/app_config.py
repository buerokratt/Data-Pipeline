# App Configuration
import os
from dotenv import load_dotenv

class Config:
    load_dotenv()
    RAW_DATA = os.environ.get("RAW_DATA", "")
    PARSED_DATA = os.environ.get("PARSED_DATA", "")

    PORTAL_URL = os.environ.get("PORTAL_URL", "")

    KC_TOKEN_URL = os.environ.get("KC_TOKEN_URL", "")
    KC_CLIENT_ID = os.environ.get("KC_CLIENT_ID", "")
    KC_CLIENT_SECRET = os.environ.get("KC_CLIENT_SECRET", "")

    PORTAL_ENDPOINT = os.environ.get("PORTAL_ENDPOINT", "")
    ALLOWED_LABELS = {
        label.strip().lower()
        for label in os.environ.get("ALLOWED_LABELS", "").split(",")
        if label.strip()
    }

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