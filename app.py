import asyncio
import os
from time import sleep

import aioschedule
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import RetryAfter

from src.repository.db_data import db_get_car, db_delete_car, db_find_sold_cars, db_get_brand, db_get_model_id, \
    db_add_current_model, db_get_model_name, db_get_current_model
from src.utils.auto_categories import get_all_models
from src.scraper import start_scraper
from logger import get_logger
from src.utils.first_launch import preparations

logger = get_logger(__name__)

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
bot = Bot(TELEGRAM_TOKEN)
dp = Dispatcher(bot)

BRAND_ID = 79
BRAND_NAME = db_get_brand(BRAND_ID).name

temp_model = []


def normalize_price(price):
    price = (str(price) + " $").strip()
    return price


def normalize_list(array):
    correct_list = eval(array)
    return correct_list


def get_cars(user_request: dict, pointer: bool = False):
    """Gets cars to be sent to the user"""

    try:
        new_cars, updated_cars, sold_cars, all_cars = [], [], [], []
        new_cars_ids, updated_cars_ids, car_ids = start_scraper(user_request)

        '''New cars'''
        for new_car_id in new_cars_ids:
            car_obj = db_get_car(new_car_id)
            price = normalize_price(car_obj.price)
            mileage = str(car_obj.mileage) + " тис. км"
            car_images = normalize_list(car_obj.car_images)
            auction_images = normalize_list(car_obj.auction_images)
            car = {
                'title': car_obj.name,
                'car_url': car_obj.car_url,
                'price': price,
                'mileage': mileage,
                'location': car_obj.location,
                'car_images': car_images,
                'auction_url': car_obj.auction_url,
                'auction_images': auction_images
            }
            new_cars.append(car)

        '''Updated cars'''
        for updated_car_obj in updated_cars_ids:
            updated_car_id = updated_car_obj[0]
            car_obj = db_get_car(updated_car_id)
            old_price = str(updated_car_obj[1]) + " $"
            price = normalize_price(car_obj.price)
            mileage = str(car_obj.mileage) + " тис. км"
            car_images = normalize_list(car_obj.car_images)
            auction_images = normalize_list(car_obj.auction_images)
            car = {
                'title': car_obj.name,
                'car_url': car_obj.car_url,
                'price': price,
                'old_price': old_price,
                'mileage': mileage,
                'location': car_obj.location,
                'car_images': car_images,
                'auction_url': car_obj.auction_url,
                'auction_images': auction_images
            }
            updated_cars.append(car)

        '''Deletes sold cars'''
        cars = db_find_sold_cars(car_ids)
        for car_obj in cars:
            price = normalize_price(car_obj.price)
            car_images = normalize_list(car_obj.car_images)
            car = {
                'title': car_obj.name,
                'price': price,
                'location': car_obj.location,
                'car_images': car_images,
            }
            sold_cars.append(car)
            db_delete_car(car_obj.car_id)

        if pointer:
            for car_id in car_ids:
                car_obj = db_get_car(car_id)
                price = normalize_price(car_obj.price)
                mileage = str(car_obj.mileage) + " тис. км"
                car_images = normalize_list(car_obj.car_images)
                auction_images = normalize_list(car_obj.auction_images)
                car = {
                    'title': car_obj.name,
                    'car_url': car_obj.car_url,
                    'price': price,
                    'mileage': mileage,
                    'location': car_obj.location,
                    'car_images': car_images,
                    'auction_url': car_obj.auction_url,
                    'auction_images': auction_images
                }
                all_cars.append(car)

        return new_cars, updated_cars, sold_cars, all_cars

    except Exception as error:
        logger.error(f"[ERROR] {error}")


