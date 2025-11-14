# logic.py
import sqlite3
from config import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

class DB_Map():
    def __init__(self, database):
        self.database = database
        # ensure tables exist
        self.create_user_table()
        self.create_user_prefs_table()

    # --- DB schema helpers ---
    def create_user_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users_cities (
                                user_id INTEGER,
                                city_id TEXT,
                                FOREIGN KEY(city_id) REFERENCES cities(id)
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

    # --- user prefs ---
    def set_marker_color(self, user_id, color):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR REPLACE INTO user_prefs(user_id, marker_color) VALUES (?, COALESCE((SELECT marker_color FROM user_prefs WHERE user_id=?),?))',
                         (user_id, user_id, color))
            # simpler replace:
            conn.execute('UPDATE user_prefs SET marker_color = ? WHERE user_id = ?', (color, user_id))
            conn.commit()
            return True

    def get_marker_color(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT marker_color FROM user_prefs WHERE user_id = ?', (user_id,))
            r = cursor.fetchone()
            return r[0] if r else 'red'

    def set_fill_colors(self, user_id, land_color=None, ocean_color=None, fill_land=None):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM user_prefs WHERE user_id=?', (user_id,))
            if cursor.fetchone() is None:
                conn.execute('INSERT INTO user_prefs(user_id, marker_color, land_color, ocean_color, fill_land) VALUES (?, ?, ?, ?, ?)',
                             (user_id, 'red', land_color or '#f0ead6', ocean_color or '#b3d9ff', 1 if fill_land else 0))
            else:
                if land_color:
                    conn.execute('UPDATE user_prefs SET land_color=? WHERE user_id=?', (land_color, user_id))
                if ocean_color:
                    conn.execute('UPDATE user_prefs SET ocean_color=? WHERE user_id=?', (ocean_color, user_id))
                if fill_land is not None:
                    conn.execute('UPDATE user_prefs SET fill_land=? WHERE user_id=?', (1 if fill_land else 0, user_id))
            conn.commit()
            return True

    def get_fill_prefs(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT land_color, ocean_color, fill_land FROM user_prefs WHERE user_id=?', (user_id,))
            r = cursor.fetchone()
            if r:
                return {'land_color': r[0], 'ocean_color': r[1], 'fill_land': bool(r[2])}
            else:
                return {'land_color': '#f0ead6', 'ocean_color': '#b3d9ff', 'fill_land': True}

    # --- city management ---
    def add_city(self,user_id, city_name ):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cities WHERE city=?", (city_name,))
            city_data = cursor.fetchone()
            if city_data:
                city_id = city_data[0]  
                conn.execute('INSERT INTO users_cities VALUES (?, ?)', (user_id, city_id))
                conn.commit()
                return 1
            else:
                return 0

    def select_cities(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT cities.city 
                            FROM users_cities  
                            JOIN cities ON users_cities.city_id = cities.id
                            WHERE users_cities.user_id = ?''', (user_id,))
            cities = [row[0] for row in cursor.fetchall()]
            return cities

    def get_coordinates(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT lat, lng
                            FROM cities  
                            WHERE city = ?''', (city_name,))
            coordinates = cursor.fetchone()
            return coordinates

    # --- map drawing helpers ---
    def create_map(self, path, cities=None, marker_color=None, fill_map=True, land_color=None, ocean_color=None,
                   extra_points=None, lines=None, polygons=None, extent=None):
        """
        Создаёт карту и сохраняет в path.
        - cities: list of city names (вытягивает координаты из БД)
        - marker_color: цвет маркера (цвет строки/маркера matplotlib)
        - fill_map: bool, заливать ли land/ocean
        - land_color, ocean_color: hex или цвет matplotlib
        - extra_points: list of (lat, lon, label_opt)
        - lines: list of ((lat1,lon1),(lat2,lon2), label_opt)
        - polygons: list of ([ (lat,lon), ... ], label_opt)
        - extent: [lon_min, lon_max, lat_min, lat_max] (опционально, для приближения)
        """
        fig = plt.figure(figsize=(10, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())

        # background / coastlines
        ax.add_feature(cfeature.COASTLINE)

        # fill land/ocean
        if fill_map:
            land_c = land_color or '#f0ead6'
            ocean_c = ocean_color or '#b3d9ff'
            ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor=land_c)
            ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor=ocean_c)
        else:
            # if not filling, still add natural features outlines
            ax.stock_img()

        # extent (if given)
        if extent:
            ax.set_extent(extent, crs=ccrs.PlateCarree())

        # default marker color from prefs if not provided
        if marker_color is None:
            marker_color = 'red'

        # plot cities (by name)
        if cities:
            for city in cities:
                coords = self.get_coordinates(city)
                if coords:
                    lat, lng = coords
                    ax.plot(lng, lat,
                            marker='o', markersize=6,
                            color=marker_color,
                            transform=ccrs.Geodetic())

        # extra points (list of tuples)
        if extra_points:
            for item in extra_points:
                lat, lon = item[0], item[1]
                label = item[2] if len(item) > 2 else None
                ax.plot(lon, lat, marker='o', markersize=6, color=marker_color, transform=ccrs.Geodetic())
                if label:
                    ax.text(lon + 0.5, lat + 0.5, label, transform=ccrs.Geodetic())

        # lines (list of ((lat1,lon1),(lat2,lon2), label_opt))
        if lines:
            for l in lines:
                (lat1, lon1), (lat2, lon2) = (l[0], l[1])
                label = l[2] if len(l) > 2 else None
                ax.plot([lon1, lon2], [lat1, lat2],
                        color=marker_color, linewidth=2, transform=ccrs.Geodetic())
                if label:
                    mid_lon = (lon1 + lon2) / 2
                    mid_lat = (lat1 + lat2) / 2
                    ax.text(mid_lon, mid_lat, label, transform=ccrs.Geodetic())

        # polygons (list of ([ (lat,lon), ... ], label_opt))
        if polygons:
            import matplotlib.patches as mpatches
            for p in polygons:
                coords = p[0]
                label = p[1] if len(p) > 1 else None
                lons = [c[1] for c in coords]
                lats = [c[0] for c in coords]
                poly_coords = list(zip(lons, lats))
                patch = mpatches.Polygon(poly_coords, closed=True, transform=ccrs.PlateCarree(),
                                         alpha=0.4, facecolor=marker_color, edgecolor='k')
                ax.add_patch(patch)
                if label:
                    cx = sum(lons) / len(lons)
                    cy = sum(lats) / len(lats)
                    ax.text(cx, cy, label, transform=ccrs.Geodetic())

        # gridlines for context
        gl = ax.gridlines(draw_labels=True, linewidth=0.2, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False

        plt.savefig(path, bbox_inches='tight', dpi=150)
        plt.close(fig)
        return path

    # backward compat wrapper for older code that called create_grapf/create_graf
    def create_grapf(self, path, cities):
        # default behavior: use user red, no fills (keeps previous visual similar)
        return self.create_map(path, cities=cities, marker_color='red', fill_map=True)

    def create_graf(self, path, cities):
        return self.create_map(path, cities=cities, marker_color='red', fill_map=True)

    # extra utility demo method: draw distance between two cities
    def draw_distance(self, city1, city2, path='distance_map.png', marker_color='blue'):
        city1_coords = self.get_coordinates(city1)
        city2_coords = self.get_coordinates(city2)
        if not city1_coords or not city2_coords:
            return None
        lat1, lon1 = city1_coords
        lat2, lon2 = city2_coords
        # reuse create_map with lines
        lines = [((lat1, lon1), (lat2, lon2), f'{city1} ↔ {city2}')]
        extra_points = [(lat1, lon1, city1), (lat2, lon2, city2)]
        self.create_map(path, cities=None, marker_color=marker_color,
                        extra_points=extra_points, lines=lines)
        return path

if __name__=="__main__":
    m = DB_Map(DATABASE)
    m.create_user_table()
    m.create_user_prefs_table()
