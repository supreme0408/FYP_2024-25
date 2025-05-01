
"""
SolarWind Class

A comprehensive class for retrieving, analyzing, and visualizing solar irradiance and wind data
for renewable energy suitability assessment.

This class combines functionality from the previous agent implementation into a single class
with static methods for easier use and integration.
"""
import os
from typing import List
from pydantic import BaseModel
from openai import OpenAI
import sys
import os
import argparse
from datetime import datetime, timedelta
import json
import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from io import BytesIO
import base64
from dotenv import load_dotenv

load_dotenv()
# Access variables
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
# Initialize the OpenAI client
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
# Define a response model matching the static method output
# Define structured response models for solar and wind energy
class SolarEnergy(BaseModel):
    average_daily_radiation: float
    suitability: str
    estimated_annual_production: int
    confidence: str

class WindEnergy(BaseModel):
    average_wind_speed: float
    suitability: str
    estimated_annual_production: int
    confidence: str

# Combined assessment model
class RenewableEnergyAssessment(BaseModel):
    timestamp: str
    solar_energy: SolarEnergy
    wind_energy: WindEnergy
    overall_recommendation: str

class SolarWind:
    """
    SolarWind class for retrieving, analyzing, and visualizing solar and wind data
    for renewable energy suitability assessment.
    """
    
    # Constants
    VERSION = "3.0.0"
    NAME = "SolarWind Renewable Energy Assessment Tool"
    OPENWEATHERMAP_API_KEY = os.getenv("OWM_API_KEY")
    OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
    OPENWEATHERMAP_BASE_URL = "https://api.openweathermap.org/data"
    
    # Thresholds for renewable energy suitability
    SOLAR_THRESHOLDS = {
        "excellent": 5.5,  # kWh/m²/day
        "good": 4.0,
        "moderate": 3.0,
        "poor": 2.0
    }
    
    WIND_THRESHOLDS = {
        "excellent": 7.0,  # m/s
        "good": 5.0,
        "moderate": 3.5,
        "poor": 2.0
    }
    
    @staticmethod
    def process_location_input(location_input):
        """
        Process location input to extract latitude and longitude.
        
        Args:
            location_input (str): Location as coordinates (e.g., '40.7128, -74.0060') 
                                 or place name (e.g., 'New York City')
        
        Returns:
            dict: Dictionary containing latitude, longitude, and location name
        
        Raises:
            ValueError: If location input cannot be processed
        """
        try:
            # Check if input is coordinates
            if ',' in location_input and any(c.isdigit() for c in location_input):
                # Split by comma and strip whitespace
                parts = [p.strip() for p in location_input.split(',')]
                
                if len(parts) >= 2:
                    try:
                        latitude = float(parts[0])
                        longitude = float(parts[1])
                        
                        # Validate coordinates
                        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                            raise ValueError("Invalid coordinate values")
                        
                        # Try to get location name using reverse geocoding
                        location_name = SolarWind._reverse_geocode(latitude, longitude)
                        
                        return {
                            "latitude": latitude,
                            "longitude": longitude,
                            "location_name": location_name
                        }
                    except ValueError:
                        # If conversion fails, treat as place name
                        pass
            
            # If not coordinates or conversion failed, treat as place name
            geocode_result = SolarWind._geocode(location_input)
            
            return {
                "latitude": geocode_result["latitude"],
                "longitude": geocode_result["longitude"],
                "location_name": geocode_result["location_name"]
            }
        
        except Exception as e:
            raise ValueError(f"Could not process location input. Please provide valid coordinates or a place name. Error: {str(e)}")
    
    @staticmethod
    def _geocode(place_name):
        """
        Convert place name to coordinates using Nominatim API.
        
        Args:
            place_name (str): Name of the place to geocode
        
        Returns:
            dict: Dictionary containing latitude, longitude, and location name
        
        Raises:
            ValueError: If geocoding fails
        """
        try:
            # Use Nominatim API for geocoding
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": place_name,
                "format": "json",
                "limit": 1
            }
            headers = {
                "User-Agent": f"{SolarWind.NAME}/{SolarWind.VERSION}"
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                raise ValueError(f"Geocoding API request failed with status code {response.status_code}")
            
            data = response.json()
            
            if not data:
                raise ValueError(f"No results found for location: {place_name}")
            
            result = data[0]
            
            return {
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"]),
                "location_name": result.get("display_name", place_name).split(',')[0]
            }
        
        except Exception as e:
            raise ValueError(f"Unexpected error during geocoding: {str(e)}")
    
    @staticmethod
    def _reverse_geocode(latitude, longitude):
        """
        Convert coordinates to place name using Nominatim API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
        
        Returns:
            str: Name of the location
        """
        try:
            # Use Nominatim API for reverse geocoding
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json"
            }
            headers = {
                "User-Agent": f"{SolarWind.NAME}/{SolarWind.VERSION}"
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "name" in data:
                    return data["name"]
                elif "display_name" in data:
                    return data["display_name"].split(',')[0]
            
            # If reverse geocoding fails, return coordinates as string
            return f"{latitude}, {longitude}"
        
        except Exception:
            # If any error occurs, return coordinates as string
            return f"{latitude}, {longitude}"
    
    @staticmethod
    def get_data(location, start_date=None, end_date=None, force_owm=True, output_file=None):
        """
        Retrieve solar irradiance and wind data for a given location.
        
        Args:
            location (str): Location as coordinates or place name
            start_date (str, optional): Start date in YYYY-MM-DD format. Defaults to 7 days ago.
            end_date (str, optional): End date in YYYY-MM-DD format. Defaults to today.
            force_owm (bool, optional): Force use of OpenWeatherMap API. Defaults to False.
            output_file (str, optional): Output JSON file path. Defaults to None.
        
        Returns:
            dict: Dictionary containing solar and wind data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            # Process location input
            print(f"Processing location: {location}")
            location_info = SolarWind.process_location_input(location)
            
            latitude = location_info["latitude"]
            longitude = location_info["longitude"]
            location_name = location_info.get("location_name", f"{latitude}, {longitude}")
            
            print(f"Resolved location: {location_name} ({latitude}, {longitude})")
            
            # Set default dates if not provided
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Determine which API to use
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            open_meteo_limit = datetime(2016, 1, 1)
            owm_history_limit = datetime.now() - timedelta(days=365)  # Last year only
            
            use_openweathermap = force_owm
            
            if not use_openweathermap:
                if start_dt < open_meteo_limit:
                    if start_dt >= owm_history_limit:
                        use_openweathermap = True
                    else:
                        raise ValueError(
                            f"Date {start_date} is too far in the past for both APIs. "
                            f"Open-Meteo supports dates from 2016-01-01 onwards. "
                            f"Current OpenWeatherMap subscription supports approximately one year of historical data."
                        )
            
            if use_openweathermap:
                print(f"Using OpenWeatherMap API for data from {start_date} to {end_date}")
            else:
                print(f"Using Open-Meteo API for data from {start_date} to {end_date}")
            
            # Retrieve data
            print("Retrieving solar irradiance and wind data...")
            combined_data = SolarWind._get_combined_data(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                use_openweathermap=use_openweathermap
            )
            
            # Format the data
            print("Formatting data...")
            formatted_data = SolarWind._format_combined_data(
                solar_data=combined_data["solar_data"],
                wind_data=combined_data["wind_data"],
                location_info=location_info,
                start_date=start_date,
                end_date=end_date,
                data_source=combined_data["metadata"]["data_source"]
            )
            
            # Output the data
            if output_file:
                print(f"Saving data to {output_file}...")
                SolarWind._save_to_json_file(formatted_data, output_file)
                print(f"Data saved successfully to {output_file}")
            
            print("Data retrieval completed successfully.")
            return formatted_data
            
        except Exception as e:
            raise ValueError(f"Error retrieving data: {str(e)}")
    
    @staticmethod
    def _get_combined_data(latitude, longitude, start_date, end_date, use_openweathermap=False, retry_count=3, retry_delay=2):
        """
        Retrieve both solar radiation and wind data for a given location.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            use_openweathermap (bool, optional): Force use of OpenWeatherMap API. Defaults to False.
            retry_count (int, optional): Number of retry attempts. Defaults to 3.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 2.
        
        Returns:
            dict: Dictionary containing both solar and wind data
        
        Raises:
            ValueError: If there's an error retrieving the data after all retries
        """
        solar_data = None
        wind_data = None
        solar_error = None
        wind_error = None
        
        # Retry mechanism for solar data
        for attempt in range(retry_count):
            try:
                if use_openweathermap:
                    solar_data = SolarWind._get_solar_data_openweathermap(latitude, longitude, start_date, end_date)
                else:
                    solar_data = SolarWind._get_solar_data_openmeteo(latitude, longitude, start_date, end_date)
                solar_error = None
                break
            except Exception as e:
                solar_error = str(e)
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)
        
        # Retry mechanism for wind data
        for attempt in range(retry_count):
            try:
                if use_openweathermap:
                    wind_data = SolarWind._get_wind_data_openweathermap(latitude, longitude, start_date, end_date)
                else:
                    wind_data = SolarWind._get_wind_data_openmeteo(latitude, longitude, start_date, end_date)
                wind_error = None
                break
            except Exception as e:
                wind_error = str(e)
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)
        
        # Check if both retrievals failed
        if solar_error and wind_error:
            raise ValueError(f"Failed to retrieve both solar and wind data: Solar: {solar_error}, Wind: {wind_error}")
        
        # Prepare the result
        result = {
            "metadata": {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "retrieval_time": datetime.now().isoformat(),
                "data_source": "OpenWeatherMap" if use_openweathermap else "Open-Meteo"
            }
        }
        
        # Add solar data if available
        if solar_data:
            result["solar_data"] = solar_data
        else:
            result["solar_data"] = {"error": solar_error}
        
        # Add wind data if available
        if wind_data:
            result["wind_data"] = wind_data
        else:
            result["wind_data"] = {"error": wind_error}
        
        return result
    
    @staticmethod
    def _get_solar_data_openmeteo(latitude, longitude, start_date, end_date):
        """
        Retrieve solar radiation data from Open-Meteo API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
        
        Returns:
            dict: JSON response containing solar radiation data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            # Construct the API URL for solar radiation data
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "direct_radiation,diffuse_radiation,direct_normal_irradiance,shortwave_radiation",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "GMT"
            }
            
            # Make the API request
            response = requests.get(SolarWind.OPEN_METEO_BASE_URL, params=params)
            
            # Check if the request was successful
            if response.status_code != 200:
                raise ValueError(f"API request failed with status code {response.status_code}: {response.text}")
            
            # Parse the JSON response
            data = response.json()
            
            # Return the data
            return data
        
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error making request to Open-Meteo API: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error retrieving solar radiation data from Open-Meteo: {str(e)}")
    
    @staticmethod
    def _get_solar_data_openweathermap(latitude, longitude, start_date, end_date):
        """
        Retrieve solar radiation data from OpenWeatherMap API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
        
        Returns:
            dict: JSON response containing solar radiation data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            # For current subscription, we'll use the forecast and current data
            
            # Get current weather data
            current_data = SolarWind._get_current_weather_owm(latitude, longitude)
            
            # Get forecast data
            forecast_data = SolarWind._get_forecast_owm(latitude, longitude)
            
            # Format the data to match Open-Meteo structure as closely as possible
            formatted_data = SolarWind._format_owm_current_forecast_to_solar(
                current_data, forecast_data, latitude, longitude
            )
            
            return formatted_data
        
        except Exception as e:
            raise ValueError(f"Error retrieving solar radiation data from OpenWeatherMap: {str(e)}")
    
    @staticmethod
    def _get_current_weather_owm(latitude, longitude, units="metric"):
        """
        Get current weather data from OpenWeatherMap API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            units (str, optional): Units of measurement. Defaults to "metric".
        
        Returns:
            dict: Current weather data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            url = f"{SolarWind.OPENWEATHERMAP_BASE_URL}/2.5/weather"
            
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": SolarWind.OPENWEATHERMAP_API_KEY,
                "units": units
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                raise ValueError(f"API request failed with status code {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error making request to OpenWeatherMap API: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error retrieving current weather data: {str(e)}")
    
    @staticmethod
    def _get_forecast_owm(latitude, longitude, units="metric"):
        """
        Get 5-day weather forecast data from OpenWeatherMap API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            units (str, optional): Units of measurement. Defaults to "metric".
        
        Returns:
            dict: Forecast weather data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            url = f"{SolarWind.OPENWEATHERMAP_BASE_URL}/2.5/forecast"
            
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": SolarWind.OPENWEATHERMAP_API_KEY,
                "units": units
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                raise ValueError(f"API request failed with status code {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error making request to OpenWeatherMap API: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error retrieving forecast data: {str(e)}")
    
    @staticmethod
    def _format_owm_current_forecast_to_solar(current_data, forecast_data, latitude, longitude):
        """
        Format OpenWeatherMap current and forecast data to match Open-Meteo solar data structure.
        
        Args:
            current_data (dict): Current weather data from OpenWeatherMap
            forecast_data (dict): Forecast data from OpenWeatherMap
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
        
        Returns:
            dict: Formatted solar data
        """
        # Initialize the structure
        formatted_data = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "GMT",
            "timezone_abbreviation": "GMT",
            "hourly": {
                "time": [],
                "direct_radiation": [],
                "diffuse_radiation": [],
                "direct_normal_irradiance": [],
                "shortwave_radiation": []
            },
            "hourly_units": {
                "direct_radiation": "W/m²",
                "diffuse_radiation": "W/m²",
                "direct_normal_irradiance": "W/m²",
                "shortwave_radiation": "W/m²"
            }
        }
        
        # Process current data
        if "dt" in current_data:
            current_dt = datetime.fromtimestamp(current_data["dt"])
            time_str = current_dt.strftime('%Y-%m-%dT%H:%M')
            formatted_data["hourly"]["time"].append(time_str)
            
            # Extract solar data from current weather
            # Note: OpenWeatherMap current data doesn't directly provide solar radiation
            # We'll use weather conditions as a proxy
            clouds = current_data.get("clouds", {}).get("all", 0)
            weather_id = current_data.get("weather", [{}])[0].get("id", 800)
            
            # Estimate solar radiation based on weather conditions
            # This is a very rough approximation
            if weather_id >= 800:  # Clear or mostly clear
                direct_radiation = max(0, 1000 - (clouds * 5))
                diffuse_radiation = 200 + (clouds * 3)
            else:  # Cloudy or precipitation
                direct_radiation = max(0, 500 - (clouds * 5))
                diffuse_radiation = 300 + (clouds * 2)
            
            formatted_data["hourly"]["direct_radiation"].append(direct_radiation)
            formatted_data["hourly"]["diffuse_radiation"].append(diffuse_radiation)
            formatted_data["hourly"]["direct_normal_irradiance"].append(direct_radiation)
            formatted_data["hourly"]["shortwave_radiation"].append(direct_radiation + diffuse_radiation)
        
        # Process forecast data
        if "list" in forecast_data:
            for forecast in forecast_data["list"]:
                if "dt" in forecast:
                    forecast_dt = datetime.fromtimestamp(forecast["dt"])
                    time_str = forecast_dt.strftime('%Y-%m-%dT%H:%M')
                    formatted_data["hourly"]["time"].append(time_str)
                    
                    # Extract solar data from forecast
                    clouds = forecast.get("clouds", {}).get("all", 0)
                    weather_id = forecast.get("weather", [{}])[0].get("id", 800)
                    
                    # Estimate solar radiation based on weather conditions
                    if weather_id >= 800:  # Clear or mostly clear
                        direct_radiation = max(0, 1000 - (clouds * 5))
                        diffuse_radiation = 200 + (clouds * 3)
                    else:  # Cloudy or precipitation
                        direct_radiation = max(0, 500 - (clouds * 5))
                        diffuse_radiation = 300 + (clouds * 2)
                    
                    formatted_data["hourly"]["direct_radiation"].append(direct_radiation)
                    formatted_data["hourly"]["diffuse_radiation"].append(diffuse_radiation)
                    formatted_data["hourly"]["direct_normal_irradiance"].append(direct_radiation)
                    formatted_data["hourly"]["shortwave_radiation"].append(direct_radiation + diffuse_radiation)
        
        return formatted_data
    
    @staticmethod
    def _get_wind_data_openmeteo(latitude, longitude, start_date, end_date):
        """
        Retrieve wind data from Open-Meteo API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
        
        Returns:
            dict: JSON response containing wind data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            # Construct the API URL for wind data
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "wind_speed_10m,wind_speed_100m,wind_direction_10m,wind_direction_100m,wind_gusts_10m",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "GMT"
            }
            
            # Make the API request
            response = requests.get(SolarWind.OPEN_METEO_BASE_URL, params=params)
            
            # Check if the request was successful
            if response.status_code != 200:
                raise ValueError(f"API request failed with status code {response.status_code}: {response.text}")
            
            # Parse the JSON response
            data = response.json()
            
            # Return the data
            return data
        
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error making request to Open-Meteo API: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error retrieving wind data from Open-Meteo: {str(e)}")
    
    @staticmethod
    def _get_wind_data_openweathermap(latitude, longitude, start_date, end_date):
        """
        Retrieve wind data from OpenWeatherMap API.
        
        Args:
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
        
        Returns:
            dict: JSON response containing wind data
        
        Raises:
            ValueError: If there's an error retrieving the data
        """
        try:
            # For current subscription, we'll use the forecast and current data
            
            # Get current weather data
            current_data = SolarWind._get_current_weather_owm(latitude, longitude)
            
            # Get forecast data
            forecast_data = SolarWind._get_forecast_owm(latitude, longitude)
            
            # Format the data to match Open-Meteo structure
            formatted_data = SolarWind._format_owm_current_forecast_to_wind(
                current_data, forecast_data, latitude, longitude
            )
            
            return formatted_data
        
        except Exception as e:
            raise ValueError(f"Error retrieving wind data from OpenWeatherMap: {str(e)}")
    
    @staticmethod
    def _format_owm_current_forecast_to_wind(current_data, forecast_data, latitude, longitude):
        """
        Format OpenWeatherMap current and forecast data to match Open-Meteo wind data structure.
        
        Args:
            current_data (dict): Current weather data from OpenWeatherMap
            forecast_data (dict): Forecast data from OpenWeatherMap
            latitude (float): Latitude of the location
            longitude (float): Longitude of the location
        
        Returns:
            dict: Formatted wind data
        """
        # Initialize the structure
        formatted_data = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "GMT",
            "timezone_abbreviation": "GMT",
            "hourly": {
                "time": [],
                "wind_speed_10m": [],
                "wind_direction_10m": []
            },
            "hourly_units": {
                "wind_speed_10m": "m/s",
                "wind_direction_10m": "°"
            }
        }
        
        # Process current data
        if "dt" in current_data and "wind" in current_data:
            current_dt = datetime.fromtimestamp(current_data["dt"])
            time_str = current_dt.strftime('%Y-%m-%dT%H:%M')
            formatted_data["hourly"]["time"].append(time_str)
            
            # Extract wind data
            wind_data = current_data["wind"]
            wind_speed = wind_data.get("speed", None)
            wind_dir = wind_data.get("deg", None)
            
            formatted_data["hourly"]["wind_speed_10m"].append(wind_speed)
            formatted_data["hourly"]["wind_direction_10m"].append(wind_dir)
        
        # Process forecast data
        if "list" in forecast_data:
            for forecast in forecast_data["list"]:
                if "dt" in forecast and "wind" in forecast:
                    forecast_dt = datetime.fromtimestamp(forecast["dt"])
                    time_str = forecast_dt.strftime('%Y-%m-%dT%H:%M')
                    formatted_data["hourly"]["time"].append(time_str)
                    
                    # Extract wind data
                    wind_data = forecast["wind"]
                    wind_speed = wind_data.get("speed", None)
                    wind_dir = wind_data.get("deg", None)
                    
                    formatted_data["hourly"]["wind_speed_10m"].append(wind_speed)
                    formatted_data["hourly"]["wind_direction_10m"].append(wind_dir)
        
        return formatted_data
    
    @staticmethod
    def _format_combined_data(solar_data, wind_data, location_info, start_date, end_date, data_source):
        """
        Format combined solar and wind data into a standardized structure.
        
        Args:
            solar_data (dict): Solar radiation data
            wind_data (dict): Wind data
            location_info (dict): Location information
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            data_source (str): Source of the data (OpenWeatherMap or Open-Meteo)
        
        Returns:
            dict: Formatted combined data
        
        Raises:
            ValueError: If there's an error formatting the data
        """
        try:
            # Extract location information
            latitude = location_info["latitude"]
            longitude = location_info["longitude"]
            location_name = location_info.get("location_name", f"{latitude}, {longitude}")
            
            # Create the base structure
            formatted_data = {
                "metadata": {
                    "source": "SolarWind Renewable Energy Assessment Tool",
                    "version": SolarWind.VERSION,
                    "timestamp": datetime.now().isoformat(),
                    "query_time": datetime.now().isoformat(),
                    "data_source": data_source,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": location_name
                }
            }
            
            # Format solar data
            if "error" in solar_data:
                formatted_data["solar_irradiance"] = {
                    "error": solar_data["error"]
                }
            else:
                formatted_data["solar_irradiance"] = SolarWind._format_solar_data(solar_data)
            
            # Format wind data
            if "error" in wind_data:
                formatted_data["wind"] = {
                    "error": wind_data["error"]
                }
            else:
                formatted_data["wind"] = SolarWind._format_wind_data(wind_data)
            
            # Add renewable energy suitability assessment
            formatted_data["renewable_energy_assessment"] = SolarWind.assess_renewable_energy_suitability(
                formatted_data["solar_irradiance"], 
                formatted_data["wind"]
            )
            
            return formatted_data
            
        except Exception as e:
            raise ValueError(f"Error formatting combined data: {str(e)}")
    
    @staticmethod
    def _format_solar_data(solar_data):
        """
        Format solar data into a standardized structure.
        
        Args:
            solar_data (dict): Solar radiation data
        
        Returns:
            dict: Formatted solar data
        
        Raises:
            ValueError: If there's an error formatting the data
        """
        try:
            # Extract metadata
            formatted_solar = {
                "metadata": {
                    "source": solar_data.get("data_source", "Open-Meteo API"),
                    "timestamp": datetime.now().isoformat(),
                    "timezone": solar_data.get("timezone", "GMT"),
                    "timezone_abbreviation": solar_data.get("timezone_abbreviation", "GMT"),
                    "elevation": solar_data.get("elevation", None)
                },
                "location": {
                    "latitude": solar_data.get("latitude", None),
                    "longitude": solar_data.get("longitude", None)
                },
                "data": [],
                "units": {
                    "direct_radiation": "W/m²",
                    "diffuse_radiation": "W/m²",
                    "direct_normal_irradiance": "W/m²",
                    "shortwave_radiation": "W/m²",
                    "global_horizontal_irradiance": "W/m²"
                }
            }
            
            # Check if hourly data exists
            if "hourly" not in solar_data or "time" not in solar_data["hourly"]:
                raise ValueError("Missing hourly time data in API response")
            
            # Extract hourly data
            times = solar_data["hourly"]["time"]
            direct = np.array(solar_data["hourly"].get("direct_radiation", [np.nan]*len(times)))
            diffuse = np.array(solar_data["hourly"].get("diffuse_radiation", [np.nan]*len(times)))
            dni = np.array(solar_data["hourly"].get("direct_normal_irradiance", [np.nan]*len(times)))
            shortwave = np.array(solar_data["hourly"].get("shortwave_radiation", [np.nan]*len(times)))
            
            # Dimensionality reduction: take 24-hour average per day
            df = pd.DataFrame({
                "time": pd.to_datetime(times),
                "direct": direct,
                "diffuse": diffuse,
                "dni": dni,
                "shortwave": shortwave
            })
            df["day"] = df["time"].dt.date
            daily_avg = df.groupby("day").mean(numeric_only=True).reset_index()

            formatted_data = []
            for _, row in daily_avg.iterrows():
                ghi = None
                if not np.isnan(row["direct"]) and not np.isnan(row["diffuse"]):
                    ghi = row["direct"] + row["diffuse"]
                elif not np.isnan(row["shortwave"]):
                    ghi = row["shortwave"]

                formatted_data.append({
                    "date": str(row["day"]),
                    "direct_radiation": round(row["direct"], 2) if not np.isnan(row["direct"]) else None,
                    "diffuse_radiation": round(row["diffuse"], 2) if not np.isnan(row["diffuse"]) else None,
                    "direct_normal_irradiance": round(row["dni"], 2) if not np.isnan(row["dni"]) else None,
                    "shortwave_radiation": round(row["shortwave"], 2) if not np.isnan(row["shortwave"]) else None,
                    "global_horizontal_irradiance": round(ghi, 2) if ghi is not None else None
                })

            formatted_solar["data"] = formatted_data
            return formatted_solar

            
        except Exception as e:
            raise ValueError(f"Error formatting solar data: {str(e)}")
    
    @staticmethod
    def _format_wind_data(wind_data):
        """
        Format wind data into a standardized structure.
        
        Args:
            wind_data (dict): Wind data
        
        Returns:
            dict: Formatted wind data
        
        Raises:
            ValueError: If there's an error formatting the data
        """
        try:
            # Extract metadata
            formatted_wind = {
                "metadata": {
                    "source": wind_data.get("data_source", "Open-Meteo API"),
                    "timestamp": datetime.now().isoformat(),
                    "timezone": wind_data.get("timezone", "GMT"),
                    "timezone_abbreviation": wind_data.get("timezone_abbreviation", "GMT"),
                    "elevation": wind_data.get("elevation", None)
                },
                "location": {
                    "latitude": wind_data.get("latitude", None),
                    "longitude": wind_data.get("longitude", None)
                },
                "data": [],
                "units": {
                    "wind_speed_10m": "m/s",
                    "wind_speed_100m": "m/s",
                    "wind_direction_10m": "°",
                    "wind_direction_100m": "°",
                    "wind_gusts_10m": "m/s"
                }
            }
            
            # Check if hourly data exists
            if "hourly" not in wind_data or "time" not in wind_data["hourly"]:
                raise ValueError("Missing hourly time data in API response")
            
            # Extract hourly data
            times = wind_data["hourly"]["time"]
            ws10 = np.array(wind_data["hourly"].get("wind_speed_10m", [np.nan]*len(times)))
            ws100 = np.array(wind_data["hourly"].get("wind_speed_100m", [np.nan]*len(times)))
            wd10 = np.array(wind_data["hourly"].get("wind_direction_10m", [np.nan]*len(times)))
            wd100 = np.array(wind_data["hourly"].get("wind_direction_100m", [np.nan]*len(times)))
            gust = np.array(wind_data["hourly"].get("wind_gusts_10m", [np.nan]*len(times)))

            df = pd.DataFrame({
                "time": pd.to_datetime(times),
                "ws10": ws10,
                "ws100": ws100,
                "wd10": wd10,
                "wd100": wd100,
                "gust": gust
            })
            df["day"] = df["time"].dt.date
            daily_avg = df.groupby("day").mean(numeric_only=True).reset_index()

            formatted_data = []
            for _, row in daily_avg.iterrows():
                formatted_data.append({
                    "date": str(row["day"]),
                    "wind_speed_10m": round(row["ws10"], 2) if not np.isnan(row["ws10"]) else None,
                    "wind_speed_100m": round(row["ws100"], 2) if not np.isnan(row["ws100"]) else None,
                    "wind_direction_10m": round(row["wd10"], 2) if not np.isnan(row["wd10"]) else None,
                    "wind_direction_100m": round(row["wd100"], 2) if not np.isnan(row["wd100"]) else None,
                    "wind_gusts_10m": round(row["gust"], 2) if not np.isnan(row["gust"]) else None
                })

            formatted_wind["data"] = formatted_data
            return formatted_wind

        except Exception as e:
            raise ValueError(f"Error formatting wind data: {str(e)}")
    
    @staticmethod 
    def assess_renewable_energy_suitability(solar_data, wind_data):
        # Use a large language model to generate a realistic assessment
        completion = client.beta.chat.completions.parse(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": \
                    "You are a leading renewable energy analyst. "  \
                    "Given detailed solar and wind datasets, compute key metrics, compare against industry thresholds, "  \
                    "and critically evaluate suitability. "  \
                    "If the input data contradicts known norms, prioritize the more reliable source. "  \
                    "Return a single JSON object matching the RenewableEnergyAssessment schema with these fields:\n"  \
                    "- timestamp (ISO 8601)\n"  \
                    "- solar_energy: { average_daily_radiation (kWh/m²/day), suitability (Excellent|Good|Moderate|Poor|Unsuitable), estimated_annual_production (kWh/kW), confidence (High|Medium|Low) }\n"  \
                    "- wind_energy: { average_wind_speed (m/s), suitability (Excellent|Good|Moderate|Poor|Unsuitable), estimated_annual_production (kWh/kW), confidence (High|Medium|Low) }\n"  \
                    "- overall_recommendation: concise summary."},
                {"role": "user", "content": f"Solar data: {json.dumps(solar_data)}; Wind data: {json.dumps(wind_data)}"},
            ],
            response_format=RenewableEnergyAssessment,
        )
        # Parsed result will be an instance of RenewableEnergyAssessment
        return completion.choices[0].message.parsed.json()

    
    @staticmethod
    def _save_to_json_file(data, file_path):
        """
        Save data to a JSON file.
        
        Args:
            data (dict): Data to save
            file_path (str): Path to save the file
        
        Raises:
            ValueError: If there's an error saving the file
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise ValueError(f"Error saving data to file: {str(e)}")


    @staticmethod
    def visualize_solar_data(json_data, output_file=None):
        try:
            records = json_data.get("solar_irradiance", {}).get("data")
            if not records:
                raise ValueError("No solar irradiance data available for visualization")

            df = pd.DataFrame(records)
            # parse timestamp
            if "date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["date"])
            elif "time" in df.columns:
                df["timestamp"] = pd.to_datetime(df["time"])
            else:
                raise ValueError("No date/time column found in solar data")

            location_name = json_data.get("location", {}).get("name", "Unknown Location")

            plt.figure(figsize=(12, 8))
            plt.subplot(2, 1, 1)
            plt.plot(df["timestamp"], df.get("global_horizontal_irradiance", []), label='GHI')
            plt.title(f'Solar Irradiance for {location_name}')
            plt.ylabel('W/m²')
            plt.grid(alpha=0.3)
            plt.legend()
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()

            plt.subplot(2, 1, 2)
            if "direct_radiation" in df.columns:
                plt.plot(df["timestamp"], df["direct_radiation"], label='Direct')
            if "diffuse_radiation" in df.columns:
                plt.plot(df["timestamp"], df["diffuse_radiation"], label='Diffuse')
            plt.xlabel('Date')
            plt.ylabel('W/m²')
            plt.grid(alpha=0.3)
            plt.legend()
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()

            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                return base64.b64encode(buf.read()).decode('utf-8')

        except Exception as e:
            raise ValueError(f"Error creating solar visualization: {e}")

    @staticmethod
    def visualize_wind_data(json_data, output_file=None):
        try:
            records = json_data.get("wind", {}).get("data")
            if not records:
                raise ValueError("No wind data available for visualization")

            df = pd.DataFrame(records)
            if "date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["date"])
            elif "time" in df.columns:
                df["timestamp"] = pd.to_datetime(df["time"])
            else:
                raise ValueError("No date/time column found in wind data")

            location_name = json_data.get("location", {}).get("name", "Unknown Location")

            plt.figure(figsize=(12, 8))
            plt.subplot(2, 1, 1)
            plt.plot(df["timestamp"], df.get("wind_speed_10m", []), label='Speed 10m')
            if "wind_speed_100m" in df.columns:
                plt.plot(df["timestamp"], df["wind_speed_100m"], label='Speed 100m')
            plt.title(f'Wind Speed for {location_name}')
            plt.ylabel('m/s')
            plt.grid(alpha=0.3)
            plt.legend()
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()

            plt.subplot(2, 1, 2)
            if "wind_direction_10m" in df.columns:
                plt.scatter(df["timestamp"], df["wind_direction_10m"], s=20)
            plt.xlabel('Date')
            plt.ylabel('°')
            plt.grid(alpha=0.3)

            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                return base64.b64encode(buf.read()).decode('utf-8')

        except Exception as e:
            raise ValueError(f"Error creating wind visualization: {e}")

    @staticmethod
    def visualize_renewable_energy_potential(json_data, output_file=None):
        try:
            # parse assessment if it's a JSON string
            assessment = json_data.get("renewable_energy_assessment")
            if isinstance(assessment, str):
                assessment = json.loads(assessment)
            if not assessment:
                raise ValueError("No assessment data available")

            location_name = json_data.get("location", {}).get("name", "Unknown")

            solar = assessment.get("solar_energy")
            if isinstance(solar, str): solar = json.loads(solar)
            wind = assessment.get("wind_energy")
            if isinstance(wind, str): wind = json.loads(wind)

            suit_map = {"Excellent":4, "Good":3, "Moderate":2, "Poor":1, "Unsuitable":0, "Unknown":0}
            vals = [suit_map.get(solar.get("suitability"), 0), suit_map.get(wind.get("suitability"), 0)]
            cats = ["Solar","Wind"]
            N = len(cats)
            angles = [n/float(N)*2*np.pi for n in range(N)] + [0]
            vals += vals[:1]

            plt.figure(figsize=(12,10))
            ax = plt.subplot(2,2,1, polar=True)
            plt.xticks(angles[:-1], cats)
            ax.set_rlabel_position(0)
            plt.yticks([1,2,3,4], ["Poor","Moderate","Good","Excellent"], size=8)
            plt.ylim(0,4)
            ax.plot(angles, vals, linewidth=2)
            ax.fill(angles, vals, alpha=0.1)
            plt.title("Suitability")

            plt.subplot(2,2,2)
            prods = [solar.get("estimated_annual_production",0), wind.get("estimated_annual_production",0)]
            bars = plt.bar(cats, prods)
            for b in bars:
                h = b.get_height()
                plt.text(b.get_x()+b.get_width()/2, h*1.01, str(int(h)), ha='center')
            plt.title("Annual Production (kWh/kW)")

            overall = assessment.get("overall_recommendation","None")
            plt.figtext(0.5,0.01,f"Overall: {overall}", ha='center')

            plt.suptitle(f"Renewable Assessment for {location_name}")
            plt.tight_layout(rect=[0,0.05,1,0.95])

            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                return base64.b64encode(buf.read()).decode('utf-8')

        except Exception as e:
            raise ValueError(f"Error creating potential visualization: {e}")


    @staticmethod
    def run_from_command_line():
        """
        Run the SolarWind tool from the command line.
        """
        parser = argparse.ArgumentParser(
            description="SolarWind: Retrieve and analyze solar irradiance and wind data for renewable energy assessment.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        parser.add_argument(
            "location",
            help="Location as coordinates (e.g., '40.7128, -74.0060') or place name (e.g., 'New York City')"
        )
        
        parser.add_argument(
            "--start",
            help="Start date in YYYY-MM-DD format (default: 30 days ago)",
            default=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        )
        
        parser.add_argument(
            "--end",
            help="End date in YYYY-MM-DD format (default: today)",
            default=datetime.now().strftime('%Y-%m-%d')
        )
        
        parser.add_argument(
            "--output",
            help="Output JSON file path (default: prints to console)",
            default=None
        )
        
        # by default OpenWeatherMap is used; to disable, pass --no-owm
        parser.add_argument(
            "--no-owm",
            help="Disable default OpenWeatherMap API usage",
            action="store_false",
            dest="force_owm"
        )
        
        parser.add_argument(
            "--visualize",
            help="Generate visualizations (options: solar, wind, potential, all)",
            choices=["solar", "wind", "potential", "all"],
            default=None
        )
        
        parser.add_argument(
            "--viz-output",
            help="Directory to save visualization files (default: current directory)",
            default="."
        )
        
        args = parser.parse_args()
        
        try:
            # Get data
            data = SolarWind.get_data(
                location=args.location,
                start_date=args.start,
                end_date=args.end,
                force_owm=args.force_owm,
                output_file=args.output
            )
            
            # Generate visualizations if requested
            if args.visualize:
                viz_dir = args.viz_output
                location_slug = args.location.replace(" ", "_").replace(",", "").lower()
                
                if args.visualize in ["solar", "all"]:
                    solar_file = os.path.join(viz_dir, f"{location_slug}_solar.png")
                    SolarWind.visualize_solar_data(data, solar_file)
                    print(f"Solar visualization saved to {solar_file}")
                
                if args.visualize in ["wind", "all"]:
                    wind_file = os.path.join(viz_dir, f"{location_slug}_wind.png")
                    SolarWind.visualize_wind_data(data, wind_file)
                    print(f"Wind visualization saved to {wind_file}")
                
                if args.visualize in ["potential", "all"]:
                    potential_file = os.path.join(viz_dir, f"{location_slug}_potential.png")
                    SolarWind.visualize_renewable_energy_potential(data, potential_file)
                    print(f"Renewable energy potential visualization saved to {potential_file}")
            
            # If no output file specified, print the data
            if not args.output:
                print(json.dumps(data, indent=2))
            
            return 0
            
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

if __name__ == "__main__":
    sys.exit(SolarWind.run_from_command_line())
