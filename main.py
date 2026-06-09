import sys
import argparse

from config.app_config import Config
from api_client import APIClient
from logger_config import get_logger
from auth_portal import get_bearer_token
from crawler import get_all_articles, save_raw_articles
from parser import parse_article, log_unknown_nodes, save_parsed_blob
from chunker import chunk_article
# from blob_formatter import build_article_blob
# from parsed_writer import save_parsed_blob
from blob_handler import build_article_blob, upload_article_blob, mark_blob_deleted, purge_deleted_blobs
from manifest_handler import write_manifest, read_latest_manifest, diff_manifests
from trigger_indexer import run_index_request
from utils import delete_dir

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="ADF ingestion pipeline")

    parser.add_argument(
        "--mode",
        choices=["crawl", "full"],
        default="full",
        help="crawl = download + parse to local directory, full = entire pipeline with upload",
    )

    args = parser.parse_args()
    client = APIClient(get_bearer_token)
    articles = get_all_articles(client)

    if articles is None:
        logger.error("No articles found. Sad.")
        sys.exit(1)

    page_ids = [a["pageId"] for a in articles]
    previous_manifest = read_latest_manifest()
    diff = diff_manifests(previous_manifest, page_ids)

    for page_id in diff["deleted"]:
        logger.info(f"Soft deleting article: {page_id}")
        mark_blob_deleted(page_id)

    logger.info(f"Added: {len(diff['added'])}")
    logger.info(f"Deleted: {len(diff['deleted'])}")
    logger.info(f"Unchanged: {len(diff['unchanged'])}")

    save_raw_articles(articles)

    if args.mode in ["crawl", "full"]:
        success = True

        try:
            for article in articles:
                parsed = parse_article(article)
                chunks = chunk_article(parsed)
                blob_doc = build_article_blob(parsed, chunks)

                if args.mode in ["crawl"]:
                    save_parsed_blob(blob_doc)
                    logger.info("Articles saved locally.")
                
                if args.mode in ["full"]:
                    upload_article_blob(parsed.page_id, blob_doc)

        except Exception:
            success = False
            raise
        finally:
            if success and args.mode in ["full"]:
                write_manifest(page_ids)
                run_index_request()
                purged = purge_deleted_blobs(retention_days=7)
                logger.info("Purged %s expired deleted blobs", purged)

        log_unknown_nodes()
        delete_dir(Config.RAW_DATA)
        delete_dir(Config.PARSED_DATA)


if __name__ == "__main__":
    main()
