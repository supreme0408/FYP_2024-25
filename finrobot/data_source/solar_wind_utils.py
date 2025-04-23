
"""
SolarWind Class

A comprehensive class for retrieving, analyzing, and visualizing solar irradiance and wind data
for renewable energy suitability assessment.

This class combines functionality from the previous agent implementation into a single class
with static methods for easier use and integration.
"""

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

class SolarWind:
    """
    SolarWind class for retrieving, analyzing, and visualizing solar and wind data
    for renewable energy suitability assessment.
    """
    
    # Constants
    VERSION = "3.0.0"
    NAME = "SolarWind Renewable Energy Assessment Tool"
    OPENWEATHERMAP_API_KEY = "3debd8fec55dfc7d852be72d1381fd8f"
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
    def get_data(location, start_date=None, end_date=None, force_owm=False, output_file=None):
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
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
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
            formatted_data["renewable_energy_assessment"] = SolarWind._assess_renewable_energy_suitability(
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
            direct_radiation = solar_data["hourly"].get("direct_radiation", [None] * len(times))
            diffuse_radiation = solar_data["hourly"].get("diffuse_radiation", [None] * len(times))
            direct_normal_irradiance = solar_data["hourly"].get("direct_normal_irradiance", [None] * len(times))
            shortwave_radiation = solar_data["hourly"].get("shortwave_radiation", [None] * len(times))
            
            # Combine data
            for i in range(len(times)):
                # Calculate global horizontal irradiance (GHI) if possible
                ghi = None
                if direct_radiation[i] is not None and diffuse_radiation[i] is not None:
                    ghi = direct_radiation[i] + diffuse_radiation[i]
                elif shortwave_radiation[i] is not None:
                    ghi = shortwave_radiation[i]
                
                data_point = {
                    "time": times[i],
                    "direct_radiation": direct_radiation[i] if i < len(direct_radiation) else None,
                    "diffuse_radiation": diffuse_radiation[i] if i < len(diffuse_radiation) else None,
                    "direct_normal_irradiance": direct_normal_irradiance[i] if i < len(direct_normal_irradiance) else None,
                    "shortwave_radiation": shortwave_radiation[i] if i < len(shortwave_radiation) else None,
                    "global_horizontal_irradiance": ghi
                }
                
                formatted_solar["data"].append(data_point)
            
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
            wind_speed_10m = wind_data["hourly"].get("wind_speed_10m", [None] * len(times))
            wind_speed_100m = wind_data["hourly"].get("wind_speed_100m", [None] * len(times))
            wind_direction_10m = wind_data["hourly"].get("wind_direction_10m", [None] * len(times))
            wind_direction_100m = wind_data["hourly"].get("wind_direction_100m", [None] * len(times))
            wind_gusts_10m = wind_data["hourly"].get("wind_gusts_10m", [None] * len(times))
            
            # Combine data
            for i in range(len(times)):
                data_point = {
                    "time": times[i],
                    "wind_speed_10m": wind_speed_10m[i] if i < len(wind_speed_10m) else None,
                    "wind_speed_100m": wind_speed_100m[i] if i < len(wind_speed_100m) else None,
                    "wind_direction_10m": wind_direction_10m[i] if i < len(wind_direction_10m) else None,
                    "wind_direction_100m": wind_direction_100m[i] if i < len(wind_direction_100m) else None,
                    "wind_gusts_10m": wind_gusts_10m[i] if i < len(wind_gusts_10m) else None
                }
                
                formatted_wind["data"].append(data_point)
            
            return formatted_wind
            
        except Exception as e:
            raise ValueError(f"Error formatting wind data: {str(e)}")
    
    @staticmethod
    def _assess_renewable_energy_suitability(solar_data, wind_data):
        """
        Assess the suitability of a location for renewable energy based on solar and wind data.
        
        Args:
            solar_data (dict): Formatted solar data
            wind_data (dict): Formatted wind data
        
        Returns:
            dict: Renewable energy suitability assessment
        """
        assessment = {
            "timestamp": datetime.now().isoformat(),
            "solar_energy": {
                "average_daily_radiation": None,
                "suitability": None,
                "estimated_annual_production": None,
                "confidence": "low"
            },
            "wind_energy": {
                "average_wind_speed": None,
                "suitability": None,
                "estimated_annual_production": None,
                "confidence": "low"
            },
            "overall_recommendation": None
        }
        
        # Process solar data if available
        if "data" in solar_data and solar_data["data"]:
            # Calculate average daily radiation (kWh/m²/day)
            total_radiation = 0
            count = 0
            
            for point in solar_data["data"]:
                if point["global_horizontal_irradiance"] is not None:
                    # Convert W/m² to kWh/m² (assuming hourly data)
                    total_radiation += point["global_horizontal_irradiance"] / 1000
                    count += 1
            
            if count > 0:
                # Calculate daily average (assuming 24 hours of data per day)
                avg_daily_radiation = total_radiation / (count / 24)
                assessment["solar_energy"]["average_daily_radiation"] = round(avg_daily_radiation, 2)
                
                # Assess suitability
                if avg_daily_radiation >= SolarWind.SOLAR_THRESHOLDS["excellent"]:
                    suitability = "Excellent"
                elif avg_daily_radiation >= SolarWind.SOLAR_THRESHOLDS["good"]:
                    suitability = "Good"
                elif avg_daily_radiation >= SolarWind.SOLAR_THRESHOLDS["moderate"]:
                    suitability = "Moderate"
                elif avg_daily_radiation >= SolarWind.SOLAR_THRESHOLDS["poor"]:
                    suitability = "Poor"
                else:
                    suitability = "Unsuitable"
                
                assessment["solar_energy"]["suitability"] = suitability
                
                # Estimate annual production (kWh/kW)
                # Rough estimate: 1 kW of solar panels produces about 4 kWh per day for each kWh/m²/day of radiation
                annual_production = avg_daily_radiation * 365 * 4
                assessment["solar_energy"]["estimated_annual_production"] = round(annual_production)
                
                # Set confidence based on data points
                if count >= 168:  # At least 7 days of hourly data
                    assessment["solar_energy"]["confidence"] = "high"
                elif count >= 72:  # At least 3 days of hourly data
                    assessment["solar_energy"]["confidence"] = "medium"
        
        # Process wind data if available
        if "data" in wind_data and wind_data["data"]:
            # Calculate average wind speed
            total_wind_speed = 0
            count = 0
            
            for point in wind_data["data"]:
                if point["wind_speed_10m"] is not None:
                    total_wind_speed += point["wind_speed_10m"]
                    count += 1
            
            if count > 0:
                avg_wind_speed = total_wind_speed / count
                assessment["wind_energy"]["average_wind_speed"] = round(avg_wind_speed, 2)
                
                # Assess suitability
                if avg_wind_speed >= SolarWind.WIND_THRESHOLDS["excellent"]:
                    suitability = "Excellent"
                elif avg_wind_speed >= SolarWind.WIND_THRESHOLDS["good"]:
                    suitability = "Good"
                elif avg_wind_speed >= SolarWind.WIND_THRESHOLDS["moderate"]:
                    suitability = "Moderate"
                elif avg_wind_speed >= SolarWind.WIND_THRESHOLDS["poor"]:
                    suitability = "Poor"
                else:
                    suitability = "Unsuitable"
                
                assessment["wind_energy"]["suitability"] = suitability
                
                # Estimate annual production (kWh/kW)
                # Rough estimate based on wind speed cubed relationship
                # Assuming a 1 kW turbine at 10m height
                if avg_wind_speed >= 3.0:  # Minimum wind speed for most turbines
                    capacity_factor = min(0.45, 0.05 * (avg_wind_speed ** 2))  # Simplified capacity factor calculation
                    annual_production = capacity_factor * 8760  # 8760 hours in a year
                    assessment["wind_energy"]["estimated_annual_production"] = round(annual_production)
                else:
                    assessment["wind_energy"]["estimated_annual_production"] = 0
                
                # Set confidence based on data points
                if count >= 168:  # At least 7 days of hourly data
                    assessment["wind_energy"]["confidence"] = "high"
                elif count >= 72:  # At least 3 days of hourly data
                    assessment["wind_energy"]["confidence"] = "medium"
        
        # Overall recommendation
        solar_score = 0
        wind_score = 0
        
        if assessment["solar_energy"]["suitability"] == "Excellent":
            solar_score = 4
        elif assessment["solar_energy"]["suitability"] == "Good":
            solar_score = 3
        elif assessment["solar_energy"]["suitability"] == "Moderate":
            solar_score = 2
        elif assessment["solar_energy"]["suitability"] == "Poor":
            solar_score = 1
        
        if assessment["wind_energy"]["suitability"] == "Excellent":
            wind_score = 4
        elif assessment["wind_energy"]["suitability"] == "Good":
            wind_score = 3
        elif assessment["wind_energy"]["suitability"] == "Moderate":
            wind_score = 2
        elif assessment["wind_energy"]["suitability"] == "Poor":
            wind_score = 1
        
        if solar_score > 0 or wind_score > 0:
            if solar_score >= 3 and wind_score >= 3:
                assessment["overall_recommendation"] = "Excellent location for hybrid solar and wind energy systems"
            elif solar_score >= 3:
                assessment["overall_recommendation"] = "Excellent location for solar energy, " + (
                    "with potential for supplementary wind energy" if wind_score > 0 else "but not suitable for wind energy"
                )
            elif wind_score >= 3:
                assessment["overall_recommendation"] = "Excellent location for wind energy, " + (
                    "with potential for supplementary solar energy" if solar_score > 0 else "but not suitable for solar energy"
                )
            elif solar_score >= 2 and wind_score >= 2:
                assessment["overall_recommendation"] = "Moderate potential for hybrid solar and wind energy systems"
            elif solar_score >= 2:
                assessment["overall_recommendation"] = "Moderate potential for solar energy, limited potential for wind energy"
            elif wind_score >= 2:
                assessment["overall_recommendation"] = "Moderate potential for wind energy, limited potential for solar energy"
            else:
                assessment["overall_recommendation"] = "Limited potential for renewable energy, consider other locations or energy sources"
        else:
            assessment["overall_recommendation"] = "Insufficient data to make a recommendation"
        
        return assessment
    
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
    def visualize_solar_data(data, output_file=None):
        """
        Visualize solar irradiance data.
        
        Args:
            data (dict): Solar and wind data from get_data method
            output_file (str, optional): Path to save the visualization. Defaults to None.
        
        Returns:
            str or None: If output_file is None, returns a base64 encoded image.
                        Otherwise, saves the image to the specified file.
        
        Raises:
            ValueError: If there's an error creating the visualization
        """
        try:
            # Check if solar data is available
            if "solar_irradiance" not in data or "data" not in data["solar_irradiance"]:
                raise ValueError("No solar irradiance data available for visualization")
            
            # Extract data
            solar_data = data["solar_irradiance"]["data"]
            location_name = data["location"]["name"]
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(solar_data)
            df["time"] = pd.to_datetime(df["time"])
            
            # Set up the figure
            plt.figure(figsize=(12, 8))
            
            # Plot global horizontal irradiance
            plt.subplot(2, 1, 1)
            plt.plot(df["time"], df["global_horizontal_irradiance"], 'r-', label='Global Horizontal Irradiance')
            plt.title(f'Solar Irradiance Data for {location_name}')
            plt.ylabel('Irradiance (W/m²)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.gcf().autofmt_xdate()
            
            # Plot direct and diffuse radiation
            plt.subplot(2, 1, 2)
            plt.plot(df["time"], df["direct_radiation"], 'b-', label='Direct Radiation')
            plt.plot(df["time"], df["diffuse_radiation"], 'g-', label='Diffuse Radiation')
            plt.xlabel('Time')
            plt.ylabel('Radiation (W/m²)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.gcf().autofmt_xdate()
            
            # Add assessment information
            if "renewable_energy_assessment" in data and "solar_energy" in data["renewable_energy_assessment"]:
                assessment = data["renewable_energy_assessment"]["solar_energy"]
                avg_radiation = assessment.get("average_daily_radiation", "N/A")
                suitability = assessment.get("suitability", "N/A")
                annual_production = assessment.get("estimated_annual_production", "N/A")
                
                info_text = (
                    f"Average Daily Radiation: {avg_radiation} kWh/m²/day\n"
                    f"Suitability for Solar Energy: {suitability}\n"
                    f"Estimated Annual Production: {annual_production} kWh/kW"
                )
                
                plt.figtext(0.5, 0.01, info_text, ha='center', fontsize=12, 
                           bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
            
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])
            
            # Save or return the figure
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                # Return as base64 encoded image
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
            
        except Exception as e:
            raise ValueError(f"Error creating solar visualization: {str(e)}")
    
    @staticmethod
    def visualize_wind_data(data, output_file=None):
        """
        Visualize wind data.
        
        Args:
            data (dict): Solar and wind data from get_data method
            output_file (str, optional): Path to save the visualization. Defaults to None.
        
        Returns:
            str or None: If output_file is None, returns a base64 encoded image.
                        Otherwise, saves the image to the specified file.
        
        Raises:
            ValueError: If there's an error creating the visualization
        """
        try:
            # Check if wind data is available
            if "wind" not in data or "data" not in data["wind"]:
                raise ValueError("No wind data available for visualization")
            
            # Extract data
            wind_data = data["wind"]["data"]
            location_name = data["location"]["name"]
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(wind_data)
            df["time"] = pd.to_datetime(df["time"])
            
            # Set up the figure
            plt.figure(figsize=(12, 8))
            
            # Plot wind speed at 10m
            plt.subplot(2, 1, 1)
            plt.plot(df["time"], df["wind_speed_10m"], 'b-', label='Wind Speed at 10m')
            if "wind_speed_100m" in df.columns and not df["wind_speed_100m"].isna().all():
                plt.plot(df["time"], df["wind_speed_100m"], 'g-', label='Wind Speed at 100m')
            plt.title(f'Wind Data for {location_name}')
            plt.ylabel('Wind Speed (m/s)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Add horizontal lines for wind energy thresholds
            plt.axhline(y=SolarWind.WIND_THRESHOLDS["excellent"], color='r', linestyle='--', alpha=0.5, 
                       label=f'Excellent Threshold ({SolarWind.WIND_THRESHOLDS["excellent"]} m/s)')
            plt.axhline(y=SolarWind.WIND_THRESHOLDS["good"], color='g', linestyle='--', alpha=0.5, 
                       label=f'Good Threshold ({SolarWind.WIND_THRESHOLDS["good"]} m/s)')
            plt.axhline(y=SolarWind.WIND_THRESHOLDS["moderate"], color='y', linestyle='--', alpha=0.5, 
                       label=f'Moderate Threshold ({SolarWind.WIND_THRESHOLDS["moderate"]} m/s)')
            plt.legend()
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.gcf().autofmt_xdate()
            
            # Plot wind direction at 10m
            plt.subplot(2, 1, 2)
            plt.scatter(df["time"], df["wind_direction_10m"], c=df["wind_speed_10m"], 
                      cmap='viridis', alpha=0.7, s=20)
            plt.colorbar(label='Wind Speed (m/s)')
            plt.xlabel('Time')
            plt.ylabel('Wind Direction (degrees)')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.gcf().autofmt_xdate()
            
            # Add assessment information
            if "renewable_energy_assessment" in data and "wind_energy" in data["renewable_energy_assessment"]:
                assessment = data["renewable_energy_assessment"]["wind_energy"]
                avg_speed = assessment.get("average_wind_speed", "N/A")
                suitability = assessment.get("suitability", "N/A")
                annual_production = assessment.get("estimated_annual_production", "N/A")
                
                info_text = (
                    f"Average Wind Speed: {avg_speed} m/s\n"
                    f"Suitability for Wind Energy: {suitability}\n"
                    f"Estimated Annual Production: {annual_production} kWh/kW"
                )
                
                plt.figtext(0.5, 0.01, info_text, ha='center', fontsize=12, 
                           bbox={"facecolor":"lightblue", "alpha":0.2, "pad":5})
            
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])
            
            # Save or return the figure
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                # Return as base64 encoded image
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
            
        except Exception as e:
            raise ValueError(f"Error creating wind visualization: {str(e)}")
    
    @staticmethod
    def visualize_renewable_energy_potential(data, output_file=None):
        """
        Visualize renewable energy potential.
        
        Args:
            data (dict): Solar and wind data from get_data method
            output_file (str, optional): Path to save the visualization. Defaults to None.
        
        Returns:
            str or None: If output_file is None, returns a base64 encoded image.
                        Otherwise, saves the image to the specified file.
        
        Raises:
            ValueError: If there's an error creating the visualization
        """
        try:
            # Check if assessment data is available
            if "renewable_energy_assessment" not in data:
                raise ValueError("No renewable energy assessment data available for visualization")
            
            # Extract data
            assessment = data["renewable_energy_assessment"]
            location_name = data["location"]["name"]
            
            # Extract solar and wind assessment
            solar_assessment = assessment.get("solar_energy", {})
            wind_assessment = assessment.get("wind_energy", {})
            
            # Get values
            solar_avg = solar_assessment.get("average_daily_radiation", 0) or 0
            solar_suitability = solar_assessment.get("suitability", "Unknown")
            solar_production = solar_assessment.get("estimated_annual_production", 0) or 0
            
            wind_avg = wind_assessment.get("average_wind_speed", 0) or 0
            wind_suitability = wind_assessment.get("suitability", "Unknown")
            wind_production = wind_assessment.get("estimated_annual_production", 0) or 0
            
            # Set up the figure
            plt.figure(figsize=(12, 10))
            
            # Create a radar chart for suitability
            plt.subplot(2, 2, 1, polar=True)
            
            # Convert suitability to numeric values
            suitability_map = {
                "Excellent": 4,
                "Good": 3,
                "Moderate": 2,
                "Poor": 1,
                "Unsuitable": 0,
                "Unknown": 0
            }
            
            solar_value = suitability_map.get(solar_suitability, 0)
            wind_value = suitability_map.get(wind_suitability, 0)
            
            # Create radar chart data
            categories = ['Solar Energy', 'Wind Energy']
            values = [solar_value, wind_value]
            
            # Number of variables
            N = len(categories)
            
            # What will be the angle of each axis in the plot
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Close the loop
            
            # Add values
            values += values[:1]  # Close the loop
            
            # Draw the chart
            ax = plt.subplot(2, 2, 1, polar=True)
            
            # Draw one axis per variable and add labels
            plt.xticks(angles[:-1], categories, size=10)
            
            # Draw ylabels
            ax.set_rlabel_position(0)
            plt.yticks([1, 2, 3, 4], ["Poor", "Moderate", "Good", "Excellent"], color="grey", size=8)
            plt.ylim(0, 4)
            
            # Plot data
            ax.plot(angles, values, linewidth=2, linestyle='solid')
            
            # Fill area
            ax.fill(angles, values, 'b', alpha=0.1)
            
            plt.title('Renewable Energy Suitability', size=14)
            
            # Bar chart for estimated annual production
            plt.subplot(2, 2, 2)
            sources = ['Solar Energy', 'Wind Energy']
            production = [solar_production, wind_production]
            
            bars = plt.bar(sources, production, color=['orange', 'skyblue'])
            
            # Add values on top of bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 50,
                        f'{int(height)}',
                        ha='center', va='bottom', rotation=0, size=10)
            
            plt.title('Estimated Annual Production (kWh/kW)')
            plt.ylabel('kWh/kW')
            plt.grid(axis='y', alpha=0.3)
            
            # Daily profile of solar radiation
            plt.subplot(2, 2, 3)
            
            if "solar_irradiance" in data and "data" in data["solar_irradiance"]:
                solar_data = data["solar_irradiance"]["data"]
                df = pd.DataFrame(solar_data)
                df["time"] = pd.to_datetime(df["time"])
                
                # Extract hour of day
                df["hour"] = df["time"].dt.hour
                
                # Group by hour and calculate average
                hourly_avg = df.groupby("hour")["global_horizontal_irradiance"].mean()
                
                # Plot hourly average
                plt.plot(hourly_avg.index, hourly_avg.values, 'r-', marker='o')
                plt.title('Average Daily Solar Radiation Profile')
                plt.xlabel('Hour of Day')
                plt.ylabel('Global Horizontal Irradiance (W/m²)')
                plt.grid(True, alpha=0.3)
                plt.xticks(range(0, 24, 2))
            else:
                plt.text(0.5, 0.5, 'No solar data available', ha='center', va='center')
            
            # Daily profile of wind speed
            plt.subplot(2, 2, 4)
            
            if "wind" in data and "data" in data["wind"]:
                wind_data = data["wind"]["data"]
                df = pd.DataFrame(wind_data)
                df["time"] = pd.to_datetime(df["time"])
                
                # Extract hour of day
                df["hour"] = df["time"].dt.hour
                
                # Group by hour and calculate average
                hourly_avg = df.groupby("hour")["wind_speed_10m"].mean()
                
                # Plot hourly average
                plt.plot(hourly_avg.index, hourly_avg.values, 'b-', marker='o')
                plt.title('Average Daily Wind Speed Profile')
                plt.xlabel('Hour of Day')
                plt.ylabel('Wind Speed at 10m (m/s)')
                plt.grid(True, alpha=0.3)
                plt.xticks(range(0, 24, 2))
                
                # Add threshold lines
                plt.axhline(y=SolarWind.WIND_THRESHOLDS["excellent"], color='r', linestyle='--', alpha=0.5)
                plt.axhline(y=SolarWind.WIND_THRESHOLDS["good"], color='g', linestyle='--', alpha=0.5)
                plt.axhline(y=SolarWind.WIND_THRESHOLDS["moderate"], color='y', linestyle='--', alpha=0.5)
            else:
                plt.text(0.5, 0.5, 'No wind data available', ha='center', va='center')
            
            # Add overall recommendation
            overall_recommendation = assessment.get("overall_recommendation", "No recommendation available")
            plt.figtext(0.5, 0.01, f"Overall Recommendation: {overall_recommendation}", 
                       ha='center', fontsize=12, bbox={"facecolor":"lightgreen", "alpha":0.2, "pad":5})
            
            plt.suptitle(f'Renewable Energy Assessment for {location_name}', fontsize=16)
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])
            
            # Save or return the figure
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                return output_file
            else:
                # Return as base64 encoded image
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
            
        except Exception as e:
            raise ValueError(f"Error creating renewable energy potential visualization: {str(e)}")
    
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
            help="Start date in YYYY-MM-DD format (default: 7 days ago)",
            default=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
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
        
        parser.add_argument(
            "--force-owm",
            help="Force use of OpenWeatherMap API regardless of date range",
            action="store_true"
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
