import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from typing import Annotated

class WeatherAPIUtils:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    @staticmethod
    def get_coordinates(address: Annotated[str, "Location name or address"]):
        """Converts a location name to latitude and longitude."""
        geolocator = Nominatim(user_agent="geocoding_app")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None

    @staticmethod
    def fetch_weather_data(
        lat: Annotated[float, "Latitude of location"],
        lon: Annotated[float, "Longitude of location"],
        param: Annotated[str, "Weather parameter to fetch"],
        start_date: Annotated[str, "Start date in YYYY-MM-DD format"],
        end_date: Annotated[str, "End date in YYYY-MM-DD format"],
    ):
        """Fetches daily weather data from Open-Meteo API within the given date range."""
        url = f"{WeatherAPIUtils.ARCHIVE_URL}?latitude={lat}&longitude={lon}&daily={param}&timezone=auto&start_date={start_date}&end_date={end_date}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    @staticmethod
    def save_data(df: Annotated[pd.DataFrame, "DataFrame to be saved"], filename: Annotated[str, "File name for saving data"]):
        """Saves the DataFrame to a CSV file."""
        if not os.path.exists(WeatherAPIUtils.DATA_DIR):
            os.makedirs(WeatherAPIUtils.DATA_DIR)
        file_path = os.path.join(WeatherAPIUtils.DATA_DIR, filename)
        df.to_csv(file_path, index=False)

    @staticmethod
    def get_monthly_rainfall(
        location: Annotated[str, "Name of location or address for rainfall data"],
        year: Annotated[str, "Year in YYYY format for which rainfall data is to be fetched"],
        save_path: Annotated[str, "Folder Path to save the rainfall data CSV file"]
    ):
        """Gets cached monthly rainfall data or fetches if unavailable. One year of data is fetched and stored in a DataFrame for further LLM analysis."""
        coords = WeatherAPIUtils.get_coordinates(location)
        if not coords:
            return None

        lat, lon = coords
        filename = f"rainfall_{location.replace(' ', '_')}_{year}.csv"
        file_path = os.path.join(save_path, filename)

        if os.path.exists(file_path):
            return pd.read_csv(file_path)

        monthly_rainfall = []

        for month in range(1, 13):  # Loop through all 12 months
            start_date = f"{year}-{month:02d}-01"
            end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")

            data = WeatherAPIUtils.fetch_weather_data(lat, lon, "rain_sum", start_date, end_date)
            if not data or "daily" not in data or "rain_sum" not in data["daily"]:
                continue

            rainfall_values = data["daily"]["rain_sum"]
            monthly_avg_rainfall = sum(rainfall_values) / len(rainfall_values) if rainfall_values else 0
            monthly_rainfall.append([f"{year}-{month:02d}", monthly_avg_rainfall])

        df = pd.DataFrame(monthly_rainfall, columns=["Month", "Average Rainfall (mm)"])
        WeatherAPIUtils.save_data(df, filename)
        return df

    @staticmethod
    def get_monthly_temperature(
        location: Annotated[str, "Name of location or address for temperature and solar radiation data"],
        year: Annotated[str, "Year in YYYY format for which temperature and radiation data is to be fetched"],
        save_path: Annotated[str, "Folder Path to save the temperature data CSV file"]
    ):
        """Gets cached monthly temperature and shortwave radiation data or fetches if unavailable. One year of data is fetched and stored in a DataFrame for further LLM analysis."""
        coords = WeatherAPIUtils.get_coordinates(location)
        if not coords:
            return None

        lat, lon = coords
        filename = f"temperature_{location.replace(' ', '_')}_{year}.csv"
        file_path = os.path.join(save_path, filename)

        if os.path.exists(file_path):
            return pd.read_csv(file_path)

        monthly_data = []

        for month in range(1, 13):  # Loop through all 12 months
            start_date = f"{year}-{month:02d}-01"
            end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            end_date = end_date.strftime("%Y-%m-%d")

            data = WeatherAPIUtils.fetch_weather_data(lat, lon, "temperature_2m_mean,shortwave_radiation_sum", start_date, end_date)
            if not data or "daily" not in data:
                continue

            temp_values = data["daily"].get("temperature_2m_mean", [])
            radiation_values = data["daily"].get("shortwave_radiation_sum", [])

            avg_temp = sum(temp_values) / len(temp_values) if temp_values else 0
            avg_radiation = sum(radiation_values) / len(radiation_values) if radiation_values else 0

            monthly_data.append([f"{year}-{month:02d}", avg_temp, avg_radiation])

        df = pd.DataFrame(monthly_data, columns=["Month", "Average Temperature (°C)", "Average Shortwave Radiation (W/m²)"])
        WeatherAPIUtils.save_data(df, filename)
        return df
