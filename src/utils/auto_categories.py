import os

import requests
from dotenv import load_dotenv

from logger import get_logger
from ..repository.db_data import db_add_model, db_get_all_models, db_add_brand

load_dotenv()

logger = get_logger(__name__)

API_KEY = os.environ.get('RIA_API_KEY')

category_id, brand_id = 1, 79

brands_url = f"https://developers.ria.com/auto/categories/{category_id}/marks?api_key=" + API_KEY
models_url = f"http://api.auto.ria.com/categories/{category_id}/marks/{brand_id}/models?api_key=" + API_KEY


def record_brand():
    try:
        db_add_brand()
        logger.info(f"Brand was added")
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def record_all_models():
    """Record all models of current brand from Auto.ria API"""

    try:
        request = requests.get(models_url)
        if request.status_code == 200:
            request.encoding = "utf-8"
            all_models: list[dict] = request.json()
            for model in all_models:
                name = model.get("name")
                model_id = model.get("value")
                db_add_model(name, model_id, brand_id)
            logger.info(f"All models of brand {brand_id} were recorded")
        else:
            logger.error(f"[ERROR] Connection Error, {request.status_code}")
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def get_all_models(brand_id: int):
    """Get all models for user to choose"""

    try:
        models_obj = db_get_all_models(brand_id)
        models = [model_obj.name for model_obj in models_obj]
        return models
    except Exception as error:
        logger.error(f"[ERROR] {error}")
