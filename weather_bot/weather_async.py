import asyncio
import os
from dotenv import load_dotenv
import pytz
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest
import aiohttp

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен и API key из переменных окружения
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY")

if not BOT_TOKEN or not OPENWEATHERMAP_API_KEY:
    print("Ошибка: Необходимы переменные окружения TELEGRAM_BOT_TOKEN и OPENWEATHERMAP_API_KEY.")
    exit()

# Инициализируем бот и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция для создания клавиатуры
def create_keyboard():
    """Создает клавиатуру с кнопками."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [
            types.KeyboardButton(text="Москва"),
            types.KeyboardButton(text="Санкт-Петербург"),
            types.KeyboardButton(text="Минск")
        ],
        [
            types.KeyboardButton(text="Екатеринбург"),
            types.KeyboardButton(text="Казань"),
            types.KeyboardButton(text="Нижний Новгород")
        ],
        [
            types.KeyboardButton(text="Челябинск"),
            types.KeyboardButton(text="Омск"),
            types.KeyboardButton(text="Самара"),
            types.KeyboardButton(text="Ростов-на-Дону")
        ]
    ])
    return markup

def hpa_to_atm(hpa):
    """Переводит давление из гектопаскалей в атмосферы."""
    return hpa / 1013.25

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """Отправляет приветственное и справочное сообщение."""
    markup = create_keyboard()
    await message.answer(
        f"Привет, {message.from_user.first_name} 👋!\n"
        "Я бот погоды. Выберите город или отправьте мне его название.\n\n"
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/help - получить справку",
        reply_markup=markup
    )
# Обработчик команды /start
@dp.message(Command("help"))
async def command_help_handler(message: types.Message) -> None:
    """Отправляет приветственное и справочное сообщение."""

    await message.answer(
        f"Я бот погоды. Выберите город или отправьте его название.\n"

    )

async def get_weather(city: str, message: types.Message) -> None:
    """Получает погоду и прогноз для указанного города."""
    try:
        # 1. Текущая погода
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ru"
        async with aiohttp.ClientSession() as session:
            async with session.get(current_url) as current_response:
                current_response.raise_for_status() # Проверяем на ошибки
                current_data = await current_response.json()

        if current_data["cod"] != 200:
            await message.reply("Город не найден, попробуйте еще раз.")
            return

        temperature = current_data["main"]["temp"]
        feels_like = current_data["main"]["feels_like"]
        description = current_data["weather"][0]["description"]
        pressure_hpa = current_data["main"]["pressure"]
        pressure_atm = hpa_to_atm(pressure_hpa)  # Пересчитываем давление
        humidity = current_data["main"]["humidity"]
        wind_speed = current_data["wind"]["speed"]
        visibility = current_data.get("visibility", "Нет данных") #видимость может отсутствовать

        # 2. Прогноз погоды
        # Получаем координаты города
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHERMAP_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.get(geo_url) as geo_response:
                geo_response.raise_for_status()
                geo_data = await geo_response.json()

        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]

        # Формируем URL для запроса прогноза погоды
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ru"
        async with aiohttp.ClientSession() as session:
            async with session.get(forecast_url) as forecast_response:
                forecast_response.raise_for_status()
                forecast_data = await forecast_response.json()

        # Печатаем прогноз на ближайшие 3 часа
        forecast = forecast_data['list'][0] #Самый ближайший прогноз
        forecast_temperature = forecast['main']['temp']
        forecast_description = forecast['weather'][0]['description']
        forecast_time_utc = forecast['dt_txt'] #Время в UTC

        # Определяем часовой пояс города (пример, нужно уточнять для каждого города!)
        if city == "Москва" or city == "Санкт-Петербург" or city == "Казань" or city == "Нижний Новгород" or city == "Ростов-на-Дону":
            timezone = pytz.timezone('Europe/Moscow')
        elif city == "Новосибирск":
            timezone = pytz.timezone('Asia/Novosibirsk')
        elif city == "Екатеринбург" or city == "Челябинск":
            timezone = pytz.timezone('Asia/Yekaterinburg')
        elif city == "Омск":
            timezone = pytz.timezone('Asia/Omsk')
        elif city == "Самара":
            timezone = pytz.timezone('Europe/Samara')
        else:
            timezone = pytz.utc #Если город не известен, используем UTC

        # Преобразуем время в местный часовой пояс
        forecast_time_utc_dt = datetime.strptime(forecast_time_utc, '%Y-%m-%d %H:%M:%S') #Преобразуем строку во время
        forecast_time_local_dt = pytz.utc.localize(forecast_time_utc_dt).astimezone(timezone) #Локализиурем и переводим во временную зону
        forecast_time_local = forecast_time_local_dt.strftime('%Y-%m-%d %H:%M:%S') #Форматируем в строку

        # 3. Формируем и отправляем сообщение
        weather_info = (
            f"Погода в городе {city}:\n"
            f"Температура: {temperature}°C\n"
            f"Ощущается как: {feels_like}°C\n"
            f"Описание: {description}\n"
            f"Влажность: {humidity}%\n"
            f"Давление: {pressure_hpa} гПа ({pressure_atm:.2f} атм)\n"
            f"Скорость ветра: {wind_speed} м/с\n"
            f"Видимость: {visibility} м\n"
            f"\nПрогноз на {forecast_time_local} (Местное время):\n"
            f"Температура: {forecast_temperature}°C\n"
            f"Описание: {forecast_description}"
        )
        await message.reply(weather_info)

    except aiohttp.ClientError as e:
        print(f"Ошибка при запросе к API: {e}")
        await message.reply("Произошла ошибка при получении погоды. Попробуйте позже.")
    except (KeyError, IndexError) as e:
        print(f"Ошибка при обработке данных API: {e}")
        await message.reply("Произошла ошибка при обработке данных о погоде. Пожалуйста, попробуйте другой город.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        await message.reply("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

# Обработчик текстовых сообщений
@dp.message(F.text)
async def handle_message(message: types.Message):
     await get_weather(message.text, message)

# Функция запуска бота
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())