def created_car_html_message(car):
    try:
        # Extract car information from the dictionary
        title = car.get('title')
        car_url = car.get('car_url')
        price = car.get('price')
        mileage = car.get('mileage')
        location = car.get('location')
        car_images = car.get('car_images')
        auction_url = car.get('auction_url')
        auction_images = car.get('auction_images')

        # Create the HTML message
        html_message = f'<a href="{car_url}">{title}</a>\n'
        html_message += f'\U0001F4B8 {price}\n'  # Money bag icon
        html_message += f'\U0001F698 {mileage}\n'  # Car icon
        html_message += f'\U0001F30E {location}\n'  # Earth globe icon
        if auction_url:
            html_message += f'&#x1F1FA;&#x1F1F8; <a href="{auction_url}">bidfax</a>\n'  # USA flag icon

        return html_message, car_images, auction_images
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def updated_car_html_message(car):
    try:
        # Extract car information from the dictionary
        title = car.get('title')
        car_url = car.get('car_url')
        price = car.get('price')
        old_price = car.get('old_price')
        mileage = car.get('mileage')
        location = car.get('location')
        car_images = car.get('car_images')
        auction_url = car.get('auction_url')
        auction_images = car.get('auction_images')

        # Create the HTML message
        html_message = f'&#9888; Price Update\n'  # red exclamation point icon
        html_message += f'<a href="{car_url}">{title}</a>\n'
        html_message += f'\U0001F4B0 Old {old_price}\n'  # Money bag icon
        html_message += f'\U0001F4B8 New {price}\n'  # Money bag icon
        html_message += f'\U0001F698 {mileage}\n'  # Car icon
        html_message += f'\U0001F30E {location}\n'  # Earth globe icon
        if auction_url:
            html_message += f'&#x1F1FA;&#x1F1F8; <a href="{auction_url}">bidfax</a>\n'  # USA flag icon

        return html_message, car_images, auction_images
    except Exception as error:
        logger.error(f"[ERROR] {error}")


def sold_car_html_message(car):
    try:
        # Extract car information from the dictionary
        title = car.get('title')
        price = car.get('price')
        location = car.get('location')
        car_images = car.get('car_images')

        # Create the HTML message
        html_message = f'&#9888; Sold car\n'
        html_message += f'{title}\n'
        html_message += f'\U0001F4B8 {price}\n'  # Money bag icon
        html_message += f'\U0001F30E {location}\n'  # Earth globe icon

        return html_message, car_images
    except Exception as error:
        logger.error(f"[ERROR] {error}")


async def send_message(html_message, images, auction_images):
    """Sending messages to the Telegram chanel"""

    try:
        if images:
            media = [types.InputMediaPhoto(media=image_url) for image_url in images]

            await bot.send_media_group(TELEGRAM_CHANNEL_ID, media=media)
            await asyncio.sleep(6)

        message = await bot.send_message(TELEGRAM_CHANNEL_ID, html_message, parse_mode=types.ParseMode.HTML)
        await asyncio.sleep(2)

        if auction_images:
            media = [types.InputMediaPhoto(media=image_url) for image_url in auction_images]
            await bot.send_media_group(TELEGRAM_CHANNEL_ID, media=media, reply_to_message_id=message.message_id)
            await asyncio.sleep(6)
    except RetryAfter as error:
        delay = error.timeout  # Get the delay from the exception
        await asyncio.sleep(delay)  # Wait for the specified duration
        await send_message(html_message, images, auction_images)  # Retry sending the message


