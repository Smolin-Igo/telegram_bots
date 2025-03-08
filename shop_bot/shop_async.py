import asyncio
import os
from dotenv import load_dotenv
import sqlite3

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("Ошибка: Необходима переменная окружения TELEGRAM_BOT_TOKEN.")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_db_connection():
    conn = sqlite3.connect('db/shop.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def create_categories_keyboard():
    categories = get_categories()
    if "Избранное" in categories:
        categories.remove("Избранное")
    categories.insert(0, "Избранное")

    keyboard = []
    buttons_per_row = 3
    for i in range(0, len(categories), buttons_per_row):
        row = categories[i:i + buttons_per_row]
        keyboard.append([KeyboardButton(text=category) for category in row])

    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)
    return markup

def create_products_keyboard(category):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.id, products.name FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE categories.name = ?
    ''', (category,))
    products = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    for product in products:
        product_id = product['id']
        product_name = product['name']
        button_text = f"{product_name} (ID: {product_id})"
        callback_data = f"show_product_{product_id}"
        builder.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    builder.add(InlineKeyboardButton(text="Назад к категориям", callback_data="back_to_categories"))
    builder.adjust(1)
    return builder.as_markup()

def create_inline_categories_keyboard():
    categories = get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.add(InlineKeyboardButton(text=category, callback_data=f"category_selected_{category}"))
    builder.adjust(1)
    return builder.as_markup()

def get_or_create_user_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT favorite_id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        favorite_id = result[0]
        conn.close()
        return favorite_id
    else:
        cursor.execute("INSERT INTO favorites DEFAULT VALUES")
        favorite_id = cursor.lastrowid

        cursor.execute("INSERT INTO users (id, favorite_id) VALUES (?, ?)", (user_id, favorite_id))
        conn.commit()
        conn.close()
        return favorite_id

def add_to_favorites(user_id, product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)

    cursor.execute('''
        SELECT 1
        FROM favorite_items
        WHERE favorite_id = ? AND product_id = ?
    ''', (favorite_id, product_id))
    existing_item = cursor.fetchone()

    if not existing_item:
        cursor.execute("INSERT INTO favorite_items (favorite_id, product_id) VALUES (?, ?)", (favorite_id, product_id))
        conn.commit()
    conn.close()

def remove_from_favorites(user_id, product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)
    cursor.execute("DELETE FROM favorite_items WHERE favorite_id = ? AND product_id = ?", (favorite_id, product_id))
    conn.commit()
    conn.close()

def show_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)
    cursor.execute('''
        SELECT products.id, products.name
        FROM favorite_items
        JOIN products ON favorite_items.product_id = products.id
        WHERE favorite_items.favorite_id = ?
    ''', (favorite_id,))
    favorite_items = cursor.fetchall()
    conn.close()

    if not favorite_items:
        return "Ваше избранное пусто."
    else:
        builder = InlineKeyboardBuilder()
        for item in favorite_items:
            product_id = item['id']
            product_name = item['name']
            button = InlineKeyboardButton(text=product_name, callback_data=f"show_product_{product_id}")
            builder.add(button)
        builder.adjust(1)
        return builder.as_markup()

async def is_product_in_favorites(user_id, product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)
    cursor.execute('''
        SELECT 1
        FROM favorite_items
        WHERE favorite_id = ? AND product_id = ?
    ''', (favorite_id, product_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

async def show_product_details(product_id, chat_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.name, description, price, image_url, seller_contacts, categories.name AS category_name
        FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE products.id = ?
    ''', (product_id,))
    product = cursor.fetchone()
    conn.close()

    if not product:
        await bot.send_message(chat_id, "Товар не найден.")
        return

    product_name = product['name']
    product_description = product['description']
    product_price = product['price']
    product_image_url = product['image_url']
    seller_contacts = product['seller_contacts']
    category_name = product['category_name']

    is_in_favorites = await is_product_in_favorites(user_id, product_id)

    builder = InlineKeyboardBuilder()

    if is_in_favorites:
        button_text = "Удалить из избранного"
        callback_data = f"remove_from_favorites_{product_id}"
    else:
        button_text = "Добавить в избранное"
        callback_data = f"add_to_favorites_{product_id}"

    fav_button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
    back_to_products_button = InlineKeyboardButton(text="Назад к товарам", callback_data=f"back_to_products_{category_name}")
    builder.add(fav_button, back_to_products_button)

    product_info = (
        f"*{product_name}*\n"
        f"{product_description}\n"
        f"{product_price:.2f} руб\n"
        f"Продавец: {seller_contacts}\n"
        f"id: {product_id}"
    )

    if product_image_url:
        sent_message = await bot.send_photo(chat_id, product_image_url, caption=product_info, reply_markup=builder.as_markup())
    else:
        sent_message = await bot.send_message(chat_id, product_info, reply_markup=builder.as_markup())
            # Сохраняем message_id
    msg_id = sent_message.message_id
    return msg_id

