#!/usr/bin/env python3
"""
Database module for air quality and system monitoring data storage
"""

import sqlite3
import datetime
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Use environment variable or default to data directory relative to project root
DB_PATH = os.environ.get('MONITORING_DB_PATH', 
                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    'data', 'monitoring.db'))

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database schema"""
    # Ensure the data directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS air_quality_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pm1_0 REAL NOT NULL,
                pm2_5 REAL NOT NULL,
                pm10 REAL NOT NULL,
                aqi INTEGER NOT NULL,
                aqi_level TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                sample_count INTEGER DEFAULT 1
            )
        """)
        
        # Create index on timestamp for faster queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_air_quality_timestamp 
            ON air_quality_readings(timestamp DESC)
        """)
        
        # Create system readings table for CPU temperature and other system metrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_temp REAL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL
            )
        """)
        
        # Create index on system readings timestamp
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_timestamp 
            ON system_readings(timestamp DESC)
        """)
        
        logger.info("Database initialized successfully")

def insert_reading(pm1_0: float, pm2_5: float, pm10: float, 
                  aqi: int, aqi_level: str, temperature: Optional[float] = None,
                  humidity: Optional[float] = None, sample_count: int = 1):
    """Insert a new air quality reading"""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO air_quality_readings 
            (pm1_0, pm2_5, pm10, aqi, aqi_level, temperature, humidity, sample_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pm1_0, pm2_5, pm10, aqi, aqi_level, temperature, humidity, sample_count))
        
        logger.debug(f"Inserted reading: PM2.5={pm2_5}, AQI={aqi}")

def get_latest_reading() -> Optional[Dict]:
    """Get the most recent air quality reading"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT * FROM air_quality_readings
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()
        
        if row:
            return dict(row)
        return None

def get_readings_last_24h() -> List[Dict]:
    """Get all readings from the last 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = conn.execute("""
            SELECT * FROM air_quality_readings
            WHERE timestamp > ?
            ORDER BY timestamp ASC
        """, (cutoff_time,)).fetchall()
        
        return [dict(row) for row in rows]

def get_hourly_averages_24h() -> List[Dict]:
    """Get hourly averages for the last 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                AVG(pm1_0) as avg_pm1_0,
                AVG(pm2_5) as avg_pm2_5,
                AVG(pm10) as avg_pm10,
                AVG(aqi) as avg_aqi,
                AVG(temperature) as avg_temperature,
                COUNT(*) as reading_count
            FROM air_quality_readings
            WHERE timestamp > ?
            GROUP BY hour
            ORDER BY hour ASC
        """, (cutoff_time,)).fetchall()
        
        return [dict(row) for row in rows]

def get_15min_averages_24h() -> List[Dict]:
    """Get 15-minute averages for the last 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:', timestamp) || 
                CASE 
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 15 THEN '00:00'
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 30 THEN '15:00'
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 45 THEN '30:00'
                    ELSE '45:00'
                END as interval_time,
                AVG(pm1_0) as avg_pm1_0,
                AVG(pm2_5) as avg_pm2_5,
                AVG(pm10) as avg_pm10,
                AVG(aqi) as avg_aqi,
                AVG(temperature) as avg_temperature,
                COUNT(*) as reading_count
            FROM air_quality_readings
            WHERE timestamp > ?
            GROUP BY interval_time
            ORDER BY interval_time ASC
        """, (cutoff_time,)).fetchall()
        
        return [dict(row) for row in rows]

def get_interval_averages(hours: int = 24, interval_minutes: int = 15) -> List[Dict]:
    """Get interval averages for a specified time period with configurable interval
    
    Args:
        hours: Number of hours to look back (1, 6, or 24)
        interval_minutes: Interval size in minutes (2, 5, or 15)
    
    Returns:
        List of dictionaries with interval averages
    """
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        
        # Build the interval time formatting based on interval_minutes
        if interval_minutes == 2:
            # 2-minute intervals: round to nearest 2 minutes
            interval_sql = """
                strftime('%Y-%m-%d %H:', timestamp) || 
                printf('%02d:00', (CAST(strftime('%M', timestamp) AS INTEGER) / 2) * 2)
            """
        elif interval_minutes == 5:
            # 5-minute intervals: round to nearest 5 minutes
            interval_sql = """
                strftime('%Y-%m-%d %H:', timestamp) || 
                printf('%02d:00', (CAST(strftime('%M', timestamp) AS INTEGER) / 5) * 5)
            """
        else:
            # Default 15-minute intervals
            interval_sql = """
                strftime('%Y-%m-%d %H:', timestamp) || 
                CASE 
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 15 THEN '00:00'
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 30 THEN '15:00'
                    WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 45 THEN '30:00'
                    ELSE '45:00'
                END
            """
        
        query = f"""
            SELECT 
                {interval_sql} as interval_time,
                AVG(pm1_0) as avg_pm1_0,
                AVG(pm2_5) as avg_pm2_5,
                AVG(pm10) as avg_pm10,
                AVG(aqi) as avg_aqi,
                AVG(temperature) as avg_temperature,
                COUNT(*) as reading_count
            FROM air_quality_readings
            WHERE timestamp > ?
            GROUP BY interval_time
            ORDER BY interval_time ASC
        """
        
        rows = conn.execute(query, (cutoff_time,)).fetchall()
        
        # Log for debugging
        if rows:
            logger.debug(f"get_interval_averages: Requested {hours}h with {interval_minutes}min intervals")
            logger.debug(f"Cutoff time: {cutoff_time}")
            logger.debug(f"First row timestamp: {rows[0]['interval_time']}")
            logger.debug(f"Last row timestamp: {rows[-1]['interval_time']}")
            logger.debug(f"Total rows returned: {len(rows)}")
        else:
            logger.debug(f"get_interval_averages: No data found for {hours}h range")
        
        return [dict(row) for row in rows]

def get_temperature_history_optimized(hours: int = 24, max_points: int = 100) -> List[Dict]:
    """Get optimized temperature history with limited data points for charting
    
    Args:
        hours: Number of hours to look back (default: 24)
        max_points: Maximum number of data points to return (default: 100)
    
    Returns:
        List of dictionaries with timestamp and cpu_temp, limited to max_points
    """
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        
        # First, check how many total records we have in the time range
        total_count = conn.execute("""
            SELECT COUNT(*) FROM system_readings
            WHERE timestamp > ? AND cpu_temp IS NOT NULL
        """, (cutoff_time,)).fetchone()[0]
        
        logger.debug(f"get_temperature_history_optimized: {total_count} total records for {hours}h range")
        
        if total_count <= max_points:
            # If we have fewer records than max_points, just return them all
            rows = conn.execute("""
                SELECT timestamp, cpu_temp
                FROM system_readings
                WHERE timestamp > ? AND cpu_temp IS NOT NULL
                ORDER BY timestamp ASC
            """, (cutoff_time,)).fetchall()
        else:
            # Use LIMIT with OFFSET to sample evenly across the dataset
            step = max(1, total_count // max_points)
            rows = conn.execute("""
                SELECT timestamp, cpu_temp
                FROM system_readings
                WHERE timestamp > ? AND cpu_temp IS NOT NULL
                ORDER BY timestamp ASC
                LIMIT ? OFFSET 0
            """, (cutoff_time, max_points)).fetchall()
        
        result = [dict(row) for row in rows]
        logger.debug(f"get_temperature_history_optimized: returning {len(result)} data points")
        return result

def cleanup_old_readings():
    """Remove readings older than 24 hours from both tables"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        
        # Clean up air quality readings
        air_deleted = conn.execute("""
            DELETE FROM air_quality_readings
            WHERE timestamp < ?
        """, (cutoff_time,)).rowcount
        
        # Clean up system readings
        system_deleted = conn.execute("""
            DELETE FROM system_readings
            WHERE timestamp < ?
        """, (cutoff_time,)).rowcount
        
        total_deleted = air_deleted + system_deleted
        if total_deleted > 0:
            logger.info(f"Cleaned up {air_deleted} air quality readings and {system_deleted} system readings")
            # Vacuum to reclaim disk space
            conn.execute("VACUUM")

