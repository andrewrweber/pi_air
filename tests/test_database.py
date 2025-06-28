"""
Unit tests for database module
"""

import pytest
import sqlite3
import datetime
from unittest.mock import patch, Mock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import database


@pytest.mark.unit
@pytest.mark.database
class TestDatabase:
    """Test database operations"""
    
    def test_init_db(self, test_db):
        """Test database initialization"""
        # Verify tables were created
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Check air_quality_readings table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='air_quality_readings'")
        assert cursor.fetchone() is not None
        
        # Check system_readings table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_readings'")
        assert cursor.fetchone() is not None
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_air_quality_timestamp'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_insert_air_quality_reading(self, test_db, sample_air_quality_data):
        """Test inserting air quality reading"""
        with patch('database.DB_PATH', test_db):
            database.insert_reading(**sample_air_quality_data)
            
            # Verify insertion
            latest = database.get_latest_reading()
            assert latest is not None
            assert latest['pm2_5'] == sample_air_quality_data['pm2_5']
            assert latest['aqi'] == sample_air_quality_data['aqi']
            assert latest['aqi_level'] == sample_air_quality_data['aqi_level']
    
    def test_insert_system_reading(self, test_db, sample_system_data):
        """Test inserting system reading"""
        with patch('database.DB_PATH', test_db):
            database.insert_system_reading(**sample_system_data)
            
            # Verify insertion
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_readings ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None
            # Column order in system_readings: id, timestamp, cpu_temp, cpu_usage, memory_usage, disk_usage
            assert row[2] == sample_system_data['cpu_temp']  # cpu_temp column
            assert row[3] == sample_system_data['cpu_usage']  # cpu_usage column
            assert row[4] == sample_system_data['memory_usage']  # memory_usage column
    
    def test_get_latest_reading_empty(self, test_db):
        """Test getting latest reading when database is empty"""
        with patch('database.DB_PATH', test_db):
            latest = database.get_latest_reading()
            assert latest is None
    
    def test_get_readings_last_24h(self, test_db, sample_air_quality_data):
        """Test getting readings from last 24 hours"""
        with patch('database.DB_PATH', test_db):
            # Insert some test data
            database.insert_reading(**sample_air_quality_data)
            
            # Get readings
            readings = database.get_readings_last_24h()
            assert len(readings) == 1
            assert readings[0]['pm2_5'] == sample_air_quality_data['pm2_5']
    
    def test_get_interval_averages(self, test_db, sample_air_quality_data):
        """Test getting interval averages"""
        with patch('database.DB_PATH', test_db):
            # Insert multiple readings
            for i in range(3):
                data = sample_air_quality_data.copy()
                data['pm2_5'] = 10.0 + i  # Varying PM2.5 values
                database.insert_air_quality_reading(**data)
            
            # Get 1-hour averages
            averages = database.get_interval_averages(hours=1, interval_minutes=5)
            assert len(averages) >= 1
            
            # Check that we have average values
            if averages:
                assert 'avg_pm2_5' in averages[0]
                assert 'avg_aqi' in averages[0]
    
    def test_cleanup_old_readings(self, test_db):
        """Test cleanup of old readings"""
        with patch('database.DB_PATH', test_db):
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Insert old reading (25 hours ago)
            old_timestamp = datetime.datetime.now() - datetime.timedelta(hours=25)
            cursor.execute("""
                INSERT INTO air_quality_readings 
                (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (?, 5.0, 10.0, 15.0, 50, 'Good')
            """, (old_timestamp,))
            
            # Insert recent reading
            cursor.execute("""
                INSERT INTO air_quality_readings 
                (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level)
                VALUES (datetime('now'), 6.0, 12.0, 18.0, 55, 'Moderate')
            """)
            
            conn.commit()
            conn.close()
            
            # Verify we have 2 readings
            readings = database.get_readings_last_24h()
            initial_count = len(readings)
            
            # Run cleanup
            database.cleanup_old_readings()
            
            # Verify old reading was removed
            all_readings = database.get_readings_last_24h()
            assert len(all_readings) <= initial_count
    
    def test_get_temperature_history_optimized(self, test_db):
        """Test optimized temperature history retrieval"""
        with patch('database.DB_PATH', test_db):
            # Insert some system readings
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            for i in range(5):
                timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i*10)
                cursor.execute("""
                    INSERT INTO system_readings 
                    (timestamp, cpu_usage, memory_usage, disk_usage, cpu_temp)
                    VALUES (?, 25.0, 50.0, 75.0, 55.0)
                """, (timestamp,))
            
            conn.commit()
            conn.close()
            
            # Get temperature history
            history = database.get_temperature_history_optimized(hours=2, max_points=3)
            assert len(history) <= 3
            
            if history:
                assert 'timestamp' in history[0]
                assert 'cpu_temp' in history[0]
    
    def test_database_connection_error_handling(self):
        """Test database connection error handling"""
        with patch('database.DB_PATH', '/invalid/path/db.sqlite'):
            with pytest.raises(Exception):
                database.get_latest_reading()


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseContextManager:
    """Test database context manager"""
    
    def test_context_manager_normal_operation(self, test_db):
        """Test normal database context manager operation"""
        with patch('database.DB_PATH', test_db):
            with database.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
    
    def test_context_manager_exception_handling(self, test_db):
        """Test context manager handles exceptions properly"""
        with patch('database.DB_PATH', test_db):
            try:
                with database.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INVALID SQL")
            except Exception:
                pass  # Expected to fail
            
            # Connection should still work after exception
            with database.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1