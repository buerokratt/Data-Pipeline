from utils import read_json
import requests
from config.app_config import Config

SERVICE_NAME = Config.SERVICE_NAME
INDEX_NAME = Config.INDEX_NAME
AZURE_API_KEY = Config.AZURE_API_KEY
RESOURCE_URI = Config.RESOURCE_URI
SKILLSET_NAME = Config.SKILLSET_NAME
DATASOURCE_NAME = Config.DATASOURCE_NAME
INDEXER_NAME = Config.INDEXER_NAME

indexer_url = f"https://{SERVICE_NAME}.search.windows.net/indexers?api-version=2024-07-01"
indexer_json = "helper_json/indexer.json"

json_body = read_json(indexer_json)
json_body["name"]= INDEXER_NAME
json_body["dataSourceName"]= DATASOURCE_NAME
json_body["skillsetName"]= SKILLSET_NAME
json_body["targetIndexName"]= INDEX_NAME

headers = {
    "api-key":AZURE_API_KEY,
    "Content-Type":"application/json"
}

def create_indexer_request():
    r = requests.post(indexer_url, json=json_body,headers=headers)
    if r.status_code == 201:
        print("Indexer is created")
    else:
        print(f"Create indexer request not accepted response: {r.text}")
print(json_body)

if __name__ == "__main__":
    create_indexer_request()


