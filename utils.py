import json  
from io import BytesIO
import requests
from config.app_config import Config
from auth_portal import get_authenticated_session
import shutil
import os
from logger_config import get_logger
logger = get_logger(__name__) 


def read_json(file_path):
    with open(file_path, 'r') as file:  
        # Parse the JSON data  
        data = json.load(file)
    return data


def delete_dir(directory):
    shutil.rmtree(directory)  # Deletes the directory and its contents
    os.makedirs(directory)  # Recreate the empty directory if needed
    logger.info("Directory contents deleted")


def download_image(url, session, max_size=10 * 1024 * 1024, retry_auth=True):  # max_size in bytes (10MB default)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": Config.PORTAL_URL,
        }

        response = session.get(url, stream=True, timeout=10, headers=headers)

        if response.status_code in (400, 401, 403) and retry_auth:
            logger.warning(f"Auth issue ({response.status_code}) for {url}, re-authenticating...")

            new_session = get_authenticated_session()

            return download_image(url, new_session, max_size, retry_auth=False)

        response.raise_for_status()

        # Limit file size
        total_size = 0
        image_data = BytesIO()

        for chunk in response.iter_content(chunk_size=8192):
            total_size += len(chunk)
            if total_size > max_size:
                logger.info(f"Error: File too large ({total_size / 1024 / 1024:.2f} MB)")
                return None
            image_data.write(chunk)

        image_data.seek(0)
        return image_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {url} | Error: {e}")
        return None


def get_menu():
    session = get_authenticated_session()

    page = 1
    size = 10
    menu_items = []

    while True:
        params = {
            "page": page,
            "size": size
        }

        r = session.get(Config.SEARCH_URL, params=params)

        if r.status_code != 200:
            return None

        data = r.json()

        for item in data["items"]:
            title = item["title"]
            path = item["publicPage"]["path"]

            url = f"{Config.PORTAL_URL}/juhendid{path}"

            menu_items.append({
                "title": title,
                "path": url
            })

        if not data["hasNext"]:
            break

        page += 1

    return session, menu_items
