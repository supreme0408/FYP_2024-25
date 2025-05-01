import requests
import math
import time
import statistics
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List, Union
from collections import Counter

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
    def get_current_weather(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Gets current weather data for a specified location.
        
        Returns:
            JSON object with current weather data or None if location not found
        """
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'units': 'metric'}

        data = OpenWeatherAPI.fetch_weather_data('weather', params)
        if data and 'weather' in data and len(data['weather']) > 0:
            # Add the weather description from our map
            weather_id = data['weather'][0]['id']
            data['weather_description'] = WEATHER_CODE_MAP.get(weather_id, data['weather'][0]['description'])
        
        return data

    @staticmethod
    def get_mode_weather(weather_list: List[Dict]) -> Dict:
        """Gets the most common weather condition from a list of weather data"""
        if not weather_list:
            return {}
            
        weather_ids = [item['id'] for item in weather_list]
        if not weather_ids:
            return {}
            
        most_common_id = Counter(weather_ids).most_common(1)[0][0]
        
        # Find the first weather item with this ID
        for item in weather_list:
            if item['id'] == most_common_id:
                return {
                    'id': item['id'],
                    'main': item['main'],
                    'description': item['description'],
                    'icon': item['icon'],
                    'readable_description': WEATHER_CODE_MAP.get(item['id'], item['description'])
                }
                
        return {}

    @staticmethod
    def get_hourly_forecast_condensed(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None,
                                     interval_hours: int = 6) -> Optional[Dict[str, Any]]:
        """Gets condensed hourly weather forecast grouped into specified intervals.
        
        Args:
            city_name: Name of the city
            state_code: State code (optional)
            country_code: Country code (optional)
            interval_hours: Number of hours to group forecasts by (default: 6)
            
        Returns:
            Condensed JSON with hourly forecast grouped by time intervals
        """
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'units': 'metric'}
        data = OpenWeatherAPI.fetch_weather_data('forecast', params)
        
        if not data or 'list' not in data:
            return None
            
        # Group forecast data by intervals
        intervals = {}
        city_info = data.get('city', {})
        
        for forecast_item in data['list']:
            dt = datetime.fromtimestamp(forecast_item['dt'])
            
            # Create interval key (e.g., "2025-04-29 00:00" for a 6-hour interval starting at midnight)
            interval_start = dt.replace(hour=(dt.hour // interval_hours) * interval_hours, minute=0, second=0)
            interval_key = interval_start.strftime("%Y-%m-%d %H:%M")
            
            if interval_key not in intervals:
                intervals[interval_key] = {
                    'start_time': interval_start.isoformat(),
                    'end_time': (interval_start + timedelta(hours=interval_hours)).isoformat(),
                    'temperatures': [],
                    'feels_like': [],
                    'humidity': [],
                    'pressure': [],
                    'wind_speed': [],
                    'weather_items': []
                }
            
            # Collect data for statistics
            intervals[interval_key]['temperatures'].append(forecast_item['main']['temp'])
            intervals[interval_key]['feels_like'].append(forecast_item['main']['feels_like'])
            intervals[interval_key]['humidity'].append(forecast_item['main']['humidity'])
            intervals[interval_key]['pressure'].append(forecast_item['main']['pressure'])
            if 'wind' in forecast_item and 'speed' in forecast_item['wind']:
                intervals[interval_key]['wind_speed'].append(forecast_item['wind']['speed'])
            
            # Collect weather conditions
            if 'weather' in forecast_item and forecast_item['weather']:
                intervals[interval_key]['weather_items'].extend(forecast_item['weather'])
        
        # Calculate statistics for each interval
        summarized_intervals = []
        for interval_key, data in intervals.items():
            # Find most common weather condition
            weather_summary = OpenWeatherAPI.get_mode_weather(data['weather_items'])
            
            interval_summary = {
                'interval': interval_key,
                'start_time': data['start_time'],
                'end_time': data['end_time'],
                'temperature': {
                    'avg': round(statistics.mean(data['temperatures']), 1),
                    'min': round(min(data['temperatures']), 1),
                    'max': round(max(data['temperatures']), 1)
                },
                'feels_like': round(statistics.mean(data['feels_like']), 1),
                'humidity': round(statistics.mean(data['humidity'])),
                'pressure': round(statistics.mean(data['pressure'])),
                'weather': weather_summary
            }
            
            if data['wind_speed']:
                interval_summary['wind_speed'] = round(statistics.mean(data['wind_speed']), 1)
                
            summarized_intervals.append(interval_summary)
        
        # Sort intervals by start time
        summarized_intervals.sort(key=lambda x: x['start_time'])
        
        return {
            'city': city_info,
            'intervals': summarized_intervals,
            'interval_hours': interval_hours
        }

    @staticmethod
    def get_daily_forecast_condensed(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None, cnt: int = 7) -> Optional[Dict[str, Any]]:
        """Gets condensed daily weather forecast for a specified number of days.
        
        Args:
            city_name: Name of the city
            state_code: State code (optional) 
            country_code: Country code (optional)
            cnt: Number of days to forecast (default: 7)
            
        Returns:
            Condensed JSON with daily forecast summary
        """
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'cnt': cnt, 'units': 'metric'}
        data = OpenWeatherAPI.fetch_weather_data('forecast/daily', params)
        
        if not data or 'list' not in data:
            # Try using hourly forecast API to create daily aggregates if daily API fails
            return OpenWeatherAPI._create_daily_forecast_from_hourly(city_name, state_code, country_code, cnt)
            
        daily_forecast = []
        city_info = data.get('city', {})
        
        for forecast_item in data['list']:
            dt = datetime.fromtimestamp(forecast_item['dt'])
            date_str = dt.strftime("%Y-%m-%d")
            
            # Extract main weather condition
            weather_summary = {}
            if 'weather' in forecast_item and forecast_item['weather']:
                weather_id = forecast_item['weather'][0]['id']
                weather_summary = {
                    'id': weather_id,
                    'main': forecast_item['weather'][0]['main'],
                    'description': forecast_item['weather'][0]['description'],
                    'icon': forecast_item['weather'][0]['icon'],
                    'readable_description': WEATHER_CODE_MAP.get(weather_id, forecast_item['weather'][0]['description'])
                }
            
            # Create daily summary
            day_summary = {
                'date': date_str,
                'day_of_week': dt.strftime("%A"),
                'temperature': {
                    'day': round(forecast_item['temp']['day'], 1) if isinstance(forecast_item.get('temp'), dict) else None,
                    'min': round(forecast_item['temp']['min'], 1) if isinstance(forecast_item.get('temp'), dict) else None,
                    'max': round(forecast_item['temp']['max'], 1) if isinstance(forecast_item.get('temp'), dict) else None,
                    'night': round(forecast_item['temp']['night'], 1) if isinstance(forecast_item.get('temp'), dict) else None,
                },
                'feels_like': {
                    'day': round(forecast_item['feels_like']['day'], 1) if isinstance(forecast_item.get('feels_like'), dict) else None,
                    'night': round(forecast_item['feels_like']['night'], 1) if isinstance(forecast_item.get('feels_like'), dict) else None
                },
                'humidity': forecast_item.get('humidity'),
                'pressure': forecast_item.get('pressure'),
                'weather': weather_summary
            }
            
            if 'wind_speed' in forecast_item:
                day_summary['wind_speed'] = round(forecast_item['wind_speed'], 1)
                
            daily_forecast.append(day_summary)
        
        return {
            'city': city_info,
            'daily': daily_forecast
        }

    @staticmethod
    def _create_daily_forecast_from_hourly(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None, cnt: int = 7) -> Optional[Dict[str, Any]]:
        """Creates daily forecast by aggregating hourly forecast data when daily API is unavailable"""
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        params = {'lat': lat, 'lon': lon, 'units': 'metric'}
        data = OpenWeatherAPI.fetch_weather_data('forecast', params)
        
        if not data or 'list' not in data:
            return None
            
        # Group forecast data by day
        days = {}
        city_info = data.get('city', {})
        
        for forecast_item in data['list']:
            dt = datetime.fromtimestamp(forecast_item['dt'])
            day_key = dt.strftime("%Y-%m-%d")
            
            if day_key not in days:
                days[day_key] = {
                    'date': day_key,
                    'day_of_week': dt.strftime("%A"),
                    'temperatures': [],
                    'feels_like': [],
                    'humidity': [],
                    'pressure': [],
                    'wind_speed': [],
                    'weather_items': []
                }
            
            # Collect data for statistics
            days[day_key]['temperatures'].append(forecast_item['main']['temp'])
            days[day_key]['feels_like'].append(forecast_item['main']['feels_like'])
            days[day_key]['humidity'].append(forecast_item['main']['humidity'])
            days[day_key]['pressure'].append(forecast_item['main']['pressure'])
            if 'wind' in forecast_item and 'speed' in forecast_item['wind']:
                days[day_key]['wind_speed'].append(forecast_item['wind']['speed'])
            
            # Collect weather conditions
            if 'weather' in forecast_item and forecast_item['weather']:
                days[day_key]['weather_items'].extend(forecast_item['weather'])
        
        # Calculate statistics for each day
        daily_forecast = []
        for _, day_data in sorted(days.items())[:cnt]:  # Limit to requested number of days
            # Find most common weather condition
            weather_summary = OpenWeatherAPI.get_mode_weather(day_data['weather_items'])
            
            day_summary = {
                'date': day_data['date'],
                'day_of_week': day_data['day_of_week'],
                'temperature': {
                    'avg': round(statistics.mean(day_data['temperatures']), 1),
                    'min': round(min(day_data['temperatures']), 1),
                    'max': round(max(day_data['temperatures']), 1)
                },
                'feels_like': round(statistics.mean(day_data['feels_like']), 1),
                'humidity': round(statistics.mean(day_data['humidity'])),
                'pressure': round(statistics.mean(day_data['pressure'])),
                'weather': weather_summary
            }
            
            if day_data['wind_speed']:
                day_summary['wind_speed'] = round(statistics.mean(day_data['wind_speed']), 1)
                
            daily_forecast.append(day_summary)
        
        return {
            'city': city_info,
            'daily': daily_forecast
        }

    @staticmethod
    def get_historical_weather_condensed(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None, 
                                       start_date: str = None, end_date: str = None, 
                                       interval_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Gets condensed historical weather data for a specific date range.
        
        Args:
            city_name: Name of the city
            state_code: State code (optional)
            country_code: Country code (optional) 
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval_hours: Hours to group data by (default: 24 for daily)
            
        Returns:
            Condensed JSON with historical weather data or None if location not found
        """
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
        
        # Group data by intervals
        intervals = {}
        city_info = data.get('city', {})
        
        for item in data['list']:
            dt = datetime.fromtimestamp(item['dt'])
            
            if interval_hours == 24:  # Daily intervals
                interval_key = dt.strftime("%Y-%m-%d")
                interval_start = dt.replace(hour=0, minute=0, second=0)
            else:  # Custom hour intervals
                interval_start = dt.replace(hour=(dt.hour // interval_hours) * interval_hours, minute=0, second=0)
                interval_key = interval_start.strftime("%Y-%m-%d %H:%M")
            
            if interval_key not in intervals:
                intervals[interval_key] = {
                    'start_time': interval_start.isoformat(),
                    'end_time': (interval_start + timedelta(hours=interval_hours)).isoformat(),
                    'temperatures': [],
                    'humidity': [],
                    'pressure': [],
                    'wind_speed': [],
                    'weather_items': []
                }
            
            # Collect data for statistics
            if 'main' in item:
                if 'temp' in item['main']:
                    intervals[interval_key]['temperatures'].append(item['main']['temp'])
                if 'humidity' in item['main']:
                    intervals[interval_key]['humidity'].append(item['main']['humidity'])
                if 'pressure' in item['main']:
                    intervals[interval_key]['pressure'].append(item['main']['pressure'])
            
            if 'wind' in item and 'speed' in item['wind']:
                intervals[interval_key]['wind_speed'].append(item['wind']['speed'])
            
            # Collect weather conditions
            if 'weather' in item and item['weather']:
                intervals[interval_key]['weather_items'].extend(item['weather'])
        
        # Calculate statistics for each interval
        summarized_intervals = []
        for interval_key, interval_data in sorted(intervals.items()):
            # Find most common weather condition
            weather_summary = OpenWeatherAPI.get_mode_weather(interval_data['weather_items'])
            
            interval_summary = {
                'interval': interval_key,
                'start_time': interval_data['start_time'],
                'end_time': interval_data['end_time'],
                'weather': weather_summary
            }
            
            # Add temperature statistics if available
            if interval_data['temperatures']:
                interval_summary['temperature'] = {
                    'avg': round(statistics.mean(interval_data['temperatures']), 1),
                    'min': round(min(interval_data['temperatures']), 1),
                    'max': round(max(interval_data['temperatures']), 1)
                }
            
            # Add other statistics if available
            if interval_data['humidity']:
                interval_summary['humidity'] = round(statistics.mean(interval_data['humidity']))
            
            if interval_data['pressure']:
                interval_summary['pressure'] = round(statistics.mean(interval_data['pressure']))
            
            if interval_data['wind_speed']:
                interval_summary['wind_speed'] = round(statistics.mean(interval_data['wind_speed']), 1)
                
            summarized_intervals.append(interval_summary)
        
        return {
            'city': {'name': city_name, 'coord': {'lat': lat, 'lon': lon}},
            'intervals': summarized_intervals,
            'interval_hours': interval_hours,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }

    @staticmethod
    def get_air_pollution_condensed(city_name: str, state_code: Optional[str] = None, country_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Gets condensed air pollution data for a specified location.
        
        Returns:
            Condensed JSON with air pollution data or None if location not found
        """
        coords = OpenWeatherAPI.get_coordinates(city_name, state_code, country_code)
        if not coords:
            return None
        lat, lon = coords
        
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OpenWeatherAPI.API_KEY
        }
        
        response = requests.get(OpenWeatherAPI.AIR_POLLUTION_URL, params=params)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if 'list' not in data or not data['list']:
            return None
        
        # Get the most recent air pollution data
        pollution_info = data['list'][0]
        
        # AQI description mapper
        aqi_descriptions = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }
        
        # Create condensed output
        result = {
            'location': {
                'name': city_name,
                'coord': {'lat': lat, 'lon': lon}
            },
            'timestamp': datetime.fromtimestamp(pollution_info['dt']).isoformat(),
            'air_quality_index': pollution_info['main']['aqi'],
            'air_quality_level': aqi_descriptions.get(pollution_info['main']['aqi'], "Unknown"),
            'components': {}
        }
        
        # Add components with descriptions
        component_descriptions = {
            'co': 'Carbon monoxide',
            'no': 'Nitrogen monoxide',
            'no2': 'Nitrogen dioxide',
            'o3': 'Ozone',
            'so2': 'Sulphur dioxide',
            'pm2_5': 'Fine particles (PM2.5)',
            'pm10': 'Coarse particles (PM10)',
            'nh3': 'Ammonia'
        }
        
        for component, value in pollution_info['components'].items():
            result['components'][component] = {
                'value': value,
                'name': component_descriptions.get(component, component)
            }
        
        return result

    @staticmethod
    def get_tile_coordinates(lat: float, lng: float, zoom: int) -> Tuple[int, int]:
        """
        Calculates the tile x and y coordinates for a given latitude, longitude, and zoom level.

        Args:
            lat: The latitude of the location.
            lng: The longitude of the location.
            zoom: The zoom level.

        Returns:
            A tuple containing the tile x and y coordinates
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

        return tile_coordinate_x, tile_coordinate_y

    @staticmethod
    def get_weather_map_url(
        lat: float,
        lng: float,
        layer: str = "TA2",
        zoom: int = 4,
        date: int = None,
        opacity: float = 0.8,
        palette: str = None,
        fill_bound: bool = False,
        arrow_step: int = None,
        use_norm: bool = False
    ) -> Dict[str, Any]:
        """
        Get weather map tile URL from OpenWeather Maps 2.0 API.

        Parameters:
            lat (float): Latitude
            lng (float): Longitude
            layer (str): Weather map layer (e.g., 'TA2', 'PA0', 'WND', etc.)
            zoom (int): Zoom level
            date (int, optional): Unix timestamp (UTC) for current, forecast, or historical
            opacity (float, optional): Opacity of the layer (0 to 1)
            palette (str, optional): Custom palette string in format value:HEX;value:HEX
            fill_bound (bool, optional): Whether to fill values outside specified set
            arrow_step (int, optional): Step in pixels for wind arrows (only for 'WND' layer)
            use_norm (bool, optional): Whether to normalize wind arrows (only for 'WND' layer)

        Returns:
            Dict with map URL information
        """
        # Get tile coordinates from lat/lng
        x, y = OpenWeatherAPI.get_tile_coordinates(lat=lat, lng=lng, zoom=zoom)
        
        base_url = f"http://maps.openweathermap.org/maps/2.0/weather/{layer}/{zoom}/{x}/{y}"
        
        params = {
            "appid": OpenWeatherAPI.API_KEY,
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
        full_url = f"{base_url}?{query}"
        
        # Return map info as a JSON object
        return {
            "url": full_url,
            "layer": layer,
            "coordinates": {
                "lat": lat,
                "lng": lng,
                "tile_x": x,
                "tile_y": y,
                "zoom": zoom
            },
            "parameters": params
        }

# Example usage:
if __name__ == "__main__":
    # Get current weather
    weather = OpenWeatherAPI.get_current_weather("Nagpur", "MH", "IN")
    print("Current weather:", weather)
    
    # Get condensed hourly forecast
    forecast = OpenWeatherAPI.get_hourly_forecast_condensed("Nagpur", "MH", "IN", interval_hours=6)
    print("Condensed hourly forecast:", forecast)
    
    # Get condensed daily forecast
    daily_forecast = OpenWeatherAPI.get_daily_forecast_condensed("Nagpur", "MH", "IN", cnt=7)
    print("Condensed daily forecast:", daily_forecast)
    
    # Get condensed historical weather (daily intervals)
    historical_weather = OpenWeatherAPI.get_historical_weather_condensed(
        "Nagpur", "MH", "IN", 
        start_date="2025-03-01", 
        end_date="2025-03-31",
        interval_hours=24  # Daily intervals
    )
    print("Condensed historical weather:", historical_weather)
    
    # Get condensed air pollution data
    air_pollution = OpenWeatherAPI.get_air_pollution_condensed("Nagpur", "MH", "IN")
    print("Condensed air pollution data:", air_pollution)