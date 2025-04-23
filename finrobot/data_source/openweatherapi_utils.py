import requests
import pandas as pd
import math
import requests
from PIL import Image
from io import BytesIO
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
WEATHER_CODE_MAP = {
    # Thunderstorm Group 2xx
    200: 'Thunderstorm with light rain',
    201: 'Thunderstorm with rain',
    202: 'Thunderstorm with heavy rain',
    210: 'Light thunderstorm',
    211: 'Moderate thunderstorm',
    212: 'Heavy thunderstorm',
    221: 'Ragged thunderstorm',
    230: 'Thunderstorm with light drizzle',
    231: 'Thunderstorm with drizzle',
    232: 'Thunderstorm with heavy drizzle',

    # Drizzle Group 3xx
    300: 'Light intensity drizzle',
    301: 'Drizzle',
    302: 'Heavy intensity drizzle',
    310: 'Light intensity drizzle rain',
    311: 'Drizzle rain',
    312: 'Heavy intensity drizzle rain',
    313: 'Shower rain and drizzle',
    314: 'Heavy shower rain and drizzle',
    321: 'Shower drizzle',

    # Rain Group 5xx
    500: 'Light rain',
    501: 'Moderate rain',
    502: 'Heavy intensity rain',
    503: 'Very heavy rain',
    504: 'Extreme rain',
    511: 'Freezing rain',
    520: 'Light intensity shower rain',
    521: 'Shower rain',
    522: 'Heavy intensity shower rain',
    531: 'Ragged shower rain',

    # Snow Group 6xx
    600: 'Light snow',
    601: 'Snow',
    602: 'Heavy snow',
    611: 'Sleet',
    612: 'Light shower sleet',
    613: 'Shower sleet',
    615: 'Light rain and snow',
    616: 'Rain and snow',
    620: 'Light shower snow',
    621: 'Shower snow',
    622: 'Heavy shower snow',

    # Atmosphere Group 7xx
    701: 'Mist',
    711: 'Smoke',
    721: 'Haze',
    731: 'Sand/dust whirls',
    741: 'Fog',
    751: 'Sand',
    761: 'Dust',
    762: 'Volcanic ash',
    771: 'Squalls',
    781: 'Tornado',

    # Clear
    800: 'Clear sky',

    # Clouds Group 80x
    801: 'Few clouds (11–25%)',
    802: 'Scattered clouds (25–50%)',
    803: 'Broken clouds (51–84%)',
    804: 'Overcast clouds (85–100%)'
}

