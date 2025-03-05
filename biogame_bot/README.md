# Telegram-бот BioGame

Этот скрипт представляет собой Telegram-бота, реализующего мини-игру Bio-Game, в которой игроки создают персонажей (организмы), исследуют мир и сражаются с монстрами.

## Требования

*   Python 3.x
*   Установленные библиотеки:
    *   `telebot` (PyTelegramBotAPI)
    *   `sqlite3`
    *   `random`
    *   `requests`

## Установка

1.  Установите необходимые библиотеки:
    ```bash
    pip install pyTelegramBotAPI requests
    ```

2.  Настройте токен Telegram-бота:
    *   Замените `"TELEGRAM_BOT_TOKEN"` в переменной `TOKEN` на токен, полученный от BotFather.
        ```python
        TOKEN = "TELEGRAM_BOT_TOKEN"  # Замените на свой токен
        ```

3.  Настройте базу данных SQLite:
    *   Укажите путь к базе данных в переменной `DATABASE_PATH`.
    *   Создайте базу данных `bio_game.db` со следующими таблицами (или убедитесь, что они существуют):

        *   `test` (user_id INTEGER PRIMARY KEY, user_name TEXT, user_surname TEXT, username TEXT, chat_id INTEGER, power INTEGER, hp INTEGER, immu INTEGER, level INTEGER, experience INTEGER, hero_name TEXT, en_power INTEGER, en_hp INTEGER, en_immu INTEGER, monster_type TEXT)
        *   `hero_names` (user_id INTEGER, hero_name TEXT, experience INTEGER, level INTEGER, is_active INTEGER, power INTEGER, hp INTEGER, immu INTEGER)
        *   `monsters` (id INTEGER PRIMARY KEY, name TEXT, power_base INTEGER, hp_base INTEGER, immu_base INTEGER, level_modifier REAL, description TEXT, photo_url TEXT, experience_reward INTEGER, hp_reward INTEGER, immu_reward INTEGER)

## Запуск

Запустите скрипт Python:

```bash
python ваш_скрипт.py  # Например: python bio_game_bot.py