def get_database_stats() -> Dict:
    """Get database statistics"""
    with get_db_connection() as conn:
        stats = {}
        
        # Total air quality readings
        stats['total_air_quality_readings'] = conn.execute(
            "SELECT COUNT(*) FROM air_quality_readings"
        ).fetchone()[0]
        
        # Total system readings
        stats['total_system_readings'] = conn.execute(
            "SELECT COUNT(*) FROM system_readings"
        ).fetchone()[0]
        
        # Oldest reading
        oldest = conn.execute(
            "SELECT MIN(timestamp) FROM air_quality_readings"
        ).fetchone()[0]
        stats['oldest_reading'] = oldest
        
        # Database size
        stats['db_size_kb'] = conn.execute(
            "SELECT page_count * page_size / 1024 FROM pragma_page_count(), pragma_page_size()"
        ).fetchone()[0]
        
        return stats

# System readings functions
def insert_system_reading(cpu_temp: Optional[float] = None, 
                         cpu_usage: Optional[float] = None,
                         memory_usage: Optional[float] = None,
                         disk_usage: Optional[float] = None):
    """Insert a new system reading"""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO system_readings 
            (cpu_temp, cpu_usage, memory_usage, disk_usage)
            VALUES (?, ?, ?, ?)
        """, (cpu_temp, cpu_usage, memory_usage, disk_usage))
        
        logger.debug(f"Inserted system reading: CPU temp={cpu_temp}, CPU usage={cpu_usage}")

def get_latest_system_reading() -> Optional[Dict]:
    """Get the most recent system reading"""
    with get_db_connection() as conn:
        row = conn.execute("""
            SELECT * FROM system_readings
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()
        
        if row:
            return dict(row)
        return None

def get_system_readings_last_24h() -> List[Dict]:
    """Get all system readings from the last 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = conn.execute("""
            SELECT * FROM system_readings
            WHERE timestamp > ?
            ORDER BY timestamp ASC
        """, (cutoff_time,)).fetchall()
        
        return [dict(row) for row in rows]

def get_system_hourly_averages_24h() -> List[Dict]:
    """Get hourly averages for system metrics for the last 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        rows = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                AVG(cpu_temp) as avg_cpu_temp,
                AVG(cpu_usage) as avg_cpu_usage,
                AVG(memory_usage) as avg_memory_usage,
                AVG(disk_usage) as avg_disk_usage,
                COUNT(*) as reading_count
            FROM system_readings
            WHERE timestamp > ?
            GROUP BY hour
            ORDER BY hour ASC
        """, (cutoff_time,)).fetchall()
        
        return [dict(row) for row in rows]

def cleanup_old_system_readings():
    """Remove system readings older than 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        deleted = conn.execute("""
            DELETE FROM system_readings
            WHERE timestamp < ?
        """, (cutoff_time,)).rowcount
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old system readings")