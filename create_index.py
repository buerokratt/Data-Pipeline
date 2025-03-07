from utils import read_json
import requests
from config.app_config import Config


SERVICE_NAME = Config.SERVICE_NAME
INDEX_NAME = Config.INDEX_NAME
AZURE_API_KEY = Config.AZURE_API_KEY
RESOURCE_URI = Config.RESOURCE_URI

index_url = f"https://{SERVICE_NAME}.search.windows.net/indexes?api-version=2024-07-01"
index_json = "helper_json/index.json"

headers = {
    "api-key":AZURE_API_KEY,
    "Content-Type":"application/json"
}
resourceUri = Config.RESOURCE_URI
deploymentId = Config.DEPLOYMENT_ID
apiKey = Config.OAI_API_KEY
modelName = Config.MODEL_NAME

def create_index_request():
    r = requests.post(index_url, json=json_body,headers=headers)
    if r.status_code == 201:
        print("Index is created")
    else:
        print(f"Create index request not accepted response: {r.text}")

json_body = read_json(index_json)
json_body["name"] = INDEX_NAME

for field in json_body["fields"]:
    if field["name"] == "text_vector":
        field["vectorSearchProfile"] = f"{INDEX_NAME}-azureOpenAi-text-profile"
json_body["semantic"]["defaultConfiguration"] = f"{INDEX_NAME}-semantic-configuration"
json_body["semantic"]["configurations"][0]["name"] = f"{INDEX_NAME}-semantic-configuration"
json_body["vectorSearch"]["algorithms"][0]["name"] = f"{INDEX_NAME}-algorithm"

json_body["vectorSearch"]["profiles"][0]["name"] = f"{INDEX_NAME}-azureOpenAi-text-profile"
json_body["vectorSearch"]["profiles"][0]["algorithm"] = f"{INDEX_NAME}-algorithm"
json_body["vectorSearch"]["profiles"][0]["vectorizer"] = f"{INDEX_NAME}-azureOpenAi-text-vectorizer"

json_body["vectorSearch"]["vectorizers"][0]["name"] = f"{INDEX_NAME}-azureOpenAi-text-vectorizer"
json_body["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]["resourceUri"] = resourceUri
json_body["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]["deploymentId"] = deploymentId
json_body["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]["apiKey"] = apiKey
json_body["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]["modelName"] = modelName
print(json_body)

if __name__ == "__main__":
    create_index_request()






