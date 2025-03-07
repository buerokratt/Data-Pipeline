from azure.storage.blob import BlobServiceClient
import json
from utils import read_json, download_image
import os
import time
from config.app_config import Config
from logger_config import get_logger
logger = get_logger(__name__)  

BLOB_CONTAINER_NAME = Config.BLOB_CONTAINER_NAME
CONNECTION_STR = Config.CONNECTION_STR

BLOB_TEXT_DIR_FILE_PREFIX = "prepared_data/text"
BLOB_IMAGES_DIR_FILE_PREFIX = "prepared_data/image"
PARSE_DIR = "parsed_data/"

def init():
    client = BlobServiceClient.from_connection_string(CONNECTION_STR)
    return client

def parse_blob_url(url):
    # Not the best way of doing it, but it works.
    blob = f"{url.split('.net')[0]}.net"
    container = url.split('.net/')[1].split('/')[0]
    filepath = '/'.join(url.split('.net/')[1].split('/')[1:])
    filename = url.split('/')[-1]
    return blob, container, filepath, filename

def get_full_image_url(dir_name, file_name):
    pairs = CONNECTION_STR.split(";")
    parsed_dict = dict(pair.split("=", 1) for pair in pairs)
    return f'{parsed_dict["DefaultEndpointsProtocol"]}://{parsed_dict["AccountName"]}.blob.{parsed_dict["EndpointSuffix"]}/{BLOB_CONTAINER_NAME}/{BLOB_IMAGES_DIR_FILE_PREFIX}/{dir_name}/{file_name}'

def get_client(connection_str):
    return BlobServiceClient.from_connection_string(connection_str)
    
def upload_blob_file(blob_service_client: BlobServiceClient, container_name: str, file_name, data, overwrite=True):
        logger.info('>>> uploading file from blob')
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_client.upload_blob(data, blob_type="BlockBlob", overwrite=overwrite)
        blob_client.close()
        logger.info('<<< uploading file from blob')

def upload_to_blob(data, client):
    if client:
        downloaded_images = []
        for e in data: 
            if "content" in e and e["content"]:
                content = e['content']
                title = content['title'].replace(" ", "_")
                title = title.replace("|_", "")
                if "imgurl" in content and content["imgurl"]:
                    imgurl_list = content['imgurl']
                    new_imgurls = []
                    for imgurl in imgurl_list:
                        if imgurl not in downloaded_images:
                            image_data = download_image(imgurl)
                            if image_data:
                                blob_name = imgurl.split('/')[-1]
                                full_image_path = f'{BLOB_IMAGES_DIR_FILE_PREFIX}/{title}/{blob_name}'
                                full_image_url = get_full_image_url(title, blob_name)
                                new_imgurls.append(full_image_url)
                                upload_blob_file(client, BLOB_CONTAINER_NAME, full_image_path, image_data)
                                image_data = None
                            downloaded_images.append(imgurl)
                    content['imgurl'] = new_imgurls
                full_text_path = f'{BLOB_TEXT_DIR_FILE_PREFIX}/{title}.json'
        logger.info(f"full_text_path: {full_text_path}")
        upload_blob_file(client, BLOB_CONTAINER_NAME, full_text_path, json.dumps(data))
                
                
                

def upload_by_one():
    client = init()
    for root, _, files in os.walk(PARSE_DIR):
        for file in files:
            if file.endswith(".json"):
                parse_file_path = os.path.join(root, file)
                data = read_json(parse_file_path)
                upload_to_blob(data, client)
                data = None
                time.sleep(1)
