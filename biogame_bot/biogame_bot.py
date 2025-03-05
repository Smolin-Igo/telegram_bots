import sqlite3
import telebot
from telebot import types
import random
import requests

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = "TELEGRAM_BOT_TOKEN"  # Замените на свой токен
DATABASE_PATH = 'db/bio_game.db'

bot = telebot.TeleBot(TOKEN)
bot.battle_state = {}  # {user_id: True/False}

# Подключение к БД
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
cursor = conn.cursor()

# ========================= КЛАСС ДЛЯ МОНСТРОВ =========================
class Monster:
    def __init__(self, id, name, power_base, hp_base, immu_base, level_modifier, description, photo_url, experience_reward, hp_reward, immu_reward):
        self.id = id
        self.name = name
        self.power_base = power_base
        self.hp_base = hp_base
        self.immu_base = immu_base
        self.level_modifier = level_modifier
        self.description = description
        self.photo_url = photo_url
        self.experience_reward = experience_reward
        self.immu_reward = immu_reward  # Добавляем immu_reward
        self.hp_reward = hp_reward  # Добавляем hp_reward
        self.power = 0
        self.hp = 0

    def calculate_stats(self, player_level):
        """Вычисляет характеристики монстра в зависимости от уровня игрока."""
        self.power = int(self.power_base + (player_level - 1) * 0.8 * self.level_modifier)
        self.hp = int(self.hp_base + (player_level - 1) * 2.5 * self.level_modifier)
        self.immu = int(self.immu_base + (player_level - 1) * 0.15 * self.level_modifier)
        self.immu = min(self.immu, 10)

    def get_description(self):
        """Возвращает описание монстра для отображения в игре."""
        return (f"{self.name}:\n"
                f"  *Сила: {self.power}*\n"
                f"  *Здоровье: {self.hp}*\n"
                f"  *Иммунитет: {self.immu}*\n"
                f" Описание: {self.description}")

# ========================= ФУНКЦИИ ДЛЯ РАБОТЫ С БД =========================

