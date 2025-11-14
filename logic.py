# Updated logic.py
# (Full updated version including filtering, weather, time, map rendering, user prefs)

import sqlite3
import requests
from datetime import datetime, timedelta
from config import *

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

class DB_Map:
    def __init__(self, database):
        self.database = database
        self.create_cities_table()
        self.create_user_table()
        self.create_user_prefs_table()

    # --- TABLES ------------------------------------------------------------

    def create_cities_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS cities (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                city TEXT,
                                lat REAL,
                                lng REAL,
                                country TEXT,
                                population INTEGER,
                                density INTEGER
                            )''')
            conn.commit()

    def create_user_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users_cities (
                                user_id INTEGER,
                                city_id TEXT
                            )''')
            conn.commit()

    def create_user_prefs_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS user_prefs (
                                user_id INTEGER PRIMARY KEY,
                                marker_color TEXT DEFAULT 'red',
                                land_color TEXT DEFAULT '#f0ead6',
                                ocean_color TEXT DEFAULT '#b3d9ff',
                                fill_land INTEGER DEFAULT 1
                            )''')
            conn.commit()

    # --- USER PREFS --------------------------------------------------------

    def set_marker_color(self, user_id, color):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)', (user_id,))
            conn.execute('UPDATE user_prefs SET marker_color=? WHERE user_id=?', (color, user_id))
            conn.commit()

    def get_marker_color(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT marker_color FROM user_prefs WHERE user_id=?', (user_id,))
            r = cur.fetchone()
            return r[0] if r else 'red'

    def set_fill_colors(self, user_id, land_color=None, ocean_color=None, fill_land=None):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)', (user_id,))
            if land_color:
                conn.execute('UPDATE user_prefs SET land_color=? WHERE user_id=?', (land_color, user_id))
            if ocean_color:
                conn.execute('UPDATE user_prefs SET ocean_color=? WHERE user_id=?', (ocean_color, user_id))
            if fill_land is not None:
                conn.execute('UPDATE user_prefs SET fill_land=? WHERE user_id=?', (1 if fill_land else 0, user_id))
            conn.commit()

    def get_fill_prefs(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT land_color, ocean_color, fill_land FROM user_prefs WHERE user_id=?', (user_id,))
            r = cur.fetchone()
            if r:
                return {
                    'land_color': r[0],
                    'ocean_color': r[1],
                    'fill_land': bool(r[2])
                }
            return {'land_color': '#f0ead6','ocean_color': '#b3d9ff','fill_land': True}

    # --- CITY DB OPERATIONS ------------------------------------------------

    def add_city(self, user_id, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM cities WHERE city=?", (city_name,))
            r = cur.fetchone()
            if not r:
                return 0
            city_id = r[0]
            conn.execute('INSERT INTO users_cities VALUES (?,?)', (user_id, city_id))
            conn.commit()
            return 1

    def select_cities(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''SELECT city FROM cities
                           JOIN users_cities ON users_cities.city_id = cities.id
                           WHERE users_cities.user_id=?''', (user_id,))
            return [c[0] for c in cur.fetchall()]

    def get_coordinates(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT lat,lng FROM cities WHERE city=?", (city_name,))
            return cur.fetchone()

    # --- CITY FILTERS ------------------------------------------------------

    def get_cities_by_country(self, country):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT city FROM cities WHERE country=?", (country,))
            return [c[0] for c in cur.fetchall()]

    def get_cities_by_density(self, min_d=None, max_d=None):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            q = "SELECT city FROM cities WHERE 1=1"
            p = []
            if min_d is not None:
                q += " AND density >= ?"
                p.append(min_d)
            if max_d is not None:
                q += " AND density <= ?"
                p.append(max_d)
            cur.execute(q, tuple(p))
            return [c[0] for c in cur.fetchall()]

    def get_cities_by_country_and_density(self, country, min_d=None, max_d=None):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            q = "SELECT city FROM cities WHERE country=?"
            p = [country]
            if min_d is not None:
                q += " AND density >= ?"
                p.append(min_d)
            if max_d is not None:
                q += " AND density <= ?"
                p.append(max_d)
            cur.execute(q, tuple(p))
            return [c[0] for c in cur.fetchall()]

    # --- WEATHER & TIME ----------------------------------------------------

    def get_weather(self, lat, lon):
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_KEY}&units=metric"
        r = requests.get(url).json()
        if "main" not in r:
            return None
        return {
            "temp": r["main"]["temp"],
            "feels": r["main"]["feels_like"],
            "humidity": r["main"]["humidity"],
            "desc": r["weather"][0]["description"]
        }

    def get_local_time(self, lat, lon):
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_KEY}"
        r = requests.get(url).json()
        if "timezone" not in r:
            return None
        offset = r["timezone"]
        local_time = datetime.utcnow() + timedelta(seconds=offset)
        return local_time.strftime("%Y-%m-%d %H:%M")

    # --- MAP CREATION ------------------------------------------------------

    def create_map(self, path, cities=None, marker_color="red", fill_map=True,
                   land_color="#f0ead6", ocean_color="#b3d9ff",
                   extra_points=None, lines=None, polygons=None, extent=None):

        fig = plt.figure(figsize=(10,6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE)

        if fill_map:
            ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor=land_color)
            ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor=ocean_color)
        else:
            ax.stock_img()

        if extent:
            ax.set_extent(extent, crs=ccrs.PlateCarree())

        # plot cities
        if cities:
            for c in cities:
                coords = self.get_coordinates(c)
                if coords:
                    lat,lng = coords
                    ax.plot(lng, lat, marker='o', color=marker_color, transform=ccrs.Geodetic())
                    ax.text(lng+0.3, lat+0.3, c, transform=ccrs.Geodetic(), fontsize=8)

        # extra points
        if extra_points:
            for lat,lon,label in extra_points:
                ax.plot(lon,lat, marker='o', color=marker_color)
                ax.text(lon+0.3,lat+0.3,label,fontsize=8)

        # lines
        if lines:
            for (lat1,lon1),(lat2,lon2),label in lines:
                ax.plot([lon1,lon2],[lat1,lat2],color=marker_color,linewidth=2)
                ax.text((lon1+lon2)/2,(lat1+lat2)/2,label,fontsize=8)

        # polygons
        if polygons:
            import matplotlib.patches as mpatches
            for poly,label in polygons:
                lats=[p[0] for p in poly]
                lons=[p[1] for p in poly]
                patch = mpatches.Polygon(list(zip(lons,lats)),closed=True,
                                         facecolor=marker_color,alpha=0.3,
                                         transform=ccrs.PlateCarree())
                ax.add_patch(patch)
                ax.text(sum(lons)/len(lons), sum(lats)/len(lats), label)

        plt.savefig(path,bbox_inches='tight',dpi=150)
        plt.close(fig)
        return path


if __name__ == "__main__":
    db = DB_Map(DATABASE)
