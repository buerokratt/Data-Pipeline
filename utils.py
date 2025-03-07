import json  
from io import BytesIO
from requests.adapters import HTTPAdapter, Retry
import requests
from config.app_config import Config
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

def download_image(url, max_size=10 * 1024 * 1024):  # max_size in bytes (10MB default)
    session = requests.Session()
    
    # Configure retries
    retries = Retry(
        total=5,  # Retry up to 5 times
        backoff_factor=0.3,  # Exponential backoff
        status_forcelist=[500, 502, 503, 504],  # Retry on these status codes
    )
    
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        with session.get(url, stream=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as response:
            response.raise_for_status()
            
            # Limit file size to prevent excessive memory usage
            total_size = 0
            image_data = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):  # Read in 8KB chunks
                total_size += len(chunk)
                if total_size > max_size:
                    logger.info(f"Error: File too large ({total_size / 1024 / 1024:.2f} MB)")
                    return None
                image_data.write(chunk)
            
            image_data.seek(0)  # Reset pointer to beginning
            return image_data

    except requests.exceptions.RequestException as e:
        logger.info(f"Download failed: {e}")
        return None
 
    


def get_menu():
    url = Config.MENU_URL
    query = """
{
  pages {
    list(orderBy: TITLE) {
      id
      path
      title
      description
      isPublished
    }
  }
}
"""
    payload = {"query": query}
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]["pages"]["list"] 
    else:
        return None