def db_table_val(user_id: int, user_name: str, user_surname: str, username: str, chat_id: int):
    """Добавляет нового пользователя в БД."""
    try:
        cursor.execute(
            'INSERT INTO test (user_id, user_name, user_surname, username, chat_id) VALUES (?, ?, ?, ?, ?)',
            (user_id, user_name, user_surname, username, chat_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении пользователя в БД: {e}")

def check_user_exists(username: str) -> bool:
    """Проверяет, существует ли пользователь в БД."""
    try:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM test WHERE username=?)", (username,))
        result = cursor.fetchone()
        return result[0] == 1
    except sqlite3.Error as e:
        print(f"Ошибка при проверке существования пользователя: {e}")
        return False

def hero_stats(us_id: int) -> str:
    """Возвращает статистику героя."""
    try:
        cursor.execute("SELECT hero_name, power, hp, immu, level, experience FROM test WHERE user_id = ?", (us_id,))
        stats = cursor.fetchone()
        if stats:
            hero_name, power, hp, immu, level, experience = stats
            return (f"Имя: {hero_name}\n"
                    f"Уровень: {level}\n"
                    f"Опыт: {experience}\n"
                    f"сила: {power}\n"
                    f"здоровье: {hp}\n"
                    f"иммунитет: {immu}"
                    )
        else:
            return "Организм не найден."
    except sqlite3.Error as e:
        print(f"Ошибка при получении статистики организма: {e}")
        return "Произошла ошибка при получении статистики организма."

def gain_experience(us_id: int, amount: int, chat_id: int):
    """Начисляет опыт персонажу и повышает уровень, если необходимо."""
    try:
        cursor.execute("SELECT experience, level, power, hp, immu, hero_name FROM test WHERE user_id=?", (us_id,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(chat_id, "Организм не найден.")
            return

        experience, level, power, hp, immu, hero_name = result
        experience += amount

        level_up_threshold = level * 100
        while experience >= level_up_threshold:
            level += 1
            experience -= level_up_threshold
            level_up_threshold = level * 100

            power += 1
            hp += 5
            bot.send_message(chat_id, f"🎉 Поздравляем! Ваш организм достиг {level} уровня!\n"
                                      f"Сила увеличена до {power}\n"
                                      f"Здоровье увеличено до {hp}")

        cursor.execute("UPDATE test SET experience=?, level=?, power=?, hp=?, immu=? WHERE user_id=?",
                       (experience, level, power, hp, immu, us_id))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при начислении опыта: {e}")
        bot.send_message(chat_id, "Произошла ошибка при начислении опыта.")

def get_random_monster(player_level):
    """Получает случайного монстра из базы данных."""
    try:
        cursor.execute("SELECT COUNT(*) FROM monsters")
        count = cursor.fetchone()[0]
        random_id = random.randint(1, count)  # Случайный id монстра

        cursor.execute(
            '''SELECT id, name, power_base, hp_base, immu_base, level_modifier, description, photo_url, experience_reward, hp_reward, immu_reward FROM monsters WHERE id = ?''',
            (random_id,))
        monster_data = cursor.fetchone()

        if monster_data:
            monster = Monster(id=monster_data[0], name=monster_data[1], power_base=monster_data[2],
                              hp_base=monster_data[3], immu_base=monster_data[4], level_modifier=monster_data[5],
                              description=monster_data[6], photo_url=monster_data[7], experience_reward=monster_data[8], hp_reward=monster_data[9], immu_reward=monster_data[10])
            monster.calculate_stats(player_level)
            return monster
        else:
            return None
    except sqlite3.Error as e:
        print(f"Ошибка при получении монстра из БД: {e}")
        return None

def create_explore_menu(chat_id):
    """Создает меню после нажатия кнопки 'Исследовать'."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Исследовать')
    item2 = types.KeyboardButton('Мой организм')
    item3 = types.KeyboardButton('/menu')  # Добавляем кнопку /menu
    markup.add( item3, item1, item2)
    return markup  # Возвращаем markup, а не сообщение

def menu_view(message):
    """Обработчик команды /menu."""
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Кнопка создания организма всегда отображается
    item1 = types.KeyboardButton('Создать организм')

    # Проверяем, создан ли у игрока организм
    if check_user_has_hero(message.from_user.id):
        # Если да, отображаем остальные кнопки
        item2 = types.KeyboardButton('Исследовать')
        item3 = types.KeyboardButton('Мой организм')
        item4 = types.KeyboardButton('/top')  # Кнопка рейтинга
        markup.add(item1, item2, item3, item4)
    else:
        markup.add(item1)

    bot.send_message(chat_id, 'Выберите команду', reply_markup=markup)

def check_user_has_hero(user_id):
    """Проверяет, есть ли у пользователя созданный организм (по наличию имени в hero_names)."""
    try:
        cursor.execute("SELECT 1 FROM hero_names WHERE user_id = ? AND is_active = 1", (user_id,))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        print(f"Ошибка при проверке наличия героя: {e}")
        return False

def create_hero(us_id: int, chat_id: int):
    """Создает героя для пользователя."""
    msg = bot.send_message(chat_id, "Как вы назовете свой организм?")
    bot.register_next_step_handler(msg, process_hero_name, us_id, chat_id)

def process_hero_name(message, us_id, chat_id):
    """Получает имя героя и создает его."""
    hero_name = message.text
    try:
        power = random.randint(2, 6)
        hp = random.randint(10, 50)
        immu = random.randint(0, 3)

        # Получаем информацию о предыдущем герое (если был)
        #cursor.execute("SELECT hero_name, level, experience, power, hp, immu FROM hero_names WHERE user_id = ? AND is_active = 1", (us_id,))
        cursor.execute("UPDATE hero_names SET is_active = 0 WHERE user_id = ? AND is_active = 1", (us_id,))

        # Добавляем нового героя в таблицу hero_names
        cursor.execute("INSERT INTO hero_names (user_id, hero_name, experience, level, is_active, power, hp, immu) VALUES (?, ?, 0, 1, 1, ?, ?, ?)", (us_id, hero_name, power, hp, immu))

        # Обновляем или создаем запись в таблице test с текущими значениями
        cursor.execute("UPDATE test SET power=?, hp=?, immu=?, level=1, experience=0, hero_name=? WHERE user_id=?", (power, hp, immu, hero_name, us_id))
        conn.commit()

        #Обновляем меню
        bot.send_message(chat_id, f"Организм {hero_name} создан!\n\n" + hero_stats(us_id), reply_markup=create_explore_menu(chat_id), parse_mode="Markdown")
    except sqlite3.Error as e:
        print(f"Ошибка при создании героя: {e}")
        bot.send_message(chat_id, "Произошла ошибка при создании героя.")

def is_valid_url(url):
    """Проверяет, является ли URL действительным и доступным."""
    try:
        response = requests.head(url)  # Используем HEAD-запрос для экономии трафика
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def jorney(us_id: int, chat_id: int) -> str:
    """Описание приключения."""
    dice = random.randint(0, 20)
    try:
        # Получаем уровень игрока
        cursor.execute("SELECT level FROM test WHERE user_id=?", (us_id,))
        player_level = cursor.fetchone()[0]

        if dice in range(0, 3):
            attribute = random.choice(['power', 'hp', 'immu'])
            effect = random.randint(1, 3)

            cursor.execute(f"SELECT {attribute} FROM test WHERE user_id=?", (us_id,))
            score = cursor.fetchone()[0]

            if attribute == 'immu':
                effect = score // 3 + effect
            elif attribute == 'hp':
                effect *= 5

            attr = score - effect
            cursor.execute(f"UPDATE test SET {attribute}=? WHERE user_id=?", (attr, us_id))
            conn.commit()
            return (f"* мутация! *\n"
                    f"-{effect} {attribute}")

        elif dice in range(3, 7):
            attribute = random.choice(['power', 'hp', 'immu'])
            effect = random.randint(1, 3)
            if attribute == 'hp':
                effect *= 10
            cursor.execute(f"SELECT {attribute} FROM test WHERE user_id=?", (us_id,))
            attr = cursor.fetchone()[0] + effect
            cursor.execute(f"UPDATE test SET {attribute}=? WHERE user_id=?", (attr, us_id))
            conn.commit()
            return (f"* развитие! *\n"
                    f"+{effect} {attribute}")

        elif dice in range(7, 21):
            # Проверяем, находится ли игрок уже в состоянии боя
            if us_id in bot.battle_state and bot.battle_state[us_id]:
                bot.send_message(chat_id, "Сначала завершите текущий бой!")
                return ""

            bot.battle_state[us_id] = True

            # Получаем случайного монстра из базы данных
            monster = get_random_monster(player_level)

            if not monster:
                bot.send_message(chat_id, "Не удалось найти монстра.")
                return ""

            cursor.execute("UPDATE test SET en_power=?, en_hp=?, en_immu=?, monster_type=? WHERE user_id=?",
                           (monster.power, monster.hp, monster.immu, monster.name, us_id))
            conn.commit()

            # Проверяем URL фотографии
            if is_valid_url(monster.photo_url):
                # Отправляем фотографию монстра
                bot.send_photo(chat_id, photo=monster.photo_url)
            else:
                bot.send_message(chat_id, f"Не удалось загрузить фотографию для монстра {monster.name}.")
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='атаковать!', callback_data='button_click_udar')
            keyboard.add(button)
            button2 = types.InlineKeyboardButton(text='убежать', callback_data='button_click_pobeg')
            keyboard.add(button2)

            bot.send_message(chat_id,
                             monster.get_description(),
                             reply_markup=keyboard, parse_mode="Markdown")
            return ""
        else:
            return "Ничего не произошло."
    except sqlite3.Error as e:
        print(f"Ошибка в приключении: {e}")
        return "Произошла ошибка во время приключения."

def fight(us_id: int, chat_id: int):
    """Описывает бой."""
    try:
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='атаковать!', callback_data='button_click_udar')
        keyboard.add(button)
        button2 = types.InlineKeyboardButton(text='убежать', callback_data='button_click_pobeg')
        keyboard.add(button2)

        cursor.execute(
            "SELECT power, hp, immu, en_power, en_hp, en_immu FROM test WHERE user_id=?", (us_id,))
        stats = cursor.fetchone()

        if stats:
            power, hp, immu, en_power, en_hp, en_immu = stats

            cursor.execute("SELECT monster_type FROM test WHERE user_id=?", (us_id,))
            monster_type = cursor.fetchone()[0]

            bot.send_message(chat_id,
                             f"""Противник: {monster_type}:\n
                    сила: {en_power}\n
                    здоровье: {en_hp}\n
                    иммунитет: {en_immu}\n\n
                << VS >>\n\n
            Ваш организм:\n
                    сила: {power}\n
                    здоровье: {hp}\n
                    иммунитет: {immu}""",
                             reply_markup=keyboard)
        else:
            bot.send_message(chat_id, "Не удалось получить информацию об организме или монстре.")
    except sqlite3.Error as e:
        print(f"Ошибка в бою: {e}")
        bot.send_message(chat_id, "Произошла ошибка во время боя.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        bot.send_message(chat_id, "Произошла непредвиденная ошибка.")


def process_attack(us_id: int, chat_id: int, call):
    """Обрабатывает нажатие кнопки "Атаковать!"."""
    message_id = call.message.message_id  # Получаем message_id

    try:
        cursor.execute(
            "SELECT power, hp, immu, en_power, en_hp, en_immu, monster_type, hero_name FROM test WHERE user_id=?",
            (us_id,))
        stats = cursor.fetchone()

        if not stats:
            bot.send_message(chat_id, "Не удалось получить информацию об организме или монстре.")
            return

        power, hp, immu, en_power, en_hp, en_immu, monster_type, hero_name = stats

        base_dodge_chance_player = immu / 100
        base_dodge_chance_monster = en_immu / 100

        player_damage = power
        if random.random() < 0.05:
            player_damage = power // 2  # Целочисленное деление
            bot.send_message(chat_id, "Критический промах! Очень слабый удар.")
        else:
            if random.random() < base_dodge_chance_monster:
                damage_reduction_amount = random.uniform(0.1, 0.5)
                player_damage = player_damage - int(player_damage * damage_reduction_amount) #Убираем float
                bot.send_message(chat_id, "Соперник частично заблокировал атаку!")
            else:
                if random.random() < 0.05:
                    player_damage = int(power * 1.5)  # Убираем float
                    bot.send_message(chat_id, "Критический удар! Очень сильный удар!")

        monster_damage = en_power
        if random.random() < 0.05:
            monster_damage = en_power // 2  # Целочисленное деление
            bot.send_message(chat_id, "Противник сделал критический промах!")
        else:
            if random.random() < base_dodge_chance_player:
                damage_reduction_amount = random.uniform(0.1, 0.5)
                monster_damage = monster_damage - int(monster_damage * damage_reduction_amount)  # Убираем float
                bot.send_message(chat_id, "Вы частично заблокировали атаку!")
            else:
                if random.random() < 0.05:
                    monster_damage = int(en_power * 1.5)  # Убираем float
                    bot.send_message(chat_id, "Противник нанес критический удар!")

        hp -= monster_damage
        en_hp -= player_damage

        cursor.execute("UPDATE test SET hp=?, en_hp=? WHERE user_id=?", (hp, en_hp, us_id))
        conn.commit()

        #Обновляем статистику
        cursor.execute("UPDATE hero_names SET power=?, hp=?, immu=? WHERE hero_name = (SELECT hero_name FROM test WHERE user_id = ?) AND user_id=?", (power, hp, immu, us_id, us_id))
        conn.commit()

        bot.answer_callback_query(call.id, 'Атака!')

        bot.send_message(chat_id, f"Вы нанесли {player_damage} урона.\n"
                                   f"Противник нанес {monster_damage} урона.\n")

        # message_id = call.message.message_id #Получаем message_id

        if en_hp <= 0:
            cursor.execute("SELECT monster_type FROM test WHERE user_id=?", (us_id,))
            monster_type = cursor.fetchone()[0]

            #ПОЛУЧАЕМ ID МОНСТРА
            cursor.execute("SELECT en_power, en_hp, en_immu, monster_type FROM test WHERE user_id=?", (us_id,))
            en_power, en_hp, en_immu, monster_type  = cursor.fetchone()

            #ДОСТАЕМ ЗНАЧЕНИЕ РЕВАРДА
            cursor.execute("SELECT experience_reward, immu_reward, hp_reward FROM monsters WHERE name=?", (monster_type,))
            exp_reward, immu_reward, hp_reward  = cursor.fetchone()
            bot.send_message(chat_id, f'{monster_type} повержен!\n'
                                       f'Иммунитет +{immu_reward}\n'
                                       f'Здоровье +{hp_reward}\n'
                                       f'Получено опыта: +{exp_reward}')
            cursor.execute("UPDATE test SET immu=?, hp=? WHERE user_id=?", (immu + immu_reward, hp + hp_reward, us_id))
            conn.commit()

            gain_experience(us_id, exp_reward, chat_id)

            bot.battle_state[us_id] = False
            if str(us_id) + '_immu' in bot.battle_state:
                del bot.battle_state[str(us_id) + '_immu']
            #Удаляем сообщение с кнопками
            try:
                bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")

        elif hp <= 0:
            bot.send_message(chat_id, 'Ваш организм погиб. Пора создать нового!')
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Создать организм', callback_data='create_hero')
            markup.add(button)

            bot.battle_state[us_id] = False
            if str(us_id) + '_immu' in bot.battle_state:
                del bot.battle_state[str(us_id) + '_immu']
            #Удаляем сообщение с кнопками
            try:
                bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
            #помечаем старого как мертвого
            #cursor.execute("UPDATE hero_names SET is_active = 0 WHERE user_id = (SELECT user_id FROM test WHERE user_id = ?) AND hero_name = (SELECT hero_name FROM test WHERE user_id = ?)", (us_id, us_id))
            cursor.execute("UPDATE hero_names SET is_active = 0 WHERE hero_name = (SELECT hero_name FROM test WHERE user_id = ?) AND user_id=?", (us_id, us_id))

            conn.commit()
            menu_view(call.message) #отрисовываем старое меню
            bot.send_message(chat_id, 'Выберите действие:', reply_markup=markup)

        else:
            # Удаляем сообщение с кнопками
            try:
                bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")

            fight(us_id, chat_id)

    except sqlite3.Error as e:
        print(f"Ошибка при обработке атаки: {e}")
        bot.send_message(chat_id, "Произошла ошибка во время атаки.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        bot.send_message(chat_id, "Произошла непредвиденная ошибка.")


def process_escape(us_id: int, chat_id: int, call):
    """Обрабатывает нажатие кнопки "Убежать"."""
    try:
        cursor.execute("SELECT immu FROM test WHERE user_id=?", (us_id,))
        immu = cursor.fetchone()[0]
        message_id = call.message.message_id  # ID сообщения для удаления

        bot.answer_callback_query(call.id, 'Побег!')
        bot.send_message(chat_id, 'Вы избежали столкновения, но потеряли 1 иммунитет.')
        cursor.execute("UPDATE test SET immu=? WHERE user_id=?", (immu - 1, us_id))
        conn.commit()

        bot.battle_state[us_id] = False

        # Удаляем сообщение о битве
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")

    except sqlite3.Error as e:
        print(f"Ошибка при попытке убежать: {e}")
        bot.send_message(chat_id, "Произошла ошибка во время побега.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        bot.send_message(chat_id, "Произошла непредвиденная ошибка.")

# ========================= ОБРАБОТЧИКИ СООБЩЕНИЙ =========================

@bot.message_handler(commands=['start'])
def start_message(message):
    """Обработчик команды /start."""
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item = types.KeyboardButton('Начали!')
    markup.add(item)
    bot.send_message(chat_id,
                     "Добро пожаловать в Bio-Game!\n"
                     "Мини-игра о микромире, выживании и эволюции.\n"
                     "Создайте своего персонажа и отправляйтесь исследовать!",
                     reply_markup=markup)


@bot.message_handler(commands=['menu'])
def menu_view(message):
    """Обработчик команды /menu."""
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Кнопка создания организма всегда отображается
    item1 = types.KeyboardButton('Создать организм')

    # Проверяем, создан ли у игрока организм
    if check_user_has_hero(message.from_user.id):
        # Если да, отображаем остальные кнопки
        item2 = types.KeyboardButton('Исследовать')
        item3 = types.KeyboardButton('Мой организм')
        item4 = types.KeyboardButton('/top')  # Кнопка рейтинга
        markup.add(item1, item2, item3, item4)
    else:
        markup.add(item1)

    bot.send_message(chat_id, 'Выберите команду', reply_markup=markup)


@bot.message_handler(commands=['top'])
def show_top_rating(message):
    """Отображает топ-10 игроков по рейтингу."""
    try:
        cursor.execute("""
            SELECT
                hn.hero_name,
                t.level,
                t.power,
                t.hp,
                t.immu,
                (t.level * 1000) + t.experience AS rating
            FROM hero_names hn
            JOIN test t ON hn.user_id = t.user_id
            WHERE hn.is_active = 1
            ORDER BY rating DESC
            LIMIT 10
        """)
        top_players = cursor.fetchall()

        if not top_players:
            bot.send_message(message.chat.id, "Пока нет данных для рейтинга.")
            return

        response = "🏆 *Топ-10 организмов* 🏆\n\n"
        for i, (hero_name, level, power, hp, immu, rating) in enumerate(top_players):
            response += (f"{i + 1}. *{hero_name}* (lvl: {level})\n"
                         f"   power: {power}, hp: {hp}, immu: {immu}\n")

        bot.send_message(message.chat.id, response, parse_mode="Markdown")

    except sqlite3.Error as e:
        print(f"Ошибка при получении рейтинга: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении рейтинга.")



# ========================= ОБРАБОТЧИК CALLBACK-ЗАПРОСОВ =========================

@bot.callback_query_handler(func=lambda call: call.data == 'create_hero')
def create_hero_callback(call):
    """Обработчик нажатия на кнопку "Создать персонажа"."""
    us_id = call.message.chat.id
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id, "Создаем новый организм...")

    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
    create_hero(us_id, chat_id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    """Обработчик всех callback-запросов."""
    us_id = call.message.chat.id
    chat_id = call.message.chat.id

    if call.data == 'button_click_udar':
        process_attack(us_id, chat_id, call)
    elif call.data == 'button_click_pobeg':
        process_escape(us_id, chat_id, call)


# ========================= ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ =========================

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    """Обработчик текстовых сообщений."""
    chat_id = message.chat.id
    us_id = message.from_user.id
    username = message.from_user.username

    if message.text.lower() == 'начали!':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item = types.KeyboardButton(r'/menu')
        markup.add(item)
        bot.send_message(chat_id, 'Отлично, вы готовы к приключениям!',
                         reply_markup=markup)

        us_name = message.from_user.first_name
        us_sname = message.from_user.last_name

        if check_user_exists(username):
            print(f"Пользователь {username} уже существует.")
        else:
            print(f"Пользователь {username} не найден. Добавляем в БД.")
            db_table_val(user_id=us_id, user_name=us_name, user_surname=us_sname, username=username, chat_id=chat_id)

    elif message.text == 'Создать организм':
            create_hero(us_id, chat_id)
            # menu_view(message) #Обновляем меню после создания
    elif message.text == 'Исследовать':
        if us_id in bot.battle_state and bot.battle_state[us_id]:
            bot.send_message(chat_id, "Сначала завершите текущее столкновение!")
        else:
            bot.send_message(chat_id, jorney(us_id, chat_id), reply_markup=create_explore_menu(
                chat_id))  # journey запускается после отображения нового меню
    elif message.text == 'Мой организм':
        bot.send_message(chat_id, hero_stats(us_id))


# ========================= ЗАПУСК БОТА =========================

try:
    bot.polling(none_stop=True)
except Exception as e:
    print(f"Произошла ошибка при запуске бота: {e}")
finally:
    conn.close()
    print("Соединение с БД закрыто.")