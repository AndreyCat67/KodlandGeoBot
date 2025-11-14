# bot.py
import telebot
from config import *
from logic import *

bot = telebot.TeleBot(TOKEN)
manager = DB_Map(DATABASE)

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет! Я бот, который может показывать города на карте. Напиши /help для списка команд.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, """
Доступные команды:
/show_city [город] — показать город на карте (использует ваш цвет маркеров)
/remember_city [город] — запомнить город
/show_my_cities — показать все запомненные города
/set_marker_color [color] — установить цвет маркера (название или hex, напр. red или #00ff00)
/set_fill_colors [land_color] [ocean_color] — задать цвета заливки континентов и океана (hex)
/toggle_fill [on/off] — включить/выключить заливку land/ocean
/draw_demo — рисует демо-карту с разными объектами (точки, линии, полигон)
""")

@bot.message_handler(commands=['set_marker_color'])
def handle_set_marker_color(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 'Укажите цвет: /set_marker_color red  или /set_marker_color #ff0000')
        return
    color = parts[1].strip()
    manager.set_marker_color(user_id, color)
    bot.send_message(message.chat.id, f'Цвет маркера установлен: {color}')

@bot.message_handler(commands=['set_fill_colors'])
def handle_set_fill_colors(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 3:
        bot.send_message(message.chat.id, 'Укажите два цвета: /set_fill_colors #landcolor #oceancolor')
        return
    land_color = parts[1].strip()
    ocean_color = parts[2].strip()
    manager.set_fill_colors(user_id, land_color=land_color, ocean_color=ocean_color)
    bot.send_message(message.chat.id, f'Цвета заливки установлены: земля={land_color}, океан={ocean_color}')

@bot.message_handler(commands=['toggle_fill'])
def handle_toggle_fill(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 'Укажите on или off: /toggle_fill on')
        return
    val = parts[1].lower()
    if val in ('on', '1', 'true'):
        manager.set_fill_colors(user_id, fill_land=True)
        bot.send_message(message.chat.id, 'Заливка включена.')
    else:
        manager.set_fill_colors(user_id, fill_land=False)
        bot.send_message(message.chat.id, 'Заливка отключена.')

@bot.message_handler(commands=['show_city'])
def handle_show_city(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 'Укажите город: /show_city Moscow')
        return
    city_name = parts[1].strip()
    # get user prefs
    marker_color = manager.get_marker_color(user_id)
    fill_prefs = manager.get_fill_prefs(user_id)
    path = f'{user_id}_city.png'
    manager.create_map(path, cities=[city_name], marker_color=marker_color,
                       fill_map=fill_prefs['fill_land'],
                       land_color=fill_prefs['land_color'], ocean_color=fill_prefs['ocean_color'])
    with open(path, 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

@bot.message_handler(commands=['remember_city'])
def handle_remember_city(message):
    user_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 'Укажите город: /remember_city Moscow')
        return
    city_name = parts[1].strip()
    if manager.add_city(user_id, city_name):
        bot.send_message(message.chat.id, f'Город {city_name} успешно сохранен!')
    else:
        bot.send_message(message.chat.id, 'Такого города я не знаю. Убедись, что он написан на английском и есть в БД!')

@bot.message_handler(commands=['show_my_cities'])
def handle_show_visited_cities(message):
    user_id = message.chat.id
    cities = manager.select_cities(user_id)
    if cities:
        marker_color = manager.get_marker_color(user_id)
        fill_prefs = manager.get_fill_prefs(user_id)
        path = f'{user_id}_cities.png'
        manager.create_map(path, cities=cities, marker_color=marker_color,
                           fill_map=fill_prefs['fill_land'],
                           land_color=fill_prefs['land_color'], ocean_color=fill_prefs['ocean_color'])
        with open(path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo)
    else:
        bot.send_message(message.chat.id, 'У вас пока нет сохраненных городов.')

@bot.message_handler(commands=['draw_demo'])
def handle_draw_demo(message):
    user_id = message.chat.id
    # demo: plot a couple of known cities (if exist), a line and a polygon
    # replace these with cities in your DB
    cities = manager.select_cities(user_id)
    # fallback demo cities
    demo_cities = ['Moscow', 'London', 'New_York']  # имена городов, которые у вас в БД
    use_cities = cities[:3] if cities else demo_cities
    marker_color = manager.get_marker_color(user_id)
    fill_prefs = manager.get_fill_prefs(user_id)

    # extra points: arbitrary coordinates (lat, lon, label)
    extra_points = [
        (55.7558, 37.6176, 'Moscow'),      # Moscow
        (51.5074, -0.1278, 'London'),      # London
        (40.7128, -74.0060, 'New York')    # New York
    ]
    # line: Moscow -> London
    lines = [((55.7558, 37.6176), (51.5074, -0.1278), 'Moscow-London')]

    # polygon: small square somewhere (demo)
    polygons = [[[(10, -20), (10, -10), (20, -10), (20, -20)], 'DemoPoly']]

    path = f'{user_id}_demo.png'
    manager.create_map(path, cities=use_cities, marker_color=marker_color,
                       fill_map=fill_prefs['fill_land'],
                       land_color=fill_prefs['land_color'], ocean_color=fill_prefs['ocean_color'],
                       extra_points=extra_points, lines=lines, polygons=polygons, extent=[-130,40,-30,70])
    with open(path, 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

if __name__=="__main__":
    bot.polling()
