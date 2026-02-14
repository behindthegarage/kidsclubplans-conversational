"""
Weather API client with caching for KidsClubPlans.
Integrates with OpenWeatherMap API.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import lru_cache

import requests

from .models import WeatherData

logger = logging.getLogger("kcp.weather")

# Default location (Lansing, MI)
DEFAULT_LOCATION = "Lansing, MI"
DEFAULT_LAT = 42.7325
DEFAULT_LON = -84.5555

# Cache duration in minutes
CACHE_DURATION_MINUTES = 30


class WeatherCache:
    """SQLite-based cache for weather data."""
    
    def __init__(self, db_path: str = "./memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize weather cache table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    location TEXT NOT NULL,
                    date TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at TEXT NOT NULL,
                    PRIMARY KEY (location, date)
                )
            """)
            conn.commit()
    
    def get(self, location: str, date: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data, cached_at FROM weather_cache WHERE location = ? AND date = ?",
                (location, date)
            ).fetchone()
            
            if row:
                data = json.loads(row[0])
                cached_at = datetime.fromisoformat(row[1])
                
                # Check if cache is still valid
                if datetime.now() - cached_at < timedelta(minutes=CACHE_DURATION_MINUTES):
                    logger.info(f"Weather cache hit for {location} on {date}")
                    return data
                else:
                    logger.info(f"Weather cache expired for {location} on {date}")
        return None
    
    def set(self, location: str, date: str, data: Dict[str, Any]):
        """Cache weather data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO weather_cache (location, date, data, cached_at)
                   VALUES (?, ?, ?, ?)""",
                (location, date, json.dumps(data), datetime.now().isoformat())
            )
            conn.commit()
            logger.info(f"Weather cached for {location} on {date}")
    
    def clear_old_cache(self, days: int = 7):
        """Clear cache entries older than specified days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM weather_cache WHERE cached_at < ?", (cutoff,))
            conn.commit()


class WeatherClient:
    """OpenWeatherMap API client."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        self.cache = WeatherCache()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        if not self.api_key:
            logger.warning("No OpenWeather API key configured. Using mock data.")
    
    def _geocode_location(self, location: str) -> tuple[float, float]:
        """Convert location string to lat/lon coordinates."""
        # Simple geocoding for common locations
        location_lower = location.lower()
        
        # Default to Lansing, MI
        lat, lon = DEFAULT_LAT, DEFAULT_LON
        
        if "lansing" in location_lower:
            lat, lon = 42.7325, -84.5555
        elif "detroit" in location_lower:
            lat, lon = 42.3314, -83.0458
        elif "grand rapids" in location_lower:
            lat, lon = 42.9634, -85.6681
        elif "ann arbor" in location_lower:
            lat, lon = 42.2808, -83.7430
        elif "east lansing" in location_lower:
            lat, lon = 42.7360, -84.4839
        elif "okemos" in location_lower:
            lat, lon = 42.7223, -84.4275
        elif "michigan" in location_lower:
            # Default to Lansing for "Michigan"
            lat, lon = DEFAULT_LAT, DEFAULT_LON
        
        return lat, lon
    
    def _determine_outdoor_suitability(self, weather_data: Dict) -> bool:
        """Determine if outdoor activities are suitable based on weather."""
        condition = weather_data.get("weather", [{}])[0].get("main", "").lower()
        temp = weather_data.get("main", {}).get("temp", 70)
        wind_speed = weather_data.get("wind", {}).get("speed", 0)
        
        # Not suitable if:
        # - Rain, snow, thunderstorm
        # - Extreme temperatures (below 20F or above 95F)
        # - High winds (above 25 mph)
        
        bad_conditions = ["rain", "snow", "thunderstorm", "drizzle"]
        if any(bc in condition for bc in bad_conditions):
            return False
        
        if temp < 20 or temp > 95:
            return False
        
        if wind_speed > 25:
            return False
        
        return True
    
    def _map_condition(self, condition: str) -> str:
        """Map OpenWeather condition to simplified condition."""
        condition_lower = condition.lower()
        
        if "rain" in condition_lower or "drizzle" in condition_lower:
            return "rain"
        elif "snow" in condition_lower:
            return "snow"
        elif "thunder" in condition_lower or "storm" in condition_lower:
            return "storm"
        elif "cloud" in condition_lower:
            return "cloudy"
        elif "clear" in condition_lower or "sun" in condition_lower:
            return "sunny"
        elif "fog" in condition_lower or "mist" in condition_lower:
            return "foggy"
        else:
            return "cloudy"
    
    def _fetch_from_api(self, lat: float, lon: float, date: str) -> Optional[Dict[str, Any]]:
        """Fetch weather data from OpenWeather API."""
        if not self.api_key:
            return None
        
        try:
            # Check if date is today or future
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.now().date()
            days_diff = (target_date - today).days
            
            if days_diff < 0:
                # Past date - return historical-like data (use current as approximation)
                logger.warning(f"Requested past date {date}, using current weather as approximation")
                days_diff = 0
            
            if days_diff == 0:
                # Current weather
                url = f"{self.base_url}/weather"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial"
                }
            else:
                # Forecast (5 day forecast API)
                if days_diff > 5:
                    logger.warning(f"Forecast only available for 5 days, using day 5")
                    days_diff = 5
                
                url = f"{self.base_url}/forecast"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial"
                }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if days_diff > 0 and "list" in data:
                # Find forecast closest to target date
                # Each item is 3 hours, so we need to find the right slice
                target_index = min(days_diff * 8, len(data["list"]) - 1)  # 8 items per day
                data = data["list"][target_index]
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching weather: {e}")
            return None
    
    def _create_mock_weather(self, location: str, date: str) -> Dict[str, Any]:
        """Create mock weather data when API is unavailable."""
        logger.info(f"Using mock weather data for {location} on {date}")
        
        # Generate somewhat realistic mock data based on date
        target_date = datetime.strptime(date, "%Y-%m-%d")
        day_of_year = target_date.timetuple().tm_yday
        
        # Michigan seasons (rough approximation)
        # Winter: Dec-Mar, Spring: Apr-May, Summer: Jun-Aug, Fall: Sep-Nov
        if day_of_year < 80 or day_of_year > 330:  # Winter
            temp = 25 + (day_of_year % 15)
            condition = "snow" if day_of_year % 5 == 0 else "cloudy"
        elif day_of_year < 170:  # Spring
            temp = 55 + (day_of_year % 20)
            condition = "rain" if day_of_year % 4 == 0 else "cloudy"
        elif day_of_year < 260:  # Summer
            temp = 75 + (day_of_year % 20)
            condition = "sunny" if day_of_year % 3 != 0 else "cloudy"
        else:  # Fall
            temp = 60 + (day_of_year % 15)
            condition = "cloudy"
        
        return {
            "main": {
                "temp": temp,
                "humidity": 50 + (day_of_year % 30)
            },
            "weather": [{"main": condition, "description": condition}],
            "wind": {"speed": 5 + (day_of_year % 10)},
            "clouds": {"all": 30 + (day_of_year % 40)}
        }
    
    def check_weather(self, location: str = DEFAULT_LOCATION, date: Optional[str] = None) -> WeatherData:
        """
        Check weather for a location and date.
        
        Args:
            location: Location string (e.g., "Lansing, MI")
            date: Date in YYYY-MM-DD format (default: today)
        
        Returns:
            WeatherData object with weather information
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Normalize location
        location = location.strip() or DEFAULT_LOCATION
        
        # Check cache first
        cached = self.cache.get(location, date)
        if cached:
            return WeatherData(**cached)
        
        # Get coordinates
        lat, lon = self._geocode_location(location)
        
        # Try to fetch from API
        weather_data = self._fetch_from_api(lat, lon, date)
        
        if weather_data is None:
            # Use mock data
            weather_data = self._create_mock_weather(location, date)
        
        # Parse the weather data
        main = weather_data.get("main", {})
        weather_list = weather_data.get("weather", [{}])
        wind = weather_data.get("wind", {})
        
        condition = weather_list[0].get("main", "Unknown")
        description = weather_list[0].get("description", "")
        
        # Calculate precipitation chance if available
        precip_chance = None
        if "pop" in weather_data:
            precip_chance = int(weather_data["pop"] * 100)
        elif "rain" in condition.lower():
            precip_chance = 80
        elif "snow" in condition.lower():
            precip_chance = 70
        else:
            precip_chance = 10
        
        temp_f = main.get("temp")
        temp_c = (temp_f - 32) * 5 / 9 if temp_f is not None else None
        
        result = WeatherData(
            location=location,
            date=date,
            temperature_f=temp_f,
            temperature_c=round(temp_c, 1) if temp_c else None,
            conditions=self._map_condition(condition),
            description=description,
            precipitation_chance=precip_chance,
            humidity=main.get("humidity"),
            wind_speed=wind.get("speed"),
            outdoor_suitable=self._determine_outdoor_suitability(weather_data),
            uv_index=weather_data.get("uvi"),
            cached_at=datetime.now().isoformat()
        )
        
        # Cache the result
        self.cache.set(location, date, result.model_dump())
        
        return result


# Global weather client instance
_weather_client: Optional[WeatherClient] = None


def get_weather_client() -> WeatherClient:
    """Get or create the global weather client."""
    global _weather_client
    if _weather_client is None:
        _weather_client = WeatherClient()
    return _weather_client


def check_weather(location: str = DEFAULT_LOCATION, date: Optional[str] = None) -> WeatherData:
    """
    Convenience function to check weather.
    
    Args:
        location: Location string (e.g., "Lansing, MI")
        date: Date in YYYY-MM-DD format (default: today)
    
    Returns:
        WeatherData object
    """
    client = get_weather_client()
    return client.check_weather(location, date)


# Cache maintenance
if __name__ == "__main__":
    # Clear old cache entries when run directly
    cache = WeatherCache()
    cache.clear_old_cache()
    print("Weather cache cleaned up")
