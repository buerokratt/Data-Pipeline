import requests

from logger_config import get_logger

logger = get_logger(__name__)

class APIClient:
    def __init__(self, token_provider):
        self.token_provider = token_provider
        self.token = None

    def _get_token(self):
        if not self.token:
            logger.info("Fetching bearer token...")
            self.token = self.token_provider()

        return self.token

    def get(self, url, params=None):
        token = self._get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        return response