class OpenWeatherAPI:
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"
    AIR_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
    API_KEY = "3debd8fec55dfc7d852be72d1381fd8f"  # Replace with your OpenWeather API key

    @staticmethod
    def get_coordinates(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """Converts a city name to latitude and longitude using OpenWeather's Geocoding API."""
        params = {
            'q': f"{city_name},{state_code},{country_code}" if state_code and country_code else city_name,
            'limit': 1,
            'appid': OpenWeatherAPI.API_KEY
        }
        response = requests.get(OpenWeatherAPI.GEOCODE_URL, params=params)
        if response.status_code == 200 and response.json():
            location = response.json()[0]
            return location['lat'], location['lon']
        return None

    @staticmethod
    def fetch_weather_data(endpoint: str, params: dict) -> Optional[dict]:
        """Fetches weather data from OpenWeather API for a given endpoint and parameters."""
        params['appid'] = OpenWeatherAPI.API_KEY
        response = requests.get(f"{OpenWeatherAPI.BASE_URL}/{endpoint}", params=params)
        if response.status_code == 200:
            return response.json()
        return None

    @staticmethod
    def get_current_weather(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[dict]:
        """Gets current weather data for a specified location."""
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'units': 'metric'}

        return OpenWeatherAPI.fetch_weather_data('weather', params)

    @staticmethod
    def get_hourly_forecast(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Gets hourly weather forecast for the next 48 hours for a specified location."""
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'units': 'metric'}
        data = OpenWeatherAPI.fetch_weather_data('forecast', params)
        if not data or 'list' not in data:
            return None
        forecast_data = data['list']
        df = pd.DataFrame(forecast_data)
        df['dt'] = pd.to_datetime(df['dt'], unit='s')
        # Extract temperature from the 'main' column which is a dict in each row
        df['temp'] = df['main'].apply(lambda x: x['temp'] if isinstance(x, dict) else None)
        df['weather_description'] = df['weather'].apply(
        lambda x: WEATHER_CODE_MAP.get(x[0]['id']) if isinstance(x, list) and 'id' in x[0] else None
    )
        return df[['dt', 'temp', 'weather', 'weather_description']]


    @staticmethod
    def get_daily_forecast(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None, cnt: int = 7) -> Optional[pd.DataFrame]:
        """Gets daily weather forecast for a specified number of days for a given location."""
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'cnt': cnt, 'units': 'metric'}
        data = OpenWeatherAPI.fetch_weather_data('forecast/daily', params)
        if not data or 'list' not in data:
            return None
        forecast_data = data['list']
        df = pd.DataFrame(forecast_data)
        df['dt'] = pd.to_datetime(df['dt'], unit='s')
        # Extract temperature details from nested 'temp' dictionary
        df['day_temp'] = df['temp'].apply(lambda x: x.get('day') if isinstance(x, dict) else None)
        df['min_temp'] = df['temp'].apply(lambda x: x.get('min') if isinstance(x, dict) else None)
        df['max_temp'] = df['temp'].apply(lambda x: x.get('max') if isinstance(x, dict) else None)
        df['weather_description'] = df['weather'].apply(
        lambda x: WEATHER_CODE_MAP.get(x[0]['id']) if isinstance(x, list) and 'id' in x[0] else None
    )

        return df[['dt', 'day_temp', 'min_temp', 'max_temp', 'weather','weather_description']]


    @staticmethod
    def get_historical_weather(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        params = {
            'lat': lat,
            'lon': lon,
            'type': 'hour',
            'start': start_timestamp,
            'end': end_timestamp,
            'appid': OpenWeatherAPI.API_KEY,
            'units': 'metric'
        }
        response = requests.get("http://history.openweathermap.org/data/2.5/history/city", params=params)
        if response.status_code != 200:
            return None
        data = response.json()
        if 'list' not in data:
            return None
        df = pd.DataFrame(data['list'])
        df['dt'] = pd.to_datetime(df['dt'], unit='s')
        df['temp'] = df['main'].apply(lambda x: x.get('temp') if isinstance(x, dict) else None)
        df['weather_description'] = df['weather'].apply(
            lambda x: WEATHER_CODE_MAP.get(x[0]['id']) if isinstance(x, list) and 'id' in x[0] else None
        )
        return df[['dt', 'temp', 'weather', 'weather_description']]

    @staticmethod
    def get_air_pollution(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Gets current air pollution data for a specified location."""
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OpenWeatherAPI.API_KEY
        }
        response = requests.get("http://api.openweathermap.org/data/2.5/air_pollution", params=params)
        if response.status_code != 200:
            return None
        data = response.json()
        if 'list' not in data:
            return None
        pollution_info = data['list'][0]
        df = pd.json_normalize(pollution_info)
        return df


    def get_tile_coordinates(self, lat, lng, zoom):
        """
        Calculates the tile x and y coordinates for a given latitude, longitude, and zoom level.

        Args:
            lat: The latitude of the location.
            lng: The longitude of the location.
            zoom: The zoom level.

        Returns:
            A dictionary containing the zoom level, tile x, tile y, pixel x, and pixel y coordinates.
        """
        TILE_SIZE = 256
        

        # Project the latitude and longitude to world coordinates
        siny = math.sin(lat * math.pi / 180)
        siny = min(max(siny, -0.9999), 0.9999)  # Clamp to avoid issues at extreme latitudes

        world_coordinate_x = TILE_SIZE * (0.5 + lng / 360)
        world_coordinate_y = TILE_SIZE * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi))

        # Calculate the scale based on the zoom level
        scale = 1 << zoom  # Equivalent to 2**zoom

        # Calculate the pixel coordinates
        pixel_coordinate_x = math.floor(world_coordinate_x * scale)
        pixel_coordinate_y = math.floor(world_coordinate_y * scale)

        # Calculate the tile coordinates
        tile_coordinate_x = math.floor(pixel_coordinate_x / TILE_SIZE)
        tile_coordinate_y = math.floor(pixel_coordinate_y / TILE_SIZE)

        return tile_coordinate_x,tile_coordinate_y

    @staticmethod
    def get_weather_map_url(
        self,
        layer: str,
        z: int = 0,
        x: float = 21,
        y: float = 79,
        date: int = None,
        opacity: float = 0.8,
        palette: str = None,
        fill_bound: bool = False,
        arrow_step: int = None,
        use_norm: bool = False
    ) -> str:
        """
        Get weather map tile URL from OpenWeather Maps 2.0 API.

        Parameters:
            layer (str): Weather map layer (e.g., 'TA2', 'PA0', 'WND', etc.).
            z (int): Zoom level.
            x (Float): Latitude.
            y (Float): Longitude.
            date (int, optional): Unix timestamp (UTC) for current, forecast, or historical.
            opacity (float, optional): Opacity of the layer (0 to 1).
            palette (str, optional): Custom palette string in format value:HEX;value:HEX.
            fill_bound (bool, optional): Whether to fill values outside specified set.
            arrow_step (int, optional): Step in pixels for wind arrows (only for 'WND' layer).
            use_norm (bool, optional): Whether to normalize wind arrows (only for 'WND' layer).

        Returns:
            str: Fully formatted map tile URL.
        """
        x,y = self.get_tile_coordinates(lat=x,lng=y,zoom=z)
        base_url = f"http://maps.openweathermap.org/maps/2.0/weather/{layer}/{z}/{x}/{y}"
        params = {
            "appid": self.API_KEY,
            "opacity": opacity,
            "fill_bound": str(fill_bound).lower()
        }

        if date is not None:
            params["date"] = date
        if palette is not None:
            params["palette"] = palette
        if layer == "WND":
            if arrow_step is not None:
                params["arrow_step"] = arrow_step
            params["use_norm"] = str(use_norm).lower()

        query = "&".join(f"{key}={value}" for key, value in params.items())
        import IPython.display as display
        url = f"{base_url}?{query}"
        # Assuming 'url' variable from the previous code cell is still in scope
        display.Image(url=url)
        response = requests.get(url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            image.save("weather_map.png", "PNG")
        return f"{base_url}?{query}"

instance = OpenWeatherAPI()
weather = OpenWeatherAPI.get_current_weather("Nagpur", "MH", "IN")
print(weather)
forecast = OpenWeatherAPI.get_hourly_forecast("Nagpur", "MH", "IN")
print(forecast)
daily_forecast = OpenWeatherAPI.get_daily_forecast("Nagpur", "MH", "IN", cnt=7)
print(daily_forecast)
historical_weather = OpenWeatherAPI.get_historical_weather("Nagpur", "MH", "IN", start_date="2025-03-01", end_date="2025-03-31")
print(historical_weather)

url = OpenWeatherAPI.get_weather_map_url(
    instance,
    layer="TA2",                  # Air temperature at 2 meters layer
    z=4,
    x=21,                    # Approximate tile x for Pune
    y=78,                    # Approximate tile y for Pune
    date=int(time.time()),        # Current timestamp (will round to previous 3-hr interval)
    opacity=0.6,
    fill_bound=True,
    palette="-65:821692;-55:821692;-45:821692;0:23dddd;10:c2ff28;20:fff028;30:fc8014"
)

print(url)

import IPython.display as display

# Assuming 'url' variable from the previous code cell is still in scope
display.Image(url=url)