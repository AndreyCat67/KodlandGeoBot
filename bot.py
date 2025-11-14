# Updated bot.py
# Includes new commands: country filter, density filter, weather, time, improved map functionality

import telebot
from config import *
from logic import DB_Map

bot = telebot.TeleBot(TOKEN)
manager = DB_Map(DATABASE)

# --- BASIC COMMANDS ------------------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я бот для работы с картами. Используй /help для списка команд.")


@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, """
Доступные команды:

/remember_city <город> — сохранить город
/show_my_cities — показать все сохранённые города
/show_city <город> — показать город на карте

# Фильтры городов
/show_country <страна>
/show_density <min> <max>
/show_country_density <страна> <min> <max>

# Информация о городах
/city_info <город> — погода и время

# Настройки отображения
/set_marker_color <цвет>
/set_fill_colors <цвет_земли> <цвет_океана>
/toggle_fill <on/off>

/demo — демо-карта
""")


# --- PREFERENCE COMMANDS --------------------------------------------------

@bot.message_handler(commands=['set_marker_color'])
def set_marker_color_cmd(message):
    uid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /set_marker_color red или #ff0000")
        return
    manager.set_marker_color(uid, parts[1])
    bot.send_message(uid, f"Цвет маркера установлен: {parts[1]}")


@bot.message_handler(commands=['set_fill_colors'])
def set_fill_colors_cmd(message):
    uid = message.chat.id
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(uid, "Использование: /set_fill_colors #land #ocean")
        return
    manager.set_fill_colors(uid, land_color=parts[1], ocean_color=parts[2])
    bot.send_message(uid, "Цвета заливки обновлены!")


@bot.message_handler(commands=['toggle_fill'])
def toggle_fill_cmd(message):
    uid = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /toggle_fill on/off")
        return
    state = parts[1].lower()
    manager.set_fill_colors(uid, fill_land=(state=='on'))
    bot.send_message(uid, f"Заливка: {'включена' if state=='on' else 'выключена'}")


# --- SAVE / SHOW USER CITIES ----------------------------------------------

@bot.message_handler(commands=['remember_city'])
def remember_city_cmd(message):
    uid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /remember_city Moscow")
        return

    if manager.add_city(uid, parts[1]):
        bot.send_message(uid, "Город сохранён!")
    else:
        bot.send_message(uid, "Такого города нет в базе.")


@bot.message_handler(commands=['show_my_cities'])
def show_my_cities_cmd(message):
    uid = message.chat.id
    cities = manager.select_cities(uid)
    if not cities:
        bot.send_message(uid, "Нет сохранённых городов.")
        return

    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_saved.png"
    manager.create_map(path, cities=cities,
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'])

    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


@bot.message_handler(commands=['show_city'])
def show_city_cmd(message):
    uid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /show_city London")
        return

    city = parts[1]
    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_onecity.png"
    manager.create_map(path, cities=[city],
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'])
    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


# --- FILTERS ---------------------------------------------------------------

@bot.message_handler(commands=['show_country'])
def show_country_cmd(message):
    uid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /show_country Russia")
        return

    country = parts[1]
    cities = manager.get_cities_by_country(country)
    if not cities:
        bot.send_message(uid, "Нет городов по данной стране.")
        return

    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_country.png"
    manager.create_map(path, cities=cities,
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'])

    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


@bot.message_handler(commands=['show_density'])
def show_density_cmd(message):
    uid = message.chat.id
    parts = message.text.split()
    if len(parts) not in (2,3):
        bot.send_message(uid, "Использование: /show_density min [max]")
        return

    min_d = int(parts[1])
    max_d = int(parts[2]) if len(parts) == 3 else None

    cities = manager.get_cities_by_density(min_d, max_d)
    if not cities:
        bot.send_message(uid, "Города не найдены.")
        return

    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_density.png"
    manager.create_map(path, cities=cities,
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'])

    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


@bot.message_handler(commands=['show_country_density'])
def show_country_density_cmd(message):
    uid = message.chat.id
    parts = message.text.split()
    if len(parts) not in (3,4):
        bot.send_message(uid, "Использование: /show_country_density Russia min max")
        return

    country = parts[1]
    min_d = int(parts[2])
    max_d = int(parts[3]) if len(parts) == 4 else None

    cities = manager.get_cities_by_country_and_density(country, min_d, max_d)
    if not cities:
        bot.send_message(uid, "Нет городов по данным условиям.")
        return

    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_countrydensity.png"
    manager.create_map(path, cities=cities,
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'])

    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


# --- CITY INFO (WEATHER + TIME) -------------------------------------------

@bot.message_handler(commands=['city_info'])
def city_info_cmd(message):
    uid = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Использование: /city_info London")
        return

    city = parts[1]
    coords = manager.get_coordinates(city)
    if not coords:
        bot.send_message(uid, "Город не найден.")
        return

    lat,lon = coords
    weather = manager.get_weather(lat,lon)
    local_time = manager.get_local_time(lat,lon)

    if not weather:
        bot.send_message(uid, "Ошибка получения погоды.")
        return

    text = f"""
<b>{city}</b>
Температура: {weather['temp']}°C
Ощущается как: {weather['feels']}°C
Влажность: {weather['humidity']}%
Погода: {weather['desc']}

Местное время: {local_time}
"""

    bot.send_message(uid, text, parse_mode="HTML")


# --- DEMO MAP -------------------------------------------------------------

@bot.message_handler(commands=['demo'])
def demo_cmd(message):
    uid = message.chat.id

    extra_points = [
        (55.7558, 37.6176, "Moscow"),
        (51.5074,-0.1278, "London")
    ]

    lines = [
        ((55.7558,37.6176),(51.5074,-0.1278),"Route")
    ]

    polygons = [
        [[(10,-20),(10,-10),(20,-10),(20,-20)],"Area"]
    ]

    prefs = manager.get_fill_prefs(uid)
    path = f"{uid}_demo.png"
    manager.create_map(path,
                       cities=None,
                       marker_color=manager.get_marker_color(uid),
                       fill_map=prefs['fill_land'],
                       land_color=prefs['land_color'], ocean_color=prefs['ocean_color'],
                       extra_points=extra_points,
                       lines=lines,
                       polygons=polygons,
                       extent=[-30,60,0,70])

    with open(path,'rb') as ph:
        bot.send_photo(uid, ph)


# --------------------------------------------------------------------------

if __name__ == "__main__":
    bot.polling(none_stop=True)
