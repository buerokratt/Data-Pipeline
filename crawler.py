import requests 
import re
import os
from config.app_config import Config
import time
import gc
from logger_config import get_logger
logger = get_logger(__name__)  

WEB_PAGE_URL = Config.WEB_PAGE_URL
raw_data = "raw_data/"
session = requests.Session()  # Use session for connection reuse

def make_get_request(url):
    try:
        with session.get(url, stream=True, timeout=10) as r:
            if r.status_code == 200:
                return r.text
    except requests.exceptions.RequestException as e:
        logger.info(f"Request failed: {e}")
    return ""

def sanitize_filename(file_name):
    sanitized_title = re.sub(r'[<>:"/\\|?*;]', '', file_name.replace(" ", "_"))
    return f"{sanitized_title}.html"

def save_raw_data(file_name, html_content):
    """file_name already contains .html part"""
    file_dir = "raw_data"
    file_path = os.path.join(file_dir, file_name)
    os.makedirs(file_dir, exist_ok=True)
    logger.info(f"Saving raw HTML file: {file_name}")
    
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(html_content)
    except MemoryError:
        logger.info(f"Memory error while writing {file_name}. Retrying after cleanup.")
        gc.collect()
        time.sleep(5)

def save_raw_html(data):
    for item in data:
        if 'path' in item and item['path']:
            url = f"{WEB_PAGE_URL}/{item['path']}"
            content = make_get_request(url)
            if content:
                file_name = sanitize_filename(item["title"])
                save_raw_data(file_name, content)
                del content
                gc.collect()
            else:
                logger.info("Failed to retrive content from:{s}".format(s=url))
        else:
            logger.info(f"No path present in: {item}")
