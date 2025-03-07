"""Configuration file."""
import os 
from dotenv import load_dotenv

class Config:
    #URLS
    #MENU_URL = ""
    load_dotenv()
    MENU_URL = os.environ.get("MENU_URL", "")
    WEB_PAGE_URL = os.environ.get("WEB_PAGE_URL", "")
    RESOURCE_URI = os.environ.get("RESOURCE_URI", "")##We need this

    #Keys
    AZURE_API_KEY = os.environ.get("AZURE_API_KEY", "")##We need this
    OAI_API_KEY = os.environ.get("OAI_API_KEY", "") ##We need this
    CONNECTION_STR = os.environ.get("CONNECTION_STR", "")##We need this
    #Names
    SERVICE_NAME = os.environ.get("SERVICE_NAME", "")##We need this
    MODEL_NAME = os.environ.get("MODEL_NAME", "")## we need this

    BLOB_CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME", "")## we need this
    INDEXER_NAME = os.environ.get("INDEXER_NAME", "")
    INDEX_NAME = os.environ.get("INDEX_NAME", "") 
    SKILLSET_NAME = os.environ.get("SKILLSET_NAME", "")
    DATASOURCE_NAME = os.environ.get("DATASOURCE_NAME", "")
    
    #Other
    DEPLOYMENT_ID = os.environ.get("DEPLOYMENT_ID", "")## we need this
    
    




    