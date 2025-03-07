import requests
from utils import read_json
from config.app_config import Config

#PUT https://[servicename].search.windows.net/skillsets/[skillset name]?api-version=[api-version]

SERVICE_NAME = Config.SERVICE_NAME
INDEX_NAME = Config.INDEX_NAME
AZURE_API_KEY = Config.AZURE_API_KEY
RESOURCE_URI = Config.RESOURCE_URI
SKILLSET_NAME = Config.SKILLSET_NAME

skillset_url = f"https://{SERVICE_NAME}.search.windows.net/skillsets/{SKILLSET_NAME}?api-version=2024-07-01"
skillset_json = "helper_json/skillset.json"

resource_uri = Config.RESOURCE_URI
oai_api_key = Config.OAI_API_KEY
model_name = Config.MODEL_NAME
deployment_id = Config.DEPLOYMENT_ID

headers = {
    "api-key":AZURE_API_KEY,
    "Content-Type":"application/json"
}

json_body = read_json(skillset_json)
print(json_body)
json_body["name"]= SKILLSET_NAME
json_body["skills"][0]["resourceUri"] = resource_uri
json_body["skills"][0]["apiKey"] = oai_api_key
json_body["skills"][0]["deploymentId"] = deployment_id
json_body["skills"][0]["modelName"] = model_name
json_body["indexProjections"]["selectors"][0]["targetIndexName"] = INDEX_NAME
print(json_body)

def create_skillset_request():
    r = requests.put(skillset_url, json=json_body,headers=headers)
    if r.status_code == 201:
        print("Skillset is created")
    else:
        print(r)
        print(f"Create skillset request not accepted response: {r.text}")

if __name__ == "__main__":
    create_skillset_request()



