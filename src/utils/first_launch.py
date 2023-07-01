from time import sleep

from logger import get_logger

from src.utils.auto_categories import record_brand, record_all_models

logger = get_logger(__name__)


def preparations():
    try:
        record_brand()
        sleep(1)
        record_all_models()
    except Exception as error:
        logger.error(f"[ERROR] {error}")
