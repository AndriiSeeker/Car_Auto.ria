import logging
import re
from time import time, sleep
from urllib.parse import urlparse, parse_qs

import validators
import requests
from bs4 import BeautifulSoup as BS

from .db.connection import session
from .db.models import Car
from logger import get_logger
from .repository.db_data import db_add_car, db_update_car
from .utils.parse_html import get_html_page

logger = get_logger(__name__)

URL = "https://auto.ria.com/uk/"


def brand_model_id(user_data: dict):
    """Extracts the brand and model ID from the search url"""

    try:
        url = fr"{URL}{user_data.get('type')}/{user_data.get('brand')}/{user_data.get('model')}"
        request = requests.get(url, params={'page': 1})
        if request.status_code == 200:
            html = BS(request.text, features='html.parser')
            href_obj = html.find('a', class_='el-selected el-check-vin')
            search_url = href_obj['href']

            parsed_url = urlparse(search_url)
            query_params = parse_qs(parsed_url.query)

            brand = query_params['brand.id[0]'][0]
            model = query_params['model.id[0]'][0]
            if not brand and not model:
                logger.warn(f"[ERROR] Didn't find car id")

            return brand, model
        else:
            logger.error(f"[ERROR] Connection Error, {request.status_code}")
        sleep(3)
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def get_auction_url(html: BS):
    """Gets auction url"""

    try:
        auction_url = ''
        attribute = "data-bidfax-pathname"
        script_tag = html.find('script', attrs={attribute: True})
        if attribute in script_tag.attrs:
            auction_url = script_tag[attribute]
            if auction_url and "/bidfax" in auction_url:
                auction_url = auction_url.replace("/bidfax", "https://bidfax.info")
                if not validators.url(auction_url):
                    logger.warn(f"[Warning] Invalid URL")
                    auction_url = ''
            else:
                logger.warn(f"[Warning] Cannot find 'bidfax' attribute")
        else:
            logger.warn(f"[Warning] Cannot find 'bidfax' attribute")
        return auction_url
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def get_auction_images(html_text: str):
    """Gets car images from auction"""

    try:
        prefix = "https://bidfax.info"
        html = BS(html_text, features='html.parser')
        gallery = html.find('div', class_='col-md-9 full-left')
        img_tags = gallery.find_all('img')
        images = [prefix + img['src'] for img in img_tags]
        return images[:5]
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def get_car_images(link: str):
    """Gets car images from Auto.ria"""

    try:
        request = requests.get(link)
        sleep(2)
        images = []
        html = ''
        if request.status_code == 200:
            html = BS(request.text, features='html.parser')
            gallery = html.find('div', class_='preview-gallery mhide').find('div', class_='wrapper')
            images_obj = gallery.find_all('a')
            for image_obj in images_obj:
                video = image_obj.find('i')
                if video:
                    continue

                img_tag = image_obj.find('img')
                image_src = img_tag['src']
                if image_src:
                    images.append(image_src)

                if len(images) == 5:
                    break
        else:
            logger.error(f"[ERROR] Connection Error, {request.status_code}")
        return images, html
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def get_cars(brand: str, model: str, user_request):
    """Gets info about car"""

    try:
        suffix = r"search/"
        url = URL + suffix
        page = 0

        # Search parameters
        params = {
            "indexName": "auto,order_auto,newauto_search",
            "categories.main.id": 1,
            "brand.id[0]": brand,
            "model.id[0]": model,
            "price.currency": 1,
            "abroad.not": 0,
            "custom.not": 1,
            "size": 100,
        }
        if user_request.get("usa_auto") and user_request.get("accident"):
            usa_auto, damaged = 0, 0
            params["country.import.usa.not"] = usa_auto
            params["damage.not"] = damaged

        new_cars = []
        updated_cars = []
        car_ids = []  # for deleting sold cars

        # Goes through all the pages with cars
        while True:
            params['page'] = page
            request = requests.get(url, params=params)
            sleep(2)
            if request.status_code == 200:
                html = BS(request.text, features='html.parser')
                cars_objects = html.find_all('div', class_='content-bar')
                if not cars_objects:
                    break

                # Gets info about every car
                for car_obj in cars_objects:
                    try:
                        item_id = 0
                        ticket_title = car_obj.find('div', class_='item ticket-title').find('a')
                        title = ticket_title.get_text(strip=True)
                        modified_title = re.sub(r'(\D)(\d)', r'\1 \2', title)
                        link = ticket_title['href'].strip()

                        pattern = r"_([0-9]+)\.html$"

                        match = re.search(pattern, link)
                        if match:
                            item_id = match.group(1)

                        price_ticket = car_obj.find('div', class_='price-ticket')
                        price_usd_obj = price_ticket.find('span', {'data-currency': 'USD'})
                        price = price_usd_obj.text.strip()

                        definition_data = car_obj.find('div', class_='definition-data')
                        mileage_obj = definition_data.find('li', class_='item-char js-race')
                        mileage = mileage_obj.text.strip().split(" ")[0].strip()
                        location_obj = car_obj.find('li', class_='item-char view-location js-location')
                        location = location_obj.text.strip().split(" ")[0].strip()

                        auction_images = []

                        # Checks if car already exists in db
                        car = session.query(Car).filter(Car.car_id == item_id).first()

                        if item_id and price and mileage and location:
                            if car and car.price != price:

                                # Updates car info in table
                                old_price = car.price
                                db_update_car(item_id, price, mileage, location)
                                updated_cars.append([item_id, old_price])
                                car_ids.append(item_id)
                                logger.info(f"Update car {item_id} in the table")

                            elif not car:
                                if link:
                                    images, car_html = get_car_images(link)

                                    auction_url = get_auction_url(car_html)
                                    if auction_url:
                                        html_text = get_html_page(auction_url)
                                        sleep(2)
                                        if html_text:
                                            auction_images = get_auction_images(html_text)

                                    # Adds car info to table
                                    db_add_car(item_id, modified_title, price, mileage, location, link, images,
                                               auction_url, auction_images)
                                    new_cars.append(item_id)
                                    car_ids.append(item_id)
                                    logger.info(f"Add car {item_id} to the table")
                            elif car:
                                car_ids.append(item_id)

                    except Exception as error:
                        logger.error(f"[ERROR] {error}")
            else:
                logger.error(f"[ERROR] Connection Error, {request.status_code}")
            sleep(2)
            page += 1

        return new_cars, updated_cars, car_ids
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def start_scraper(request: dict):
    logger.log(level=logging.INFO, msg=f"Start Scraping")
    timer = time()
    user_request = {
        "type": "legkovie",
        "brand": "toyota",
        "model": request.get('model'),
        "usa_auto": True,
        "accident": True
    }
    brand_id, model_id = brand_model_id(user_request)
    new_cars, updated_cars, car_ids = get_cars(brand_id, model_id, user_request)
    print(f"Work time {round(time() - timer, 2)} sec")
    logger.log(level=logging.INFO, msg=f"Work time {round(time() - timer, 2)} sec")
    logger.log(level=logging.INFO, msg=f"End Scraping")
    return new_cars, updated_cars, car_ids


# start_scraper({"model": "Sequoia"})
