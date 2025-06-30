"""
Integration tests for timestamp handling in database operations
Tests the interaction between TimestampUtils and database.py
"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime, timezone, timedelta
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.timestamp_utils import TimestampUtils
import database


class TestTimestampDatabaseIntegration(unittest.TestCase):
    """Test cases for timestamp handling in database operations"""

    def setUp(self):
        """Set up test database"""
        # Create temporary database file
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)
        
        # Override the database path
        original_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_path
        
        # Initialize test database
        database.init_database()
        
        # Store original path for cleanup
        self.original_db_path = original_db_path

    def tearDown(self):
        """Clean up test database"""
        # Restore original database path
        database.DB_PATH = self.original_db_path
        
        # Remove test database file
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_database_schema_uses_utc_timestamps(self):
        """Test that database schema creates UTC timestamps"""
        # Insert a reading (uses SQLite CURRENT_TIMESTAMP)
        database.insert_reading(
            pm1_0=10.0, pm2_5=15.0, pm10=20.0,
            aqi=50, aqi_level='Good'
        )
        
        # Get the reading
        reading = database.get_latest_reading()
        self.assertIsNotNone(reading)
        
        # Parse the timestamp
        parsed_timestamp = TimestampUtils.parse_to_utc(reading['timestamp'])
        
        # Should be timezone-aware and in UTC
        self.assertTrue(TimestampUtils.is_timezone_aware(parsed_timestamp))
        self.assertEqual(parsed_timestamp.tzinfo, timezone.utc)
        
        # Should be recent (within last minute)
        now = TimestampUtils.utc_now()
        diff = now - parsed_timestamp
        self.assertLess(diff.total_seconds(), 60)

    def test_database_cutoff_queries_use_utc(self):
        """Test that database cutoff queries work with UTC"""
        # Insert readings at different times
        with database.get_db_connection() as conn:
            # Current time
            database.insert_reading(10.0, 15.0, 20.0, 50, 'Good')
            
            # 25 hours ago (should be excluded from 24h query)
            old_time = TimestampUtils.utc_now() - timedelta(hours=25)
            old_timestamp = old_time.isoformat().replace('+00:00', 'Z')
            conn.execute("""
                INSERT INTO air_quality_readings 
                (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (old_timestamp, 5.0, 10.0, 15.0, 25, 'Good'))
            
            # 12 hours ago (should be included in 24h query)
            recent_time = TimestampUtils.utc_now() - timedelta(hours=12)
            recent_timestamp = recent_time.isoformat().replace('+00:00', 'Z')
            conn.execute("""
                INSERT INTO air_quality_readings 
                (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (recent_timestamp, 8.0, 12.0, 18.0, 40, 'Good'))
        
        # Query last 24 hours
        readings_24h = database.get_readings_last_24h()
        
        # Should get 2 readings (current + 12h ago), not the 25h old one
        self.assertEqual(len(readings_24h), 2)
        
        # Verify timestamps are parseable and reasonable
        for reading in readings_24h:
            parsed = TimestampUtils.parse_to_utc(reading['timestamp'])
            self.assertTrue(TimestampUtils.is_timezone_aware(parsed))
            
            # Should be within last 24 hours
            now = TimestampUtils.utc_now()
            diff = now - parsed
            self.assertLess(diff.total_seconds(), 24 * 3600)

    def test_system_readings_timestamp_consistency(self):
        """Test that system readings use consistent timestamps"""
        # Insert system reading
        database.insert_system_reading(
            cpu_temp=45.0, cpu_usage=20.0,
            memory_usage=60.0, disk_usage=75.0
        )
        
        # Get the reading
        reading = database.get_latest_system_reading()
        self.assertIsNotNone(reading)
        
        # Parse timestamp
        parsed = TimestampUtils.parse_to_utc(reading['timestamp'])
        
        # Should be UTC and recent
        self.assertEqual(parsed.tzinfo, timezone.utc)
        now = TimestampUtils.utc_now()
        diff = now - parsed
        self.assertLess(diff.total_seconds(), 60)

    def test_interval_averages_with_utc_cutoffs(self):
        """Test that interval averages work correctly with UTC cutoffs"""
        # Insert readings over time
        base_time = TimestampUtils.utc_now() - timedelta(hours=2)
        
        with database.get_db_connection() as conn:
            for i in range(5):
                timestamp = base_time + timedelta(minutes=30 * i)
                timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
                
                conn.execute("""
                    INSERT INTO air_quality_readings 
                    (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp_str, 10.0 + i, 15.0 + i, 20.0 + i, 50 + i, 'Good'))
        
        # Get interval averages
        averages = database.get_interval_averages(hours=3, interval_minutes=60)
        
        # Should get some averages
        self.assertGreater(len(averages), 0)
        
        # Each average should have valid timestamp
        for avg in averages:
            self.assertIn('interval_time', avg)
            parsed = TimestampUtils.parse_to_utc(avg['interval_time'])
            self.assertTrue(TimestampUtils.is_timezone_aware(parsed))

    def test_database_cleanup_with_utc_cutoffs(self):
        """Test that database cleanup works with UTC cutoffs"""
        # Insert old reading
        old_time = TimestampUtils.utc_now() - timedelta(days=8)
        old_timestamp = old_time.isoformat().replace('+00:00', 'Z')
        
        with database.get_db_connection() as conn:
            conn.execute("""
                INSERT INTO air_quality_readings 
                (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (old_timestamp, 10.0, 15.0, 20.0, 50, 'Good'))
        
        # Insert recent reading
        database.insert_reading(12.0, 18.0, 25.0, 60, 'Moderate')
        
        # Count before cleanup
        with database.get_db_connection() as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM air_quality_readings"
            ).fetchone()[0]
        
        # Cleanup readings older than 7 days
        database.cleanup_old_readings(days=7)
        
        # Count after cleanup
        with database.get_db_connection() as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM air_quality_readings"
            ).fetchone()[0]
        
        # Should have removed the old reading
        self.assertEqual(count_after, count_before - 1)
        
        # Remaining reading should be recent
        remaining = database.get_latest_reading()
        parsed = TimestampUtils.parse_to_utc(remaining['timestamp'])
        now = TimestampUtils.utc_now()
        diff = now - parsed
        self.assertLess(diff.total_seconds(), 3600)  # Within last hour

    def test_direct_sqlite_current_timestamp_is_utc(self):
        """Test that SQLite CURRENT_TIMESTAMP produces UTC timestamps"""
        with database.get_db_connection() as conn:
            # Insert using SQLite's CURRENT_TIMESTAMP
            conn.execute("""
                INSERT INTO air_quality_readings 
                (pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (?, ?, ?, ?, ?)
            """, (10.0, 15.0, 20.0, 50, 'Good'))
            
            # Get the timestamp
            result = conn.execute("""
                SELECT timestamp FROM air_quality_readings 
                ORDER BY id DESC LIMIT 1
            """).fetchone()
        
        timestamp_str = result['timestamp']
        
        # Parse using our utilities
        parsed = TimestampUtils.parse_to_utc(timestamp_str)
        
        # Should be close to current UTC time
        now = TimestampUtils.utc_now()
        diff = abs((now - parsed).total_seconds())
        self.assertLess(diff, 10)  # Within 10 seconds

    def test_forecast_timestamp_consistency(self):
        """Test forecast timestamps work with our utilities"""
        # This test requires forecast_service to be importable
        try:
            from services.forecast_service import ForecastService
            
            # Create temporary forecast database
            forecast_service = ForecastService(db_path=self.test_db_path)
            
            # Test that forecast timestamps are properly formatted
            forecast_time = TimestampUtils.utc_now_iso()
            
            # The forecast service should be able to parse this
            parsed = TimestampUtils.parse_to_utc(forecast_time)
            self.assertTrue(TimestampUtils.is_timezone_aware(parsed))
            
        except ImportError:
            # Skip if forecast service dependencies not available
            self.skipTest("Forecast service dependencies not available")


if __name__ == '__main__':
    unittest.main()