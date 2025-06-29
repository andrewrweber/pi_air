#!/usr/bin/env python3
"""
Clear cached forecast data from the database.
Useful when testing forecast functionality or when cached data becomes stale.
"""

import sqlite3
import sys
import os

# Add the src directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config import config
    db_path = config.get('database.path', 'monitoring.db')
except ImportError:
    # Fallback if config can't be imported
    db_path = 'monitoring.db'

def clear_forecast_cache():
    """Clear all cached forecast data"""
    try:
        # Check if file exists
        if not os.path.exists(db_path):
            print(f"Database file not found: {db_path}")
            return False
        
        # Connect and clear
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='forecast_readings'
        """)
        
        if not cursor.fetchone():
            print("No forecast_readings table found - nothing to clear")
            conn.close()
            return True
        
        # Get count before clearing
        cursor.execute("SELECT COUNT(*) FROM forecast_readings")
        count_before = cursor.fetchone()[0]
        
        # Clear the data
        cursor.execute("DELETE FROM forecast_readings")
        conn.commit()
        
        # Get count after clearing
        cursor.execute("SELECT COUNT(*) FROM forecast_readings")
        count_after = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"Cleared {count_before - count_after} cached forecast readings")
        print(f"Database: {db_path}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = clear_forecast_cache()
    sys.exit(0 if success else 1)