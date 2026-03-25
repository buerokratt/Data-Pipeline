import sys
import argparse

from utils import get_menu,delete_dir
from crawler import save_raw_html
from parser import chunk_and_parse
from blob_handler import upload_by_one
from search_indexer import run_index_request
from config.app_config import Config
from logger_config import get_logger

logger = get_logger(__name__)  

def main():
    parser = argparse.ArgumentParser(description="RAG ingestion pipeline")

    parser.add_argument(
        "--mode",
        choices=["urls", "crawl", "crawl-images", "full"],
        default="full",
        help="urls = only print URLs, crawl = download + parse, crawl-images = crawl + save images locally, full = entire pipeline",
    )

    args = parser.parse_args()

    session, menu_items = get_menu()

    if menu_items is None:
        logger.error("Menu_items is none")
        sys.exit(1)

    logger.info(f"Found {len(menu_items)} menu items")

    # Print URLs only
    if args.mode == "urls":
        for item in menu_items:
            print(f'{item["title"]} -> {item["path"]}')
        return

    save_raw_html(menu_items, session)
    chunk_and_parse()

    # Crawl and parse only
    if args.mode == "crawl":
        logger.info("Crawl + parse finished (no upload)")
        return
    
    # Download images locally
    # TODO: dry run won't upload any scraped data to blob
    if args.mode == "crawl-images":
        logger.info("Downloading images locally (dry run)")
        upload_by_one(session, dry_run=True)
        return

    # Full pipeline
    upload_by_one(session, dry_run=False)
    run_index_request()
    delete_dir("parsed_data")
    delete_dir("raw_data")

if __name__ == "__main__":
    main()