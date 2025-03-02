import telebot
import requests
import os
from dotenv import load_dotenv
import pytz
from datetime import datetime

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен и API key из переменных окружения
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY")

if not BOT_TOKEN or not OPENWEATHERMAP_API_KEY:
    print("Ошибка: Необходимы переменные окружения TELEGRAM_BOT_TOKEN и OPENWEATHERMAP_API_KEY.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

def hpa_to_atm(hpa):
    """Переводит давление из гектопаскалей в атмосферы."""
    return hpa / 1013.25

def create_keyboard():
    """Создает клавиатуру с кнопками."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = telebot.types.KeyboardButton("Москва")
    item2 = telebot.types.KeyboardButton("Санкт-Петербург")
    item3 = telebot.types.KeyboardButton("Новосибирск")
    item4 = telebot.types.KeyboardButton("Екатеринбург")
    item5 = telebot.types.KeyboardButton("Казань")
    item6 = telebot.types.KeyboardButton("Нижний Новгород")
    item7 = telebot.types.KeyboardButton("Челябинск")
    item8 = telebot.types.KeyboardButton("Омск")
    item9 = telebot.types.KeyboardButton("Самара")
    item10 = telebot.types.KeyboardButton("Ростов-на-Дону")

    markup.add(item1, item2, item3, item4, item5)
    markup.add(item6, item7, item8, item9, item10)
    return markup

@bot.message_handler(commands=['start', 'help', 'menu'])
def send_welcome(message):
    """Отправляет приветственное сообщение и показывает меню."""
    markup = create_keyboard()
    bot.reply_to(message, "Привет! Я бот погоды. Выберите город или отправьте мне название города.",
                 reply_markup=markup)


def get_weather(message, city):
    """Получает погоду и прогноз для указанного города."""
    try:
        # 1. Текущая погода
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ru"
        current_response = requests.get(current_url)
        current_response.raise_for_status() # Проверяем на ошибки
        current_data = current_response.json()

        if current_data["cod"] != 200:
            bot.reply_to(message, "Город не найден, попробуйте еще раз.")
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
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]

        # Формируем URL для запроса прогноза погоды
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ru"
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

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
            f"**Погода в городе {city}:**\n"
            f"Температура: {temperature}°C\n"
            f"Ощущается как: {feels_like}°C\n"
            f"Описание: {description}\n"
            f"Влажность: {humidity}%\n"
            f"Давление: {pressure_hpa} гПа ({pressure_atm:.2f} атм)\n"
            f"Скорость ветра: {wind_speed} м/с\n"
            f"Видимость: {visibility} м\n"
            f"\n**Прогноз на {forecast_time_local}: (Местное время)**\n"
            f"Температура: {forecast_temperature}°C\n"
            f"Описание: {forecast_description}"
        )
        bot.send_message(message.chat.id, weather_info, parse_mode="Markdown") #Добавили Markdown для жирного шрифта

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        bot.reply_to(message, "Произошла ошибка при получении погоды. Попробуйте позже.")
    except (KeyError, IndexError) as e:
        print(f"Ошибка при обработке данных API: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке данных о погоде. Пожалуйста, попробуйте другой город.")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        bot.reply_to(message, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    get_weather(message, message.text)

if __name__ == '__main__':
    bot.infinity_polling()