"""
Tests for forecast service functionality
"""

import pytest
import sqlite3
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.forecast_service import ForecastService


class TestForecastService:
    """Test cases for ForecastService"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def service(self, temp_db):
        """Create ForecastService instance with temporary database"""
        return ForecastService(db_path=temp_db)
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        with patch('services.forecast_service.config') as mock_config:
            mock_config.is_forecast_enabled.return_value = True
            mock_config.get_forecast_provider.return_value = 'open-meteo'
            mock_config.get_cache_hours.return_value = 1
            mock_config.get_forecast_days.return_value = 3
            mock_config.get_coordinates.return_value = (37.6138, -122.4869)
            mock_config.get.return_value = 'https://air-quality-api.open-meteo.com/v1/air-quality'
            yield mock_config
    
    def test_database_initialization(self, service):
        """Test that database tables are created correctly"""
        with service._get_db_connection() as conn:
            # Check that forecast_readings table exists
            cursor = conn.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='forecast_readings'
            ''')
            assert cursor.fetchone() is not None
            
            # Check table schema
            cursor = conn.execute('PRAGMA table_info(forecast_readings)')
            columns = [row[1] for row in cursor.fetchall()]
            
            expected_columns = [
                'id', 'forecast_time', 'forecast_for_time', 'provider',
                'latitude', 'longitude', 'pm1_0', 'pm2_5', 'pm10',
                'carbon_monoxide', 'nitrogen_dioxide', 'sulphur_dioxide', 
                'ozone', 'aqi', 'aqi_level', 'raw_data', 'created_at'
            ]
            
            for col in expected_columns:
                assert col in columns
    
    def test_calculate_aqi_from_pm25(self, service):
        """Test AQI calculation from PM2.5 values"""
        test_cases = [
            (5.0, 28, "Good"),
            (9.0, 50, "Good"),
            (12.0, 56, "Moderate"),
            (35.4, 100, "Moderate"),
            (45.0, 124, "Unhealthy for Sensitive Groups"),
            (75.0, 161, "Unhealthy"),
            (200.0, 250, "Very Unhealthy"),
            (350.0, 399, "Hazardous"),
            (None, None, None)
        ]
        
        for pm25, expected_aqi, expected_level in test_cases:
            aqi, level = service._calculate_aqi_from_pm25(pm25)
            if pm25 is None:
                assert aqi is None and level is None
            else:
                assert abs(aqi - expected_aqi) <= 1  # Allow 1 point tolerance
                assert level == expected_level
    
    def test_aqi_to_pm25_conversion(self, service):
        """Test conversion from AQI back to PM2.5"""
        test_cases = [
            (25, 4.5),
            (50, 9.0),
            (75, 22.3),
            (100, 35.4),
            (150, 55.4),
            (200, 150.4),
            (None, None)
        ]
        
        for aqi, expected_pm25 in test_cases:
            pm25 = service._aqi_to_pm25(aqi)
            if aqi is None:
                assert pm25 is None
            else:
                assert abs(pm25 - expected_pm25) <= 1.0  # Allow 1.0 tolerance
    
    def test_parse_open_meteo_response(self, service):
        """Test parsing of Open-Meteo API response"""
        mock_response = {
            'latitude': 37.6,
            'longitude': -122.5,
            'hourly': {
                'time': [
                    '2025-07-01T00:00',
                    '2025-07-01T01:00',
                    '2025-07-01T02:00'
                ],
                'pm2_5': [10.1, 12.3, 15.4],
                'pm10': [13.7, 16.2, 19.8],
                'carbon_monoxide': [0.2, 0.3, 0.4],
                'nitrogen_dioxide': [15.0, 18.0, 22.0],
                'sulphur_dioxide': [2.0, 2.5, 3.0],
                'ozone': [45.0, 50.0, 55.0]
            }
        }
        
        forecast_points = service._parse_open_meteo_response(mock_response)
        
        assert len(forecast_points) == 3
        
        # Check first point
        point = forecast_points[0]
        assert point['forecast_for_time'] == '2025-07-01T00:00'
        assert point['provider'] == 'open-meteo'
        assert point['latitude'] == 37.6
        assert point['longitude'] == -122.5
        assert point['pm2_5'] == 10.1
        assert point['pm10'] == 13.7
        assert point['carbon_monoxide'] == 0.2
        assert point['nitrogen_dioxide'] == 15.0
        assert point['sulphur_dioxide'] == 2.0
        assert point['ozone'] == 45.0
        assert point['aqi'] == 53  # Should be Moderate for PM2.5 = 10.1
        assert point['aqi_level'] == 'Moderate'
        assert point['pm1_0'] is None  # Open-Meteo doesn't provide PM1.0
        
        # Verify raw_data is valid JSON
        raw_data = json.loads(point['raw_data'])
        assert raw_data['pm2_5'] == 10.1
        assert raw_data['pm10'] == 13.7
    
    def test_cache_forecast_data(self, service):
        """Test caching of forecast data"""
        forecast_data = [
            {
                'forecast_time': '2025-07-01T12:00:00',
                'forecast_for_time': '2025-07-01T15:00:00',
                'provider': 'open-meteo',
                'latitude': 37.6138,
                'longitude': -122.4869,
                'pm1_0': None,
                'pm2_5': 10.5,
                'pm10': 14.2,
                'carbon_monoxide': 0.25,
                'nitrogen_dioxide': 16.0,
                'sulphur_dioxide': 2.1,
                'ozone': 48.0,
                'aqi': 55,
                'aqi_level': 'Moderate',
                'raw_data': '{"pm2_5": 10.5, "pm10": 14.2}'
            }
        ]
        
        service._cache_forecast_data(forecast_data, 'open-meteo')
        
        # Verify data was cached
        with service._get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM forecast_readings WHERE provider = ?
            ''', ('open-meteo',))
            
            rows = cursor.fetchall()
            assert len(rows) == 1
            
            row = rows[0]
            assert row['forecast_for_time'] == '2025-07-01T15:00:00'
            assert row['provider'] == 'open-meteo'
            assert row['pm2_5'] == 10.5
            assert row['aqi'] == 55
            assert row['aqi_level'] == 'Moderate'
    
    def test_get_cached_forecast(self, service):
        """Test retrieval of cached forecast data"""
        # Insert test data
        forecast_time = datetime.utcnow().isoformat()
        future_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        
        with service._get_db_connection() as conn:
            conn.execute('''
                INSERT INTO forecast_readings (
                    forecast_time, forecast_for_time, provider,
                    latitude, longitude, pm2_5, aqi, aqi_level,
                    raw_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                forecast_time, future_time, 'open-meteo',
                37.6138, -122.4869, 12.0, 56, 'Moderate',
                '{"pm2_5": 12.0}', datetime.utcnow().isoformat()
            ))
            conn.commit()
        
        # Test retrieval
        cached_data = service._get_cached_forecast(24)
        
        assert len(cached_data) == 1
        assert cached_data[0]['forecast_for_time'] == future_time
        assert cached_data[0]['provider'] == 'open-meteo'
        assert cached_data[0]['pm2_5'] == 12.0
        assert cached_data[0]['aqi'] == 56
    
    @patch('services.forecast_service.requests.get')
    def test_fetch_open_meteo_forecast_success(self, mock_get, service, mock_config):
        """Test successful Open-Meteo API fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'latitude': 37.6,
            'longitude': -122.5,
            'hourly': {
                'time': ['2025-07-01T00:00', '2025-07-01T01:00'],
                'pm2_5': [10.1, 11.2],
                'pm10': [13.7, 15.1]
            }
        }
        mock_get.return_value = mock_response
        
        forecast_data = service._fetch_open_meteo_forecast(24)
        
        assert len(forecast_data) == 2
        assert forecast_data[0]['pm2_5'] == 10.1
        assert forecast_data[1]['pm2_5'] == 11.2
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['latitude'] == 37.6138
        assert call_args[1]['params']['longitude'] == -122.4869
    
    @patch('services.forecast_service.requests.get')
    def test_fetch_open_meteo_forecast_error(self, mock_get, service, mock_config):
        """Test Open-Meteo API fetch with network error"""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Network error")
        
        forecast_data = service._fetch_open_meteo_forecast(24)
        
        assert forecast_data == []
    
    def test_get_forecast_disabled(self, service):
        """Test forecast when functionality is disabled"""
        with patch('services.forecast_service.config') as mock_config:
            mock_config.is_forecast_enabled.return_value = False
            
            forecast_data = service.get_forecast()
            
            assert forecast_data == []
    
    @patch('services.forecast_service.requests.get')
    def test_get_forecast_with_caching(self, mock_get, service, mock_config):
        """Test forecast retrieval with caching behavior"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'latitude': 37.6,
            'longitude': -122.5,
            'hourly': {
                'time': ['2025-07-01T00:00'],
                'pm2_5': [10.1],
                'pm10': [13.7]
            }
        }
        mock_get.return_value = mock_response
        
        # First call should fetch from API
        forecast_data1 = service.get_forecast(24)
        assert len(forecast_data1) == 1
        assert mock_get.call_count == 1
        
        # Second call should use cache (within cache window)
        mock_config.get_cache_hours.return_value = 2  # 2 hour cache
        forecast_data2 = service.get_forecast(24)
        assert len(forecast_data2) == 1
        assert mock_get.call_count == 1  # No additional API call
    
    def test_clear_cache(self, service):
        """Test cache clearing functionality"""
        # Add some test data
        service._cache_forecast_data([{
            'forecast_time': '2025-07-01T12:00:00',
            'forecast_for_time': '2025-07-01T15:00:00',
            'provider': 'open-meteo',
            'latitude': 37.6138,
            'longitude': -122.4869,
            'pm1_0': None,
            'pm2_5': 10.5,
            'pm10': 14.2,
            'carbon_monoxide': 0.25,
            'nitrogen_dioxide': 16.0,
            'sulphur_dioxide': 2.1,
            'ozone': 48.0,
            'aqi': 55,
            'aqi_level': 'Moderate',
            'raw_data': '{"pm2_5": 10.5}'
        }], 'open-meteo')
        
        # Verify data exists
        with service._get_db_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM forecast_readings')
            assert cursor.fetchone()[0] == 1
        
        # Clear cache
        service.clear_cache()
        
        # Verify data is gone
        with service._get_db_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM forecast_readings')
            assert cursor.fetchone()[0] == 0
    
    def test_get_cache_stats(self, service):
        """Test cache statistics functionality"""
        # Add test data
        forecast_time = datetime.utcnow().isoformat()
        
        with service._get_db_connection() as conn:
            conn.execute('''
                INSERT INTO forecast_readings (
                    forecast_time, forecast_for_time, provider,
                    latitude, longitude, pm2_5, aqi, aqi_level,
                    raw_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                forecast_time, forecast_time, 'open-meteo',
                37.6138, -122.4869, 12.0, 56, 'Moderate',
                '{"pm2_5": 12.0}', forecast_time
            ))
            conn.commit()
        
        stats = service.get_cache_stats()
        
        assert 'open-meteo' in stats
        assert stats['open-meteo']['count'] == 1
        assert stats['open-meteo']['oldest'] == forecast_time
        assert stats['open-meteo']['newest'] == forecast_time
    
    def test_row_to_dict(self, service):
        """Test database row to dictionary conversion"""
        # Insert test data
        forecast_time = datetime.utcnow().isoformat()
        
        with service._get_db_connection() as conn:
            conn.execute('''
                INSERT INTO forecast_readings (
                    forecast_time, forecast_for_time, provider,
                    latitude, longitude, pm1_0, pm2_5, pm10,
                    carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone,
                    aqi, aqi_level, raw_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                forecast_time, forecast_time, 'open-meteo',
                37.6138, -122.4869, None, 12.0, 15.5,
                0.3, 18.0, 2.5, 50.0,
                56, 'Moderate', '{"test": "data"}', forecast_time
            ))
            conn.commit()
            
            cursor = conn.execute('SELECT * FROM forecast_readings WHERE provider = ?', ('open-meteo',))
            row = cursor.fetchone()
        
        result_dict = service._row_to_dict(row)
        
        expected_keys = [
            'forecast_time', 'forecast_for_time', 'provider',
            'latitude', 'longitude', 'pm1_0', 'pm2_5', 'pm10',
            'carbon_monoxide', 'nitrogen_dioxide', 'sulphur_dioxide', 'ozone',
            'aqi', 'aqi_level', 'created_at'
        ]
        
        for key in expected_keys:
            assert key in result_dict
        
        assert result_dict['provider'] == 'open-meteo'
        assert result_dict['pm2_5'] == 12.0
        assert result_dict['aqi'] == 56
        assert result_dict['aqi_level'] == 'Moderate'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])