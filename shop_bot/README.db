# README.md

## Описание

Этот скрипт представляет собой Telegram-бота для управления магазином всякой всячины. Он позволяет пользователям просматривать товары по категориям, добавлять товары в избранное, а администраторам - управлять категориями и товарами.

## Предварительные требования

*   Python 3.6 или выше.
*   Установленный менеджер пакетов `pip`.
*   Установленные Python-библиотеки:
    *   `telebot` (PyTelegramBotAPI)
    *   `python-dotenv`
    *   `sqlite3` (обычно входит в стандартную библиотеку Python)

## Установка

1.  **Клонируйте репозиторий (если код хранится в репозитории):**

    ```bash
    git clone <URL_вашего_репозитория>
    cd <название_каталога_репозитория>
    ```

2.  **Установите зависимости:**

    ```bash
    pip install pyTelegramBotAPI python-dotenv
    ```

3.  **Настройте переменные окружения:**

    *   Создайте файл `.env` в корневом каталоге проекта.
    *   Добавьте в `.env` токен вашего Telegram-бота:

        ```
        TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
        ```

        Замените `YOUR_TELEGRAM_BOT_TOKEN` на реальный токен вашего бота, полученный от BotFather.

4.  **Настройте базу данных SQLite:**

    *   Укажите путь к базе данных в функции `get_db_connection()`:

        ```python
        def get_db_connection():
            conn = sqlite3.connect('db/shop.db')  # Укажите правильный путь!
            conn.row_factory = sqlite3.Row
            return conn
        ```

    *   База данных должна содержать следующие таблицы:

        *   `categories` (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)
        *   `products` (id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT NOT NULL, description TEXT, price REAL, image_url TEXT, seller_contacts TEXT, FOREIGN KEY (category_id) REFERENCES categories (id))
        *   `admins` (id INTEGER PRIMARY KEY) - Содержит ID администраторов бота
        *   `users` (id INTEGER PRIMARY KEY, favorite_id INTEGER, FOREIGN KEY (favorite_id) REFERENCES favorites (id)) - Таблица пользователей для хранения избранного
        *   `favorites` (id INTEGER PRIMARY KEY) - Таблица избранного
        *   `favorite_items` (favorite_id INTEGER, product_id INTEGER, PRIMARY KEY (favorite_id, product_id), FOREIGN KEY (favorite_id) REFERENCES favorites (id), FOREIGN KEY (product_id) REFERENCES products (id)) - Таблица для связи избранного с продуктами

## Запуск

Запустите скрипт Python:

```bash
python ваш_скрипт.py  # Пример: python shop_bot.py