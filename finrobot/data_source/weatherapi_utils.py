import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from typing import Annotated
import json

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
        year: Annotated[str, "Year in YYYY format"],
    ):
        """Fetches daily weather data from Open-Meteo API within the given one Year."""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        url = f"{WeatherAPIUtils.ARCHIVE_URL}?latitude={lat}&longitude={lon}&daily={param}&timezone=auto&start_date={start_date}&end_date={end_date}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    @staticmethod
    def save_data(df: Annotated[pd.DataFrame, "DataFrame to be saved"],  save_path: Annotated[str, "Folder Path to save data in current working directory"],filename: Annotated[str, "File name for saving data"]):
        """Saves the DataFrame to a CSV file."""
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        file_path = os.path.join(save_path, filename)
        df.to_csv(file_path, index=False)

    # @staticmethod
    # def get_monthly_rainfall(
    #     location: Annotated[str, "Name of location or address for rainfall data"],
    #     year: Annotated[str, "Year in YYYY format for which rainfall data is to be fetched"],
    #     save_path: Annotated[str, "Folder Path to save the rainfall data CSV file"]
    # ):
    #     """Gets cached monthly rainfall data or fetches if unavailable. One year of data is fetched and stored in a DataFrame for further LLM analysis."""
    #     coords = WeatherAPIUtils.get_coordinates(location)
    #     if not coords:
    #         return None

    #     lat, lon = coords
    #     filename = f"rainfall_{location.replace(' ', '_')}_{year}.csv"
    #     file_path = os.path.join(save_path, filename)

    #     if os.path.exists(file_path):
    #         return pd.read_csv(file_path)

    #     monthly_rainfall = []

    #     for month in range(1, 13):  # Loop through all 12 months
    #         start_date = f"{year}-{month:02d}-01"
    #         end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    #         end_date = end_date.strftime("%Y-%m-%d")

    #         data = WeatherAPIUtils.fetch_weather_data(lat, lon, "rain_sum", start_date, end_date)
    #         if not data or "daily" not in data or "rain_sum" not in data["daily"]:
    #             continue

    #         rainfall_values = data["daily"]["rain_sum"]
    #         monthly_avg_rainfall = sum(rainfall_values) / len(rainfall_values) if rainfall_values else 0
    #         monthly_rainfall.append([f"{year}-{month:02d}", monthly_avg_rainfall])

    #     df = pd.DataFrame(monthly_rainfall, columns=["Month", "Average Rainfall (mm)"])
    #     WeatherAPIUtils.save_data(df, save_path,filename)
    #     return df

    @staticmethod
    def get_monthly_temperature(
        location: Annotated[str, "Name of location or address for temperature and solar radiation data"],
        year: Annotated[str, "Year in YYYY format for which temperature and radiation data is to be fetched"],
        save_path: Annotated[str, "Folder Path to save the temperature data CSV file"]
    ):
        """ Fetches daily rainfall data for a given location and year, calculates monthly statistics, and returns them as a JSON string.
        Output JSON Format:
        -------------------
        [
            {
                "month": "2020-01",     # Month in YYYY-MM format
                "avg_temp": 30.5,       # Mean Temperature of month (in °C)
                "avg_radiation": 10.02    # Mean shortwave radiation of month (in W/m²)
            },
            ...
        ] """
        try:
            os.makedirs(save_path, exist_ok=True)
            json_file_path = os.path.join(save_path, f"temperature{location.replace(' ', '_')}_{year}.json")
            
            coords = WeatherAPIUtils.get_coordinates(location)
            if not coords:
                return None
            lat, lon = coords
            
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as file:
                    weather_data = json.load(file)
            else:
                weather_data = WeatherAPIUtils.fetch_weather_data(lat, lon, "temperature_2m_mean,shortwave_radiation_sum", year)
                with open(json_file_path, 'w') as file:
                    json.dump(weather_data, file, indent=4)
    
            # if os.path.exists(file_path):
            #     return pd.read_csv(file_path)
            # monthly_data = []
    
            # for month in range(1, 13):  # Loop through all 12 months
            #     start_date = f"{year}-{month:02d}-01"
            #     end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            #     end_date = end_date.strftime("%Y-%m-%d")
    
            #     data = WeatherAPIUtils.fetch_weather_data(lat, lon, "temperature_2m_mean,shortwave_radiation_sum", start_date, end_date)
            #     if not data or "daily" not in data:
            #         continue
    
            #     temp_values = data["daily"].get("temperature_2m_mean", [])
            #     radiation_values = data["daily"].get("shortwave_radiation_sum", [])
    
            #     avg_temp = sum(temp_values) / len(temp_values) if temp_values else 0
            #     avg_radiation = sum(radiation_values) / len(radiation_values) if radiation_values else 0
            #     monthly_data.append([f"{year}-{month:02d}", avg_temp, avg_radiation])
            
            # Extract daily time, temperature data and radiation data
            dates = weather_data['daily']['time']
            temp_data = weather_data['daily']['temperature_2m_mean']
            radiation_data = weather_data['daily']['shortwave_radiation_sum']
    
            # Build DataFrame
            df = pd.DataFrame({
                'date': pd.to_datetime(dates),
                'temp': temp_data,
                'radiation': radiation_data
            })
            df['month'] = df['date'].dt.to_period('M')  # Format: YYYY-MM
    
            # Monthly stats calculation
            monthly_stats = df.groupby('month').agg(
            avg_temp=('temp', 'mean'),
            avg_radiation=('radiation', 'mean')
            ).reset_index()
    
             # Format result as JSON
            monthly_stats_json = []
            for _, row in monthly_stats.iterrows():
                monthly_stats_json.append({
                    "month": str(row['month']),
                    "avg_temp": round(row['avg_temp'],2),
                    "avg_radiation": round(row['avg_radiation'],2)
                })
    
            data_csv = pd.DataFrame(monthly_stats_json)
            data_csv.columns = ["Month", "Average Temperature (°C)", "Average Shortwave Radiation (W/m²)"]
            filename = f"temperature_{location.replace(' ', '_')}_{year}.csv"
            WeatherAPIUtils.save_data(data_csv, save_path, filename)
            return json.dumps(monthly_stats_json, indent=4)
        
        except Exception as e:
            return str(e)
    
    @staticmethod
    def new_get_monthly_rainfall(
    location: Annotated[str, "Name of location or address for rainfall data"],
    year: Annotated[str, "Year in YYYY format for which rainfall data is to be fetched"],
    save_path: Annotated[str, "Folder Path to save the rainfall data json file"]
    ) -> str:
        """ Fetches daily rainfall data for a given location and year, calculates monthly statistics, and returns them as a JSON string.
        Output JSON Format:
        -------------------
        [
            {
                "month": "2020-01",              # Month in YYYY-MM format
                "total_rainfall": 32.5,          # Sum of daily rainfall (mm)
                "median_rainfall": 1.2,          # Median daily rainfall
                "max_rainfall": 10.5,            # Maximum daily rainfall
                "rainy_days": 10               # Number of days it actually rained
            },
            ...
        ] """
        try:
            os.makedirs(save_path, exist_ok=True)
            json_file_path = os.path.join(save_path, f"rainfall_{location.replace(' ', '_')}_{year}.json")

            coords = WeatherAPIUtils.get_coordinates(location)
            if not coords:
                return None
            lat, lon = coords

            # Load or fetch the weather data
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as file:
                    weather_data = json.load(file)
            else:
                weather_data = WeatherAPIUtils.fetch_weather_data(lat, lon,"rain_sum",year)
                with open(json_file_path, 'w') as file:
                    json.dump(weather_data, file, indent=4)

            # Extract daily time and rain_sum data
            dates = weather_data['daily']['time']
            rainfalls = weather_data['daily']['rain_sum']

            # Build DataFrame
            df = pd.DataFrame({
                'date': pd.to_datetime(dates),
                'rainfall': rainfalls
            })
            df['month'] = df['date'].dt.to_period('M')  # Format: YYYY-MM

            # Monthly stats calculation
            monthly_stats = df.groupby('month')['rainfall'].agg(
                total_rainfall='sum',
                median_rainfall='median',
                min_rainfall='min',
                max_rainfall='max',
                rainy_days=lambda x: (x > 0).sum()
            ).reset_index()

            # Format result as JSON
            monthly_stats_json = []
            for _, row in monthly_stats.iterrows():
                monthly_stats_json.append({
                    "month": str(row['month']),
                    "total_rainfall": round(row['total_rainfall'],2),
                    "median_rainfall": round(row['median_rainfall'],2),
                    "max_rainfall": row['max_rainfall'],
                    "rainy_days": row['rainy_days']
                })
                
            data_csv = pd.DataFrame(monthly_stats_json)
            data_csv.columns = [
                "Month", "Total Rainfall (mm)", "Median Rainfall (mm)",
                "Max Rainfall (mm)", "Rainy Days Count"
            ]
            filename = f"rainfall_{location.replace(' ', '_')}_{year}.csv"
            WeatherAPIUtils.save_data(data_csv, save_path,filename)

            return json.dumps(monthly_stats_json, indent=4)

        except Exception as e:
            return str(e)
        
# Example usage
# if __name__ == "__main__":

#     data = WeatherAPIUtils.new_get_monthly_rainfall(
#         location="New York, USA",
#         year="2023",
#         save_path="./weather_data"
#     )
#     print(data)
