import requests
from config.app_config import Config

from logger_config import get_logger
logger = get_logger(__name__)  

SERVICE_NAME = Config.SERVICE_NAME
INDEXER_NAME = Config.INDEXER_NAME
AZURE_API_KEY = Config.AZURE_API_KEY

indexer_url = f"https://{SERVICE_NAME}.search.windows.net/indexers/{INDEXER_NAME}/run?api-version=2024-07-01"
headers = {
    "api-key" :AZURE_API_KEY,
    "Content-Type" : "application/json"
}
def run_index_request():
    r = requests.post(indexer_url, headers=headers)
    if r.status_code == 202:
        logger.info("Run index request is accepted")
    else:
        logger.info(f"Run index request not accepted response: {r}")

if __name__ == "__main__":
    run_index_request()