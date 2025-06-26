#!/usr/bin/env python3
"""
Database module for air quality data storage
"""

import sqlite3
import datetime
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = "air_quality.db"

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
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON air_quality_readings(timestamp DESC)
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

def cleanup_old_readings():
    """Remove readings older than 24 hours"""
    with get_db_connection() as conn:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        deleted = conn.execute("""
            DELETE FROM air_quality_readings
            WHERE timestamp < ?
        """, (cutoff_time,)).rowcount
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old readings")
            # Vacuum to reclaim disk space
            conn.execute("VACUUM")

def get_database_stats() -> Dict:
    """Get database statistics"""
    with get_db_connection() as conn:
        stats = {}
        
        # Total readings
        stats['total_readings'] = conn.execute(
            "SELECT COUNT(*) FROM air_quality_readings"
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