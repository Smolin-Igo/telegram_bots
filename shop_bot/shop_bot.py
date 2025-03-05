import telebot
import os
from dotenv import load_dotenv
import sqlite3
from telebot import types

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("Ошибка: Необходима переменная окружения TELEGRAM_BOT_TOKEN.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# Функция для создания соединения с БД
def get_db_connection():
    conn = sqlite3.connect('db/shop.db') # Путь к базе данных
    conn.row_factory = sqlite3.Row  # Для доступа к данным по именам столбцов
    return conn

# --- Функции для работы с базой данных ---
def add_category(category_name):
    """Добавляет категорию в базу данных."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Категория уже существует

def delete_category(category_name):
    """Удаляет категорию из базы данных."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))
    conn.commit()
    conn.close()

def add_product(category_id, name, description, price, image_url, seller_contacts):
    """Добавляет продукт в базу данных."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (category_id, name, description, price, image_url, seller_contacts)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (category_id, name, description, price, image_url, seller_contacts))
    conn.commit()
    conn.close()

def delete_product(product_id):
    """Удаляет продукт из базы данных."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# --- Функции для создания клавиатур ---
def create_categories_keyboard():
    """Создает клавиатуру с категориями товаров."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Добавляем "Избранное" в начало списка категорий (если его там нет)
    if "Избранное" in categories:
        categories.remove("Избранное")  # Убираем, если уже есть
    categories.insert(0, "Избранное")  # Вставляем в начало

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in categories:
        markup.add(telebot.types.KeyboardButton(category))
    return markup

def create_products_keyboard(category):
    """Создает клавиатуру с товарами в выбранной категории."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT products.id, products.name FROM products
        JOIN categories ON products.category_id = categories.id
        WHERE categories.name = ?
    ''', (category,))
    products = cursor.fetchall()
    conn.close()
    markup = telebot.types.InlineKeyboardMarkup()
    for product in products:
        product_id = product['id']
        product_name = product['name']
        button_text = f"{product_name} (ID: {product_id})"  # Добавляем ID продукта в текст кнопки
        callback_data = f"show_product_{product_id}"  # Используем ID товара
        button = telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data)
        markup.add(button)
    markup.add(telebot.types.InlineKeyboardButton("Назад к категориям", callback_data="back_to_categories"))
    return markup

def create_admin_keyboard():
    """Создает клавиатуру для администратора."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("Добавить категорию")
    item2 = telebot.types.KeyboardButton("Удалить категорию")
    item3 = telebot.types.KeyboardButton("Добавить продукт")
    item4 = telebot.types.KeyboardButton("Удалить продукт")
    markup.add(item1, item2)
    markup.add(item3, item4)
    return markup

# --- Функции для работы с избранным ---
def get_or_create_user_favorites(user_id):
    """Получает или создает избранное для пользователя."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в таблице users
    cursor.execute("SELECT favorite_id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        # Если пользователь есть, возвращаем его favorite_id
        favorite_id = result[0]
        conn.close()
        return favorite_id
    else:
        # Если пользователя нет, создаем новое избранное
        cursor.execute("INSERT INTO favorites DEFAULT VALUES")
        favorite_id = cursor.lastrowid

        # Создаем запись о пользователе и привязываем к избранному
        cursor.execute("INSERT INTO users (id, favorite_id) VALUES (?, ?)", (user_id, favorite_id))
        conn.commit()
        conn.close()
        return favorite_id

def add_to_favorites(user_id, product_id):
    """Добавляет товар в избранное пользователя, если его там еще нет."""
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)

    # Проверяем, есть ли уже товар в избранном
    cursor.execute('''
        SELECT 1
        FROM favorite_items
        WHERE favorite_id = ? AND product_id = ?
    ''', (favorite_id, product_id))
    existing_item = cursor.fetchone()

    if not existing_item:
        # Если товара нет, добавляем его в избранное
        cursor.execute("INSERT INTO favorite_items (favorite_id, product_id) VALUES (?, ?)", (favorite_id, product_id))
        conn.commit()
    conn.close()

def remove_from_favorites(user_id, product_id):
    """Удаляет товар из избранного пользователя."""
    conn = get_db_connection()
    cursor = conn.cursor()
    favorite_id = get_or_create_user_favorites(user_id)
    cursor.execute("DELETE FROM favorite_items WHERE favorite_id = ? AND product_id = ?", (favorite_id, product_id))
    conn.commit()
    conn.close()

def show_favorites(user_id):
    """Формирует сообщение с содержимым избранного."""
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
        markup = types.InlineKeyboardMarkup()
        for item in favorite_items:
            product_id = item['id']
            product_name = item['name']
            button = types.InlineKeyboardButton(product_name, callback_data=f"show_product_{product_id}")
            markup.add(button)
        return markup

# --- Обработчики сообщений ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Отправляет приветственное сообщение и показывает категории."""
    welcome_message = (
        "Добро пожаловать в наш магазин всячины!\n"
        "У нас вы найдете всякую всячину со всего света,\n"
        "Выберите категорию, чтобы посмотреть товары:"
    )
    bot.reply_to(message, welcome_message, reply_markup=create_categories_keyboard())

@bot.message_handler(func=lambda message: message.text in [row[0] for row in get_db_connection().cursor().execute("SELECT name FROM categories").fetchall()])
def show_products(message):
    """Показывает товары в выбранной категории."""
    category = message.text
    markup = create_products_keyboard(category)
    bot.send_message(message.chat.id, f"Товары в категории '{category}':", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Избранное")
def view_favorites(message):
    """Показывает содержимое избранного."""
    user_id = message.from_user.id
    markup = show_favorites(user_id)
    if isinstance(markup, str):
        bot.reply_to(message, markup)  # Отправляем текстовое сообщение, если избранное пусто
    else:
        bot.reply_to(message, "Ваше избранное:", reply_markup=markup)  # Отправляем клавиатуру с товарами

# --- Обработчики callback-запросов ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_favorites_"))
def callback_add_to_favorites(call):
    """Обрабатывает нажатия на кнопки добавления в избранное."""
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[3])  # Получаем ID товара
    add_to_favorites(user_id, product_id)
    bot.answer_callback_query(call.id, "Товар добавлен в избранное!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_from_favorites_"))
def callback_remove_from_favorites(call):
    """Обрабатывает нажатия на кнопки удаления из избранного."""
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[3])  # Получаем ID товара
    remove_from_favorites(user_id, product_id)
    bot.answer_callback_query(call.id, "Товар удален из избранного!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_product_"))
def callback_show_product(call):
    """Выводит подробную информацию о товаре."""
    product_id = int(call.data.split("_")[2]) #извлекаем product_id
    user_id = call.from_user.id  # Получаем id пользователя
    show_product_details(product_id, call.message.chat.id, user_id)
    bot.answer_callback_query(call.id)  # Убираем "часики" на кнопке

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_products_"))
def callback_back_to_products(call):
    """Возвращает к списку товаров."""
    category = call.data.split("_")[3] #Получаем product_id

    products_keyboard = create_products_keyboard(category)
    bot.send_message(call.message.chat.id, text=f"Товары в категории '{category}':", reply_markup=products_keyboard)
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)  # Убираем "часики" на кнопке

@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def process_add_category(message):
    """Добавляет новую категорию в базу данных."""
    category_name = message.text
    if add_category(category_name):
        bot.send_message(message.chat.id, f"Категория '{category_name}' успешно добавлена.")
    else:
        bot.send_message(message.chat.id, "Ошибка: Категория с таким именем уже существует.")

def process_delete_category(message):
    """Удаляет категорию из базы данных."""
    category_name = message.text
    delete_category(category_name)
    bot.send_message(message.chat.id, f"Категория '{category_name}' успешно удалена.", reply_markup=create_admin_keyboard()) #Возвращаем админ-клавиатуру

def process_add_product_category(message):
    """Обрабатывает выбор категории для нового продукта."""
    category_name = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    category_id = cursor.fetchone()[0]
    conn.close()

    # Сохраняем category_id и переходим к запросу названия продукта
    bot.send_message(message.chat.id, "Введите название нового продукта:")
    bot.register_next_step_handler(message, process_add_product_name, category_id) #Теперь ждем название продукта

def process_add_product_name(message, category_id):
     """Обрабатывает ввод названия продукта и запрашивает описание."""
     product_name = message.text
     bot.send_message(message.chat.id, "Введите описание продукта:")
     bot.register_next_step_handler(message, process_add_product_description, category_id, product_name)

def process_add_product_description(message, category_id, product_name):
    """Обрабатывает ввод описания продукта и запрашивает цену."""
    product_description = message.text
    bot.send_message(message.chat.id, "Введите цену продукта:")
    bot.register_next_step_handler(message, process_add_product_price, category_id, product_name, product_description)

def process_add_product_price(message, category_id, product_name, product_description):
    """Обрабатывает ввод цены продукта и запрашивает URL изображения."""
    try:
        product_price = float(message.text)
        bot.send_message(message.chat.id, "Введите URL изображения продукта (или пропустите):")
        bot.register_next_step_handler(message, process_add_product_image, category_id, product_name, product_description, product_price)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный формат цены. Введите число.")
        bot.register_next_step_handler(message, process_add_product_price, category_id, product_name, product_description)

def process_add_product_image(message, category_id, product_name, product_description, product_price):
    """Обрабатывает ввод URL изображения продукта и запрашивает контакты продавца."""
    product_image = message.text
    bot.send_message(message.chat.id, "Введите контакты продавца:")
    bot.register_next_step_handler(message, process_finish_add_product, category_id, product_name, product_description, product_price, product_image)

def process_finish_add_product(message, category_id, product_name, product_description, product_price, product_image):
    """Завершает добавление продукта."""
    seller_contacts = message.text
    add_product(category_id, product_name, product_description, product_price, product_image, seller_contacts)
    bot.send_message(message.chat.id, f"Продукт '{product_name}' успешно добавлен.", reply_markup=create_admin_keyboard())

def process_delete_product(message):
    """Удаляет продукт из базы данных."""
    try:
        product_id = int(message.text)
        delete_product(product_id)
        bot.send_message(message.chat.id, f"Продукт с ID '{product_id}' успешно удален.", reply_markup=create_admin_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный формат ID продукта. Введите число.")

# --- Функции для работы с базой данных (не изменяются) ---
def show_product_details(product_id, chat_id, user_id):
    """Выводит подробную информацию о товаре."""
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
        bot.send_message(chat_id, "Товар не найден.")
        return

    product_name = product['name']
    product_description = product['description']
    product_price = product['price']
    product_image_url = product['image_url']
    seller_contacts = product['seller_contacts']
    category_name = product['category_name']  # Теперь у нас есть category_name

    is_in_favorites = is_product_in_favorites(user_id, product_id)

    markup = types.InlineKeyboardMarkup()

    if is_in_favorites:
        button_text = "Удалить из избранного"
        callback_data = f"remove_from_favorites_{product_id}"
    else:
        button_text = "Добавить в избранное"
        callback_data = f"add_to_favorites_{product_id}"

    fav_button = types.InlineKeyboardButton(button_text, callback_data=callback_data)
    back_to_products_button = types.InlineKeyboardButton("Назад к товарам", callback_data=f"back_to_products_{category_name}")
    markup.add(fav_button)
    markup.add(back_to_products_button)

    product_info = (
        f"*{product_name}*\n"
        f"{product_description}\n"
        f"{product_price:.2f} руб\n"
        f"Продавец: {seller_contacts}\n"
        f"id: {product_id}"
    )

    try:
        if product_image_url:
            #Сохраняем id сообщения в базе данных
            sent_message = bot.send_photo(chat_id, product_image_url, caption=product_info, parse_mode="Markdown", reply_markup=markup)
        else:
             sent_message = bot.send_message(chat_id, product_info, parse_mode="Markdown", reply_markup=markup)
        msg_id = sent_message.message_id

    except Exception as e:
        print(f"Ошибка при отправке фото: {e}")
        sent_message = bot.send_message(chat_id, product_info, parse_mode="Markdown", reply_markup=markup)
        msg_id = sent_message.message_id

def is_product_in_favorites(user_id, product_id):
    """Проверяет, находится ли товар в избранном пользователя."""
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

def get_category_name_by_product_id(product_id):
    """Получает название категории по ID продукта."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT category_id FROM products WHERE id = ?''', (product_id,))
    category_id = cursor.fetchone()
    if category_id is None:
        conn.close()
        return None  # Или какое-то значение по умолчанию, если категория не найдена
    category_id = category_id[0]
    cursor.execute('''SELECT name FROM categories WHERE id = ?''', (category_id,))
    category = cursor.fetchone()[0]
    conn.close()
    return category

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Отправляет приветственное сообщение и показывает категории."""
    user_id = message.from_user.id
    # Проверяем, есть ли пользователь в базе данных
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        # Если пользователя нет, создаем для него избранное
        get_or_create_user_favorites(user_id)

    welcome_message = (
        "Добро пожаловать в наш магазин всячины!\n"
        "У нас вы найдете всякую всячину со всего света,\n"
        "Выберите категорию, чтобы посмотреть товары:"
    )
    bot.reply_to(message, welcome_message, reply_markup=create_categories_keyboard())

# --- Обработчики callback-запросов ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_favorites_"))
def callback_add_to_favorites(call):
    """Обрабатывает нажатия на кнопки добавления в избранное."""
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[2])  # Получаем ID товара
    add_to_favorites(user_id, product_id)
    bot.answer_callback_query(call.id, "Товар добавлен в избранное!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_from_favorites_"))
def callback_remove_from_favorites(call):
    """Обрабатывает нажатия на кнопки удаления из избранного."""
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[2])  # Получаем ID товара
    remove_from_favorites(user_id, product_id)
    bot.answer_callback_query(call.id, "Товар удален из избранного!")

 # --- Обработчики callback-запросов ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_favorites_") or call.data.startswith("remove_from_favorites_"))
def callback_toggle_favorites(call):
    """Обрабатывает нажатия на кнопки добавления/удаления из избранного."""
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[2])  # Получаем ID товара
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data.startswith("add_to_favorites_"):
        add_to_favorites(user_id, product_id)
        is_in_favorites = True  # Теперь в избранном
    else:
        remove_from_favorites(user_id, product_id)
        is_in_favorites = False  # Теперь не в избранном

    bot.answer_callback_query(call.id)

    # Определяем текст и callback_data для новой кнопки
    if is_in_favorites:
        button_text = "Удалить из избранного"
        callback_data = f"remove_from_favorites_{product_id}"
    else:
        button_text = "Добавить в избранное"
        callback_data = f"add_to_favorites_{product_id}"

    # Создаем новую клавиатуру с обновленной кнопкой
    new_markup = types.InlineKeyboardMarkup()
    fav_button = types.InlineKeyboardButton(button_text, callback_data=callback_data)

    #category_name = get_category_name_by_product_id(product_id) #Получаем имя категории
    back_to_products_button = types.InlineKeyboardButton("Назад к товарам", callback_data=f"back_to_products_{get_category_name_by_product_id(product_id)}") # Кнопка "Назад"
    new_markup.add(fav_button)
    new_markup.add(back_to_products_button)

    # Редактируем сообщение, чтобы обновить клавиатуру
    try:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=new_markup)
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_product_"))
def callback_show_product(call):
    """Выводит подробную информацию о товаре."""
    product_id = int(call.data.split("_")[2]) #извлекаем product_id
    user_id = call.from_user.id  # Получаем id пользователя
    show_product_details(product_id, call.message.chat.id, user_id)
    bot.answer_callback_query(call.id)  # Убираем "часики" на кнопке

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_products_"))
def callback_back_to_products(call):
    """Возвращает к списку товаров."""
    category = call.data.split("_")[2] #Получаем category
    conn = get_db_connection()
    cursor = conn.cursor()
    products_keyboard = create_products_keyboard(category)
    bot.send_message(call.message.chat.id, text=f"Товары в категории '{category}':", reply_markup=products_keyboard)
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)  # Убираем "часики" на кнопке
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def callback_back_to_categories(call):
    """Возвращает к списку категорий."""
    bot.send_message(call.message.chat.id, text="Выберите категорию:", reply_markup=create_categories_keyboard())
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)  # Убираем "часики" на кнопке

# --- Обработчики административных команд ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """Вход в панель администратора."""
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Добро пожаловать в панель администратора!", reply_markup=create_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(func=lambda message: message.text == "Добавить категорию")
def ask_category_name(message):
    """Запрашивает название новой категории."""
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Введите название новой категории:")
        bot.register_next_step_handler(message, process_add_category) #После этого сообщения ждет ввода текста и вызывает функцию process_add_category

@bot.message_handler(func=lambda message: message.text == "Удалить категорию")
def ask_delete_category(message):
     """Запрашивает название категории для удаления."""
     if is_admin(message.from_user.id):
         conn = get_db_connection()
         cursor = conn.cursor()
         cursor.execute("SELECT name FROM categories")
         categories = [row[0] for row in cursor.fetchall()]
         conn.close()

         if not categories:
             bot.send_message(message.chat.id, "Нет категорий для удаления.")
             return

         keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
         for category in categories:
             keyboard.add(category)
         bot.send_message(message.chat.id, "Выберите категорию для удаления:", reply_markup=keyboard)
         bot.register_next_step_handler(message, process_delete_category)

@bot.message_handler(func=lambda message: message.text == "Добавить продукт")
def ask_add_product(message):
    """Запрашивает данные для добавления нового продукта."""
    if is_admin(message.from_user.id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not categories:
            bot.send_message(message.chat.id, "Сначала добавьте хотя бы одну категорию.")
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for category in categories:
            keyboard.add(category)
        bot.send_message(message.chat.id, "Выберите категорию для нового продукта:", reply_markup=keyboard)
        bot.register_next_step_handler(message, process_add_product_category) #После выбора категории переходим к следующему шагу


@bot.message_handler(func=lambda message: message.text == "Удалить продукт")
def ask_delete_product(message):
    """Запрашивает ID продукта для удаления."""
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Введите ID продукта для удаления:")
        bot.register_next_step_handler(message, process_delete_product)

# --- Основной цикл ---
if __name__ == '__main__':
    bot.infinity_polling()