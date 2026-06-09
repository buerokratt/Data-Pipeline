import requests

from config.app_config import Config
from logger_config import get_logger

logger = get_logger(__name__)

def get_bearer_token() -> str:
    data = {
        "grant_type": "client_credentials",
        "client_id": Config.KC_CLIENT_ID,
        "client_secret": Config.KC_CLIENT_SECRET,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    logger.info("Requesting bearer token...")

    r = requests.post(
        Config.KC_TOKEN_URL,
        data=data,
        headers=headers,
        timeout=30
    )

    logger.info(f"Response status: {r.status_code}")

    r.raise_for_status()

    response_json = r.json()

    if "access_token" not in response_json:
        raise Exception("No access token found in response")
    
    logger.info("Bearer token fetched successfully")

    return response_json["access_token"]