@dp.message_handler(commands=['start'], )
async def start_command(message: types.Message, ):
    """Menu call function"""
    info = f'Hi! This is a bot for finding your dream car quickly and efficiently\n' \
           f'You can select the car brand and model in the menu'
    kb = [[types.KeyboardButton(text="Brand")], ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Press button"
    )
    await message.answer(info, reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Brand")
@dp.message_handler(commands=["brand"], )
async def brand_select(message: types.Message):
    """Brand selector"""
    info = "Currently, only the Toyota brand is available for search.\n" \
           "So, choose Toyota model"
    kb = [[types.KeyboardButton(text="Model")], [types.KeyboardButton(text='Select Another Brand')]]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Press button"
    )
    await message.answer(info, reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Model")
@dp.message_handler(commands=["model"])
async def model_select(message: types.Message):
    """Model selector"""

    models = get_all_models(BRAND_ID)

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    model_chunks = [models[i:i + 100] for i in range(0, len(models), 100)]

    for chunk in model_chunks:
        for model in chunk:
            button = types.InlineKeyboardButton(model, callback_data=model)
            keyboard.add(button)

        await message.answer('Please select a car model:', reply_markup=keyboard)
        keyboard = types.InlineKeyboardMarkup(row_width=1)


@dp.callback_query_handler(lambda query: query.message.text == 'Please select a car model:')
async def handle_selected_model(callback_query: types.CallbackQuery):
    """Manages the user's choice"""

    selected_model = callback_query.data
    message_text = f"You selected the model: {selected_model}"

    keyboard = types.ReplyKeyboardMarkup(row_width=1, selective=True, resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Accept Choice'))
    keyboard.add(types.KeyboardButton('Select Another Model'))
    keyboard.add(types.KeyboardButton('Select Another Brand'))

    temp_model.append(selected_model)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.message.chat.id, message_text, reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Accept Choice")
async def accept_model(message: types.Message):
    """Accept the selected model"""

    model = temp_model[-1]
    model_id = db_get_model_id(model)
    await message.answer(f"You have selected {BRAND_NAME} {model}")
    await bot.send_message(message.chat.id, text="The model has been changed")

    user_request = {"model": model}
    new_cars, updated_cars, sold_cars, all_cars = get_cars(user_request, True)

    if all_cars:
        for car in all_cars:
            html_message, images, auction_images = created_car_html_message(car)
            await send_message(html_message, images, auction_images)
            logger.info(f"Sent message")
        db_add_current_model(model_id)
    else:
        await bot.send_message(message.chat.id, "Sorry, there is no cars on sale for this model.\nChoose another one")


@dp.message_handler(lambda message: message.text == "Select Another Brand")
async def back_to_brand(message: types.Message):
    """Back to brand selection screen"""

    await brand_select(message)


@dp.message_handler(lambda message: message.text == "Select Another Model")
async def back_to_model(message: types.Message):
    """Back to model selection screen"""

    await model_select(message)


@dp.message_handler()
async def handle_other_messages(message: types.Message):
    """Handle other messages"""
    await message.answer("Invalid input. Please use the menu.")


async def do_revision():
    """Every 10 minutes make a revision if smth changes, send message"""

    try:
        await asyncio.sleep(1)
        logger.info("Start revision")

        current_model = db_get_current_model()
        if current_model:
            model = db_get_model_name(current_model)
            if model:
                model = model.name
                user_request = {"model": model}
                new_cars, updated_cars, sold_cars, all_cars = get_cars(user_request)
                if new_cars:
                    for car in new_cars:
                        html_message, images, auction_images = created_car_html_message(car)
                        await send_message(html_message, images, auction_images)
                        logger.info(f"Sent message")

                if updated_cars:
                    for car in updated_cars:
                        html_message, images, auction_images = updated_car_html_message(car)
                        await send_message(html_message, images, auction_images)
                        logger.info(f"Sent message")

                if sold_cars:
                    for car in sold_cars:
                        html_message, images = sold_car_html_message(car)
                        if images:
                            media = [types.InputMediaPhoto(media=image_url) for image_url in images]

                            await bot.send_media_group(TELEGRAM_CHANNEL_ID, media=media)
                            await asyncio.sleep(6)
                        await bot.send_message(TELEGRAM_CHANNEL_ID, html_message, parse_mode=types.ParseMode.HTML)
                        await asyncio.sleep(2)
                        logger.info(f"Sent message")
            else:
                logger.warn("Choose a model")

        sleep(1)
        logger.info("End revision")
    except Exception as error:
        logger.error(error)


async def scheduler():
    """Task scheduler"""

    try:
        aioschedule.every(10).minutes.do(do_revision)

        while True:
            await aioschedule.run_pending()
            await asyncio.sleep(5)
    except Exception as error:
        logger.error(error)


async def on_startup(_):
    """Run the task scheduler when the bot starts"""

    asyncio.create_task(scheduler())
    logger.info('TelegramBot running...')


if __name__ == '__main__':
    try:
        logger.info("Start preparations")
        preparations()
        logger.info("End preparations")
        logger.info("Bot is running")
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except Exception as err:
        logger.error(err)

    # asyncio.run(do_revision())
