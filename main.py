import sys

from utils import get_menu,delete_dir
from crawler import save_raw_html
from parser import chunk_and_parse
from blob_handler import upload_by_one
from search_indexer import run_index_request
from config.app_config import Config
from logger_config import get_logger
logger = get_logger(__name__)  

def main():
    menu_items = get_menu()
    if menu_items is None:
        logger.error("Menu_items is none")
        sys.exit(1)  # Exit with error status
    menu_items = [item for item in menu_items  if item["isPublished"]]
    save_raw_html(menu_items)
    chunk_and_parse()
    upload_by_one()
    run_index_request()
    delete_dir("parsed_data")
    delete_dir("raw_data")

if __name__ == "__main__":
    main()