async def update_product_details(chat_id, message_id, user_id, product_id, category_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.name, description, price, image_url, seller_contacts, categories.name AS category_name
        FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE products.id = ?
    ''', (product_id,))
    product = cursor.fetchone()
    conn.close()

    if not product:
        await bot.send_message(chat_id, "Товар не найден.")
        return

    product_name = product['name']
    product_description = product['description']
    product_price = product['price']
    product_image_url = product['image_url']
    seller_contacts = product['seller_contacts']

    is_in_favorites = await is_product_in_favorites(user_id, product_id)

    builder = InlineKeyboardBuilder()

    if is_in_favorites:
        button_text = "Удалить из избранного"
        callback_data = f"remove_from_favorites_{product_id}"
    else:
        button_text = "Добавить в избранное"
        callback_data = f"add_to_favorites_{product_id}"

    fav_button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
    back_to_products_button = InlineKeyboardButton(text="Назад к товарам", callback_data=f"back_to_products_{category_name}")
    builder.add(fav_button, back_to_products_button)
    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("show_product_"))
async def callback_show_product(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    await show_product_details(product_id, call.message.chat.id, user_id)
    await call.answer()

@dp.callback_query(F.data.startswith("add_to_favorites_"))
async def callback_add_to_favorites(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[3])
    user_id = call.from_user.id
    add_to_favorites(user_id, product_id)
    await call.answer("Товар добавлен в избранное!")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.name, description, price, image_url, seller_contacts, categories.name AS category_name
        FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE products.id = ?
    ''', (product_id,))
    product = cursor.fetchone()
    conn.close()
    category_name = product['category_name']
    await update_product_details(call.message.chat.id, call.message.message_id,  user_id, product_id, category_name)

@dp.callback_query(F.data.startswith("remove_from_favorites_"))
async def callback_remove_from_favorites(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[3])
    user_id = call.from_user.id
    remove_from_favorites(user_id, product_id)
    await call.answer("Товар удален из избранного!")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.name, description, price, image_url, seller_contacts, categories.name AS category_name
        FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE products.id = ?
    ''', (product_id,))
    product = cursor.fetchone()
    conn.close()
    category_name = product['category_name']
    await update_product_details(call.message.chat.id, call.message.message_id,  user_id, product_id, category_name)

@dp.callback_query(F.data.startswith("back_to_products_"))
async def callback_back_to_products(call: types.CallbackQuery):
    """Возвращает к списку товаров."""
    category = call.data.split("_")[3]
    conn = get_db_connection()
    cursor = conn.cursor()
    products_keyboard = create_products_keyboard(category)
    await bot.send_message(call.message.chat.id, text=f"Товары в категории '{category}':", reply_markup=products_keyboard)
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    await call.answer()
    conn.close()

@dp.callback_query(F.data == "back_to_categories")
async def callback_back_to_categories(call: types.CallbackQuery):
    """Возвращает к списку категорий."""
    await bot.send_message(call.message.chat.id, text="Выберите категорию:", reply_markup=create_categories_keyboard())
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    await call.answer()


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    welcome_message = (
        "Добро пожаловать в наш магазин всячины!\n"
        "У нас вы найдете всякую всячину со всего света,\n"
        "Выберите категорию, чтобы посмотреть товары:"
    )
    await message.reply(welcome_message, reply_markup=create_categories_keyboard())

@dp.message(F.text)
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    if text in categories and text != "Избранное":
        markup = create_products_keyboard(text)
        await message.answer(f"Товары в категории '{text}':", reply_markup=markup)
    elif text == "Избранное":
        markup = show_favorites(user_id)
        if isinstance(markup, str):
            await message.reply(markup)
        else:
            await message.reply("Ваше избранное:", reply_markup=markup)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())