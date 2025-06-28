"""
Air Quality Forecast Service
Handles fetching and caching air quality forecast data from external APIs
"""

import requests
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Set up logging
logger = logging.getLogger(__name__)

class ForecastService:
    """Service for managing air quality forecast data"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.get('database.path', 'monitoring.db')
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize forecast database tables"""
        with self._get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS forecast_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forecast_time TEXT NOT NULL,
                    forecast_for_time TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    pm1_0 REAL,
                    pm2_5 REAL,
                    pm10 REAL,
                    carbon_monoxide REAL,
                    nitrogen_dioxide REAL,
                    sulphur_dioxide REAL,
                    ozone REAL,
                    aqi INTEGER,
                    aqi_level TEXT,
                    raw_data TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_forecast_time 
                ON forecast_readings(forecast_for_time)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_forecast_provider 
                ON forecast_readings(provider, forecast_time)
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_forecast(self, hours: int = 72) -> List[Dict]:
        """
        Get air quality forecast data
        
        Args:
            hours: Number of hours to forecast (default 72 = 3 days)
            
        Returns:
            List of forecast data points
        """
        if not config.is_forecast_enabled():
            logger.info("Forecast functionality is disabled")
            return []
        
        # Check cache first
        cached_data = self._get_cached_forecast(hours)
        if cached_data:
            logger.info(f"Using cached forecast data ({len(cached_data)} points)")
            return cached_data
        
        # Fetch fresh data
        provider = config.get_forecast_provider()
        if provider == 'open-meteo':
            forecast_data = self._fetch_open_meteo_forecast(hours)
        elif provider == 'epa-airnow':
            forecast_data = self._fetch_epa_airnow_forecast(hours)
        else:
            logger.error(f"Unknown forecast provider: {provider}")
            return []
        
        if forecast_data:
            self._cache_forecast_data(forecast_data, provider)
            logger.info(f"Fetched and cached {len(forecast_data)} forecast points")
        
        return forecast_data
    
    def _get_cached_forecast(self, hours: int) -> Optional[List[Dict]]:
        """Get cached forecast data if still valid"""
        cache_hours = config.get_cache_hours()
        cutoff_time = datetime.utcnow() - timedelta(hours=cache_hours)
        cutoff_str = cutoff_time.isoformat()
        
        # Only get future forecast data
        now = datetime.utcnow()
        now_str = now.isoformat()
        
        end_time = now + timedelta(hours=hours)
        end_str = end_time.isoformat()
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM forecast_readings 
                    WHERE forecast_time > ? 
                    AND forecast_for_time >= ?
                    AND forecast_for_time <= ?
                    ORDER BY forecast_for_time
                ''', (cutoff_str, now_str, end_str))
                
                rows = cursor.fetchall()
                if not rows:
                    return None
                
                return [self._row_to_dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching cached forecast: {e}")
            return None
    
    def _fetch_open_meteo_forecast(self, hours: int) -> List[Dict]:
        """Fetch forecast data from Open-Meteo API"""
        lat, lon = config.get_coordinates()
        days = min((hours + 23) // 24, config.get_forecast_days())  # Round up to days
        
        url = config.get('apis.open_meteo.base_url')
        params = {
            'latitude': lat,
            'longitude': lon,
            'hourly': 'pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone',
            'forecast_days': days,
            'timezone': 'UTC'
        }
        
        try:
            logger.info(f"Fetching Open-Meteo forecast for {lat}, {lon}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_open_meteo_response(data)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Open-Meteo data: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Open-Meteo response: {e}")
            return []
    
    def _parse_open_meteo_response(self, data: Dict) -> List[Dict]:
        """Parse Open-Meteo API response into standardized format"""
        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        
        if not times:
            logger.warning("No hourly data in Open-Meteo response")
            return []
        
        forecast_points = []
        forecast_time = datetime.utcnow().isoformat()
        now = datetime.utcnow()
        
        for i, time_str in enumerate(times):
            try:
                # Parse forecast time and skip if it's in the past
                forecast_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if forecast_dt <= now:
                    continue
                
                # Get pollutant values (None if missing)
                pm25 = hourly.get('pm2_5', [None] * len(times))[i]
                pm10 = hourly.get('pm10', [None] * len(times))[i]
                co = hourly.get('carbon_monoxide', [None] * len(times))[i]
                no2 = hourly.get('nitrogen_dioxide', [None] * len(times))[i]
                so2 = hourly.get('sulphur_dioxide', [None] * len(times))[i]
                o3 = hourly.get('ozone', [None] * len(times))[i]
                
                # Calculate AQI from PM2.5
                aqi, aqi_level = self._calculate_aqi_from_pm25(pm25)
                
                forecast_point = {
                    'forecast_time': forecast_time,
                    'forecast_for_time': time_str,
                    'provider': 'open-meteo',
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'pm1_0': None,  # Open-Meteo doesn't provide PM1.0
                    'pm2_5': pm25,
                    'pm10': pm10,
                    'carbon_monoxide': co,
                    'nitrogen_dioxide': no2,
                    'sulphur_dioxide': so2,
                    'ozone': o3,
                    'aqi': aqi,
                    'aqi_level': aqi_level,
                    'raw_data': json.dumps({
                        'pm2_5': pm25,
                        'pm10': pm10,
                        'co': co,
                        'no2': no2,
                        'so2': so2,
                        'o3': o3
                    })
                }
                
                forecast_points.append(forecast_point)
                
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing forecast point {i}: {e}")
                continue
        
        return forecast_points
    
    def _fetch_epa_airnow_forecast(self, hours: int) -> List[Dict]:
        """Fetch forecast data from EPA AirNow API"""
        api_key = config.get('apis.epa_airnow.api_key')
        if not api_key:
            logger.error("EPA AirNow API key not configured")
            return []
        
        lat, lon = config.get_coordinates()
        url = config.get('apis.epa_airnow.base_url')
        
        # EPA AirNow provides daily forecasts, not hourly
        days = min((hours + 23) // 24, 5)  # Max 5 days
        forecast_points = []
        
        for day_offset in range(days):
            forecast_date = datetime.utcnow() + timedelta(days=day_offset)
            date_str = forecast_date.strftime('%Y-%m-%d')
            
            params = {
                'format': 'application/json',
                'latitude': lat,
                'longitude': lon,
                'date': date_str,
                'distance': 25,
                'API_KEY': api_key
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if data:
                    parsed = self._parse_epa_airnow_response(data, forecast_date)
                    forecast_points.extend(parsed)
                    
            except requests.RequestException as e:
                logger.error(f"Error fetching EPA AirNow data for {date_str}: {e}")
                continue
        
        return forecast_points
    
    def _parse_epa_airnow_response(self, data: List[Dict], forecast_date: datetime) -> List[Dict]:
        """Parse EPA AirNow API response"""
        forecast_points = []
        forecast_time = datetime.utcnow().isoformat()
        
        for item in data:
            try:
                forecast_point = {
                    'forecast_time': forecast_time,
                    'forecast_for_time': forecast_date.isoformat(),
                    'provider': 'epa-airnow',
                    'latitude': item.get('Latitude'),
                    'longitude': item.get('Longitude'),
                    'pm1_0': None,
                    'pm2_5': None,
                    'pm10': None,
                    'carbon_monoxide': None,
                    'nitrogen_dioxide': None,
                    'sulphur_dioxide': None,
                    'ozone': None,
                    'aqi': item.get('AQI'),
                    'aqi_level': item.get('Category', {}).get('Name'),
                    'raw_data': json.dumps(item)
                }
                
                # Map parameter-specific data
                param_name = item.get('ParameterName', '').lower()
                if 'pm2.5' in param_name:
                    forecast_point['pm2_5'] = self._aqi_to_pm25(item.get('AQI'))
                elif 'pm10' in param_name:
                    forecast_point['pm10'] = self._aqi_to_pm10(item.get('AQI'))
                elif 'ozone' in param_name or 'o3' in param_name:
                    forecast_point['ozone'] = item.get('AQI')
                
                forecast_points.append(forecast_point)
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing EPA AirNow item: {e}")
                continue
        
        return forecast_points
    
    def _calculate_aqi_from_pm25(self, pm25_value: Optional[float]) -> Tuple[Optional[int], Optional[str]]:
        """Calculate AQI from PM2.5 concentration using EPA 2024 standards"""
        if pm25_value is None:
            return None, None
        
        # EPA 2024 PM2.5 AQI breakpoints
        breakpoints = [
            (0.0, 9.0, 0, 50, "Good"),
            (9.1, 35.4, 51, 100, "Moderate"),
            (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
            (55.5, 150.4, 151, 200, "Unhealthy"),
            (150.5, 250.4, 201, 300, "Very Unhealthy"),
            (250.5, 350.4, 301, 400, "Hazardous"),
            (350.5, 500.4, 401, 500, "Hazardous")
        ]
        
        for c_low, c_high, i_low, i_high, category in breakpoints:
            if c_low <= pm25_value <= c_high:
                aqi = ((i_high - i_low) / (c_high - c_low)) * (pm25_value - c_low) + i_low
                return round(aqi), category
        
        return 500, "Hazardous"
    
    def _aqi_to_pm25(self, aqi: Optional[int]) -> Optional[float]:
        """Convert AQI back to PM2.5 concentration (approximate)"""
        if aqi is None:
            return None
        
        breakpoints = [
            (0, 50, 0.0, 9.0),
            (51, 100, 9.1, 35.4),
            (101, 150, 35.5, 55.4),
            (151, 200, 55.5, 150.4),
            (201, 300, 150.5, 250.4),
            (301, 400, 250.5, 350.4),
            (401, 500, 350.5, 500.4)
        ]
        
        for i_low, i_high, c_low, c_high in breakpoints:
            if i_low <= aqi <= i_high:
                pm25 = ((c_high - c_low) / (i_high - i_low)) * (aqi - i_low) + c_low
                return round(pm25, 1)
        
        return 500.0
    
    def _aqi_to_pm10(self, aqi: Optional[int]) -> Optional[float]:
        """Convert AQI back to PM10 concentration (approximate)"""
        if aqi is None:
            return None
        
        # PM10 has different breakpoints than PM2.5
        breakpoints = [
            (0, 50, 0, 54),
            (51, 100, 55, 154),
            (101, 150, 155, 254),
            (151, 200, 255, 354),
            (201, 300, 355, 424),
            (301, 400, 425, 504),
            (401, 500, 505, 604)
        ]
        
        for i_low, i_high, c_low, c_high in breakpoints:
            if i_low <= aqi <= i_high:
                pm10 = ((c_high - c_low) / (i_high - i_low)) * (aqi - i_low) + c_low
                return round(pm10, 1)
        
        return 600.0
    
    def _cache_forecast_data(self, forecast_data: List[Dict], provider: str):
        """Store forecast data in database cache"""
        if not forecast_data:
            return
        
        try:
            with self._get_db_connection() as conn:
                # Clear old cache for this provider
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                conn.execute('''
                    DELETE FROM forecast_readings 
                    WHERE provider = ? AND forecast_time < ?
                ''', (provider, cutoff_time.isoformat()))
                
                # Insert new data
                for point in forecast_data:
                    conn.execute('''
                        INSERT INTO forecast_readings (
                            forecast_time, forecast_for_time, provider,
                            latitude, longitude, pm1_0, pm2_5, pm10,
                            carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone,
                            aqi, aqi_level, raw_data, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        point['forecast_time'], point['forecast_for_time'], point['provider'],
                        point['latitude'], point['longitude'], point['pm1_0'], 
                        point['pm2_5'], point['pm10'], point['carbon_monoxide'],
                        point['nitrogen_dioxide'], point['sulphur_dioxide'], point['ozone'],
                        point['aqi'], point['aqi_level'], point['raw_data'],
                        datetime.utcnow().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"Cached {len(forecast_data)} forecast points")
                
        except sqlite3.Error as e:
            logger.error(f"Error caching forecast data: {e}")
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert database row to dictionary"""
        return {
            'forecast_time': row['forecast_time'],
            'forecast_for_time': row['forecast_for_time'],
            'provider': row['provider'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'pm1_0': row['pm1_0'],
            'pm2_5': row['pm2_5'],
            'pm10': row['pm10'],
            'carbon_monoxide': row['carbon_monoxide'],
            'nitrogen_dioxide': row['nitrogen_dioxide'],
            'sulphur_dioxide': row['sulphur_dioxide'],
            'ozone': row['ozone'],
            'aqi': row['aqi'],
            'aqi_level': row['aqi_level'],
            'created_at': row['created_at']
        }
    
    def clear_cache(self):
        """Clear all cached forecast data"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('DELETE FROM forecast_readings')
                conn.commit()
                logger.info("Forecast cache cleared")
        except sqlite3.Error as e:
            logger.error(f"Error clearing forecast cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about cached forecast data"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        provider,
                        COUNT(*) as count,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM forecast_readings 
                    GROUP BY provider
                ''')
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row['provider']] = {
                        'count': row['count'],
                        'oldest': row['oldest'],
                        'newest': row['newest']
                    }
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

# Global service instance
forecast_service = ForecastService()