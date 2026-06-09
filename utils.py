import os
import shutil

from logger_config import get_logger

logger = get_logger(__name__) 


def delete_dir(directory):
    shutil.rmtree(directory)
    os.makedirs(directory)
    logger.info("Directory contents deleted")
