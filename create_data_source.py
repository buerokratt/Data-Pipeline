import requests
from utils import read_json
from config.app_config import Config

SERVICE_NAME = Config.SERVICE_NAME
AZURE_API_KEY = Config.AZURE_API_KEY
CONNECTION_STR = Config.CONNECTION_STR
BLOB_CONTAINER_NAME = Config.BLOB_CONTAINER_NAME
INDEX_NAME = Config.INDEX_NAME  ## NOTE this cannot be underscored
DATASOURCE_NAME = Config.DATASOURCE_NAME

data_source_uri = f"https://{SERVICE_NAME}.search.windows.net/datasources?api-version=2024-07-01"
data_source_json = "helper_json/datasource.json"

json_body = read_json(data_source_json)
json_body["credentials"]["connectionString"] = CONNECTION_STR
json_body["container"]["name"] = BLOB_CONTAINER_NAME
json_body["name"] = DATASOURCE_NAME

headers = {
    "api-key":AZURE_API_KEY,
    "Content-Type":"application/json"
}
print(json_body)

def create_data_source_request():
    r = requests.post(data_source_uri, json=json_body,headers=headers)
    if r.status_code == 201:
        print("Data source is created")
    else:
        print(f"Create data source request not accepted response: {r.text}")

if __name__ == "__main__":
    create_data_source_request()