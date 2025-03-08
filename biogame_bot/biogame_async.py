import asyncio
import os
import random
import sqlite3
import requests

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = "7542463055:AAFdKLIzZBXfpK4TEGusWGavH5rn2F91CyU"  # Замените на свой токен
DATABASE_PATH = 'db/bio_game.db'  # Укажите путь к вашей базе данных
# ========================= КОНЕЦ КОНФИГУРАЦИИ =========================

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

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
        self.immu_reward = immu_reward
        self.hp_reward = hp_reward
        self.power = 0
        self.hp = 0
        self.immu = 0

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

# FSM State
class Form(StatesGroup):
    start = State()
    create_hero_name = State()
    exploration = State()

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

async def check_user_exists(username: str) -> bool:
    """Проверяет, существует ли пользователь в БД."""
    try:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM test WHERE username=?)", (username,))
        result = cursor.fetchone()
        return result[0] == 1
    except sqlite3.Error as e:
        print(f"Ошибка при проверке существования пользователя: {e}")
        return False

async def hero_stats(us_id: int) -> str:
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

async def gain_experience(us_id: int, amount: int, chat_id: int, bot: Bot):
    """Начисляет опыт персонажу и повышает уровень, если необходимо."""
    try:
        cursor.execute("SELECT experience, level, power, hp, immu, hero_name FROM test WHERE user_id=?", (us_id,))
        result = cursor.fetchone()
        if not result:
            await bot.send_message(chat_id, "Организм не найден.")
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
            await bot.send_message(chat_id, f"🎉 Поздравляем! Ваш организм достиг {level} уровня!\n"
                                      f"Сила увеличена до {power}\n"
                                      f"Здоровье увеличено до {hp}")

        cursor.execute("UPDATE test SET experience=?, level=?, power=?, hp=?, immu=? WHERE user_id=?",
                       (experience, level, power, hp, immu, us_id))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при начислении опыта: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при начислении опыта.")

async def get_random_monster(player_level):
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

def create_explore_menu():
    """Создает меню после нажатия кнопки 'Исследовать'."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Исследовать")],
        [KeyboardButton(text="Мой организм")],
        [KeyboardButton(text="/menu")]
    ])
    return markup

async def check_user_has_hero(user_id):
    """Проверяет, есть ли у пользователя созданный организм (по наличию имени в hero_names)."""
    try:
        cursor.execute("SELECT 1 FROM hero_names WHERE user_id = ? AND is_active = 1", (user_id,))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        print(f"Ошибка при проверке наличия героя: {e}")
        return False

async def create_hero(us_id: int, bot: Bot, state: FSMContext):
    """Создает героя для пользователя."""
    await bot.send_message(us_id, "Как вы назовете свой организм?")
    await state.set_state(Form.create_hero_name)

def is_valid_url(url):
    """Проверяет, является ли URL действительным и доступным."""
    try:
        response = requests.head(url)  # Используем HEAD-запрос для экономии трафика
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

async def jorney(us_id: int, bot: Bot):
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
            monster = await get_random_monster(player_level)

            if not monster:
                return "Не удалось найти монстра."

            cursor.execute("UPDATE test SET en_power=?, en_hp=?, en_immu=?, monster_type=? WHERE user_id=?",
                           (monster.power, monster.hp, monster.immu, monster.name, us_id))
            conn.commit()

            # Проверяем URL фотографии
            if is_valid_url(monster.photo_url):
                # Отправляем фотографию монстра
                await bot.send_photo(us_id, photo=monster.photo_url, caption=monster.get_description(), parse_mode="Markdown", reply_markup=create_battle_keyboard())
            else:
                await bot.send_message(us_id, f"Не удалось загрузить фотографию для монстра {monster.name}.\n{monster.get_description()}", parse_mode="Markdown", reply_markup=create_battle_keyboard())
            return ""

        else:
            return "Ничего не произошло."
    except sqlite3.Error as e:
        print(f"Ошибка в приключении: {e}")
        return "Произошла ошибка во время приключения."

def create_battle_keyboard():
    """Создает клавиатуру для битвы."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='Атаковать!', callback_data='attack'))
    builder.add(InlineKeyboardButton(text='Убежать', callback_data='escape'))
    builder.adjust(2)
    return builder.as_markup()

async def process_attack(us_id: int, call: types.CallbackQuery, bot: Bot):
    """Обрабатывает нажатие кнопки "Атаковать!"."""
    try:
        cursor.execute(
            "SELECT power, hp, immu, en_power, en_hp, en_immu, monster_type, hero_name FROM test WHERE user_id=?",
            (us_id,))
        stats = cursor.fetchone()

        if not stats:
            await bot.send_message(us_id, "Не удалось получить информацию об организме или монстре.")
            return

        power, hp, immu, en_power, en_hp, en_immu, monster_type, hero_name = stats

        base_dodge_chance_player = immu / 100
        base_dodge_chance_monster = en_immu / 100

        player_damage = power
        if random.random() < 0.05:
            player_damage = power // 2  # Целочисленное деление
            await bot.send_message(us_id, "Критический промах! Очень слабый удар.")
        else:
            if random.random() < base_dodge_chance_monster:
                damage_reduction_amount = random.uniform(0.1, 0.5)
                player_damage = player_damage - int(player_damage * damage_reduction_amount) #Убираем float
                await bot.send_message(us_id, "Соперник частично заблокировал атаку!")
            else:
                if random.random() < 0.05:
                    player_damage = int(power * 1.5)  # Убираем float
                    await bot.send_message(us_id, "Критический удар! Очень сильный удар!")

        monster_damage = en_power
        if random.random() < 0.05:
            monster_damage = en_power // 2  # Целочисленное деление
            await bot.send_message(us_id, "Противник сделал критический промах!")
        else:
            if random.random() < base_dodge_chance_player:
                damage_reduction_amount = random.uniform(0.1, 0.5)
                monster_damage = monster_damage - int(monster_damage * damage_reduction_amount)  # Убираем float
                await bot.send_message(us_id, "Вы частично заблокировали атаку!")
            else:
                if random.random() < 0.05:
                    monster_damage = int(en_power * 1.5)  # Убираем float
                    await bot.send_message(us_id, "Противник нанес критический удар!")

        hp -= monster_damage
        en_hp -= player_damage

        cursor.execute("UPDATE test SET hp=?, en_hp=? WHERE user_id=?", (hp, en_hp, us_id))
        conn.commit()

        #Обновляем статистику
        cursor.execute("UPDATE hero_names SET power=?, hp=?, immu=? WHERE hero_name = (SELECT hero_name FROM test WHERE user_id = ?) AND user_id=?", (power, hp, immu, us_id, us_id))
        conn.commit()

        await bot.answer_callback_query(call.id, 'Атака!')

        await bot.send_message(us_id, f"Вы нанесли {player_damage} урона.\n"
                                   f"Противник нанес {monster_damage} урона.\n")
        if en_hp <= 0:
            cursor.execute("SELECT monster_type FROM test WHERE user_id=?", (us_id,))
            monster_type = cursor.fetchone()[0]

            #ПОЛУЧАЕМ ID МОНСТРА
            cursor.execute("SELECT en_power, en_hp, en_immu, monster_type FROM test WHERE user_id=?", (us_id,))
            en_power, en_hp, en_immu, monster_type  = cursor.fetchone()

            #ДОСТАЕМ ЗНАЧЕНИЕ РЕВАРДА
            cursor.execute("SELECT experience_reward, immu_reward, hp_reward FROM monsters WHERE name=?", (monster_type,))
            exp_reward, immu_reward, hp_reward  = cursor.fetchone()
            await bot.send_message(us_id, f'{monster_type} повержен!\n'
                                       f'Иммунитет +{immu_reward}\n'
                                       f'Здоровье +{hp_reward}\n'
                                       f'Получено опыта: +{exp_reward}')
            cursor.execute("UPDATE test SET immu=?, hp=? WHERE user_id=?", (immu + immu_reward, hp + hp_reward, us_id))
            conn.commit()

            await gain_experience(us_id, exp_reward, us_id, bot)

        elif hp <= 0:
            await bot.send_message(us_id, 'Ваш организм погиб. Пора создать нового!')
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Создать организм', callback_data='create_hero')]])

            #помечаем старого как мертвого
            cursor.execute("UPDATE hero_names SET is_active = 0 WHERE hero_name = (SELECT hero_name FROM test WHERE user_id = ?) AND user_id=?", (us_id, us_id))

            conn.commit()
            await menu_view(us_id, bot,create_start_menu()) #отрисовываем старое меню
            await bot.send_message(us_id, 'Выберите действие:', reply_markup=markup)

        else:
            await bot.send_message(us_id,  f"Противник: {monster_type} \n "
                                           f"сила: {en_power} \n "
                                           f"здоровье: {en_hp} \n "
                                           f"иммунитет: {en_immu} \n"
                                           f"\nВы: \n "
                                           f"сила: {power} \n "
                                           f"здоровье: {hp} \n "
                                           f"иммунитет: {immu}",
                                   reply_markup=create_battle_keyboard())

    except sqlite3.Error as e:
        print(f"Ошибка при обработке атаки: {e}")
        await bot.send_message(us_id, "Произошла ошибка во время атаки.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        await bot.send_message(us_id, "Произошла непредвиденная ошибка.")

async def process_escape(us_id: int, call: types.CallbackQuery, bot: Bot):
    """Обрабатывает нажатие кнопки "Убежать"."""
    try:
        cursor.execute("SELECT immu FROM test WHERE user_id=?", (us_id,))
        immu = cursor.fetchone()[0]
        await bot.answer_callback_query(call.id, 'Побег!')
        await bot.send_message(us_id, 'Вы избежали столкновения, но потеряли 1 иммунитет.')
        cursor.execute("UPDATE test SET immu=? WHERE user_id=?", (immu - 1, us_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при попытке убежать: {e}")
        await bot.send_message(us_id, "Произошла ошибка во время побега.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        await bot.send_message(us_id, "Произошла непредвиденная ошибка.")

def create_start_menu():
    """Создает главное меню."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Создать организм")],
    ])
    return markup

async def menu_view(user_id: int, bot: Bot, reply_markup = None):
    """Отображает меню."""
    markup = reply_markup or ReplyKeyboardMarkup(resize_keyboard=True)
    if await check_user_has_hero(user_id):
        markup.keyboard.append([KeyboardButton(text="Исследовать"), KeyboardButton(text="Мой организм")])
        markup.keyboard.append([KeyboardButton(text="/top")])

    await bot.send_message(user_id, 'Выберите команду', reply_markup=markup)

# ========================= ОБРАБОТЧИКИ СООБЩЕНИЙ =========================
@dp.message(CommandStart())
async def start_message(message: types.Message, state: FSMContext):
    """Обработчик команды /start."""
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_surname = message.from_user.last_name
    username = message.from_user.username
    us_id = message.from_user.id

    reply_markup = create_start_menu()
    await message.reply("Добро пожаловать в Bio-Game!\n"
                        "Мини-игра о микромире, выживании и эволюции.\n"
                        "Создайте своего персонажа и отправляйтесь исследовать!",
                        reply_markup=reply_markup)

    if not await check_user_exists(username):
        db_table_val(user_id=us_id, user_name=user_name, user_surname=user_surname, username=username, chat_id=chat_id)

    await state.set_state(Form.start)

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    """Обработчик команды /menu."""
    user_id = message.from_user.id
    await menu_view(user_id, bot, create_start_menu())

@dp.message(Command("top"))
async def show_top_rating(message: types.Message):
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
            await bot.send_message(message.chat.id, "Пока нет данных для рейтинга.")
            return

        response = "🏆 *Топ-10 организмов* 🏆\n\n"
        for i, (hero_name, level, power, hp, immu, rating) in enumerate(top_players):
            response += (f"{i + 1}. *{hero_name}* (lvl: {level})\n"
                         f"   power: {power}, hp: {hp}, immu: {immu}\n")

        await bot.send_message(message.chat.id, response, parse_mode="Markdown")

    except sqlite3.Error as e:
        print(f"Ошибка при получении рейтинга: {e}")
        await bot.send_message(message.chat.id, "Произошла ошибка при получении рейтинга.")

@dp.message(F.text == "Создать организм")
async def create_hero_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Запускает процесс создания организма."""
    await create_hero(message.from_user.id, bot, state)

@dp.message(Form.create_hero_name, F.text)
async def process_hero_name(message: types.Message, state: FSMContext, bot: Bot):
    """Получает имя героя и создает его."""
    hero_name = message.text
    us_id = message.from_user.id
    chat_id = message.chat.id
    try:
        power = random.randint(2, 6)
        hp = random.randint(10, 50)
        immu = random.randint(0, 3)
        cursor.execute("UPDATE hero_names SET is_active = 0 WHERE user_id = ? AND is_active = 1", (us_id,))
        cursor.execute("INSERT INTO hero_names (user_id, hero_name, experience, level, is_active, power, hp, immu) VALUES (?, ?, 0, 1, 1, ?, ?, ?)", (us_id, hero_name, power, hp, immu))

        cursor.execute("UPDATE test SET power=?, hp=?, immu=?, level=1, experience=0, hero_name=? WHERE user_id=?", (power, hp, immu, hero_name, us_id))
        conn.commit()

        await bot.send_message(chat_id, f"Организм {hero_name} создан!\n\n" + await hero_stats(us_id), reply_markup=create_explore_menu(), parse_mode="Markdown")
        await state.clear()
    except sqlite3.Error as e:
        print(f"Ошибка при создании героя: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при создании героя.")

@dp.message(F.text == 'Исследовать')
async def explore_handler(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик кнопки 'Исследовать'."""
    user_id = message.from_user.id
    if await check_user_has_hero(user_id):
        report = await jorney(user_id, bot)
        await message.reply(report, reply_markup=create_explore_menu(), parse_mode="Markdown")
        await state.set_state(Form.exploration)
    else:
        await message.reply("Сначала создайте свой организм!")

@dp.message(F.text == 'Мой организм')
async def my_hero_handler(message: types.Message):
    """Обработчик кнопки 'Мой организм'."""
    stats = await hero_stats(message.from_user.id)
    await message.reply(stats)

# ========================= ОБРАБОТЧИК CALLBACK-ЗАПРОСОВ =========================
@dp.callback_query(F.data == 'create_hero')
async def create_hero_callback(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик нажатия на кнопку "Создать персонажа"."""
    user_id = call.message.chat.id
    await bot.answer_callback_query(call.id, "Создаем новый организм...")
    await bot.edit_message_reply_markup(chat_id=user_id, message_id=call.message.message_id, reply_markup=None)
    await create_hero(user_id, bot, state)

@dp.callback_query(F.data == 'attack')
async def attack_callback(call: types.CallbackQuery, bot: Bot):
    """Обработчик нажатия на кнопку "Атаковать!"."""
    user_id = call.message.chat.id
    await process_attack(user_id, call, bot)

@dp.callback_query(F.data == 'escape')
async def escape_callback(call: types.CallbackQuery, bot: Bot):
    """Обработчик нажатия кнопки "Убежать"."""
    user_id = call.message.chat.id
    await process_escape(user_id, call, bot)

# ========================= ЗАПУСК БОТА =========================
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Произошла ошибка при запуске бота: {e}")
    finally:
        conn.close()
        print("Соединение с БД закрыто.")

if __name__ == "__main__":
    asyncio.run(main())