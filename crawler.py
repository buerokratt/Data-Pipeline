import re
import json
import os

from config.app_config import Config
from api_client import APIClient
from logger_config import get_logger

logger = get_logger(__name__)

raw_data = Config.RAW_DATA


def get_all_articles(client: APIClient):
    page = 1
    size = 10

    articles = []

    while True:
        logger.info(f"Fetching page {page}")

        response = client.get(
            Config.PORTAL_ENDPOINT, params={"page": page, "size": size}
        )

        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        logger.info(f"Fetched {len(items)} articles")

        articles.extend(items)

        if not data.get("hasNext"):
            break

        page += 1

    logger.info(f"Total articles fetched: {len(articles)}")

    return articles


def save_raw_articles(articles, output_dir=raw_data):
    os.makedirs(output_dir, exist_ok=True)

    for article in articles:
        page_id = article["pageId"]
        title = article["title"]

        sanitized_title = re.sub(r'[<>:"/\\|?*;]', "", title.replace(" ", "_"))

        output_path = os.path.join(output_dir, f"raw_{page_id}_{sanitized_title}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(articles)} raw articles")
