from __future__ import annotations

import argparse
import logging
import sys

from config.app_config import AppConfig
from pipeline.runner import Pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize documents into Azure Blob Storage and trigger Azure AI Search."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the planned fetch/delete actions without uploading or triggering the indexer.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    args = parse_args()

    try:
        config = AppConfig.from_env()
        config.ensure_state_dir()
        return Pipeline(config, dry_run=args.dry_run).run()
    except Exception:
        logging.getLogger(__name__).exception("Pipeline failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
