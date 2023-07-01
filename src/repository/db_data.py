from sqlalchemy import not_

from ..db.models import Car, Brand, Model, CurrentModel
from ..db.connection import session

from logger import get_logger

logger = get_logger(__name__)


def db_add_car(item_id, modified_title, price, mileage, location, link, images, auction_url, auction_images):
    try:
        car = Car(car_id=item_id, name=modified_title, price=price, mileage=mileage, location=location, car_url=link,
                  car_images=str(images), auction_url=auction_url, auction_images=str(auction_images))
        session.add(car)
        session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_update_car(item_id, price, mileage, location):
    try:
        car = session.query(Car).filter(Car.car_id == item_id).first()
        if car:
            car.price = price
            car.mileage = mileage
            car.location = location
        session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_car(item_id: str):
    try:
        car = session.query(Car).filter(Car.car_id == item_id).first()
        return car
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_find_sold_cars(item_ids: list):
    try:
        cars = session.query(Car).filter(not_(Car.car_id.in_(item_ids))).all()
        return cars
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_delete_car(item_id: str):
    try:
        car = session.query(Car).filter(Car.car_id == item_id).first()
        session.delete(car)
        session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_add_brand(brand_id: int = 79, brand_name: str = "Toyota"):
    try:
        brand_exists = session.query(Brand).filter(Brand.brand_id == brand_id).first()
        if not brand_exists:
            brand = Brand(name=brand_name, brand_id=brand_id)
            session.add(brand)
            session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_add_model(name, model_id, brand_id):
    try:
        model_exists = session.query(Model).filter(Model.model_id == model_id).first()
        if not model_exists:
            model = Model(name=name, model_id=model_id, brand_id=brand_id)
            session.add(model)
            session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_all_models(brand_id: int):
    try:
        models = session.query(Model).filter(Model.brand_id == brand_id).all()
        return models
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_model_id(name: str):
    try:
        model = session.query(Model).filter(Model.name == name).first()
        return model.model_id
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_model_name(id: int):
    try:
        model = session.query(Model).filter(Model.model_id == id).first()
        return model
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_brand(brand_id: int):
    try:
        brand = session.query(Brand).filter(Brand.brand_id == brand_id).first()
        return brand
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_add_current_model(model_id):
    try:
        model = session.query(CurrentModel).first()
        if model:
            model.model_id = model_id
        else:
            user = CurrentModel(model_id=model_id)
            session.add(user)
        session.commit()
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def db_get_current_model():
    try:
        model = session.query(CurrentModel).first()
        if model:
            model_id = model.model_id
        else:
            model_id = 2104
        return model_id
    except Exception as error:
        logger.error(f"[ERROR] {error}")
