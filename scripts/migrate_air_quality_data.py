#!/usr/bin/env python3
"""
Migration script to move air quality data from old database to new unified database
"""

import sqlite3
import sys
import os
from datetime import datetime

def migrate_air_quality_data():
    """Migrate air quality readings from old database to new database"""
    
    # Define database paths
    old_db_path = "air_quality.db"
    new_db_path = "data/monitoring.db"
    
    # Check if old database exists
    if not os.path.exists(old_db_path):
        print(f"Error: Old database '{old_db_path}' not found")
        return False
    
    # Check if new database exists
    if not os.path.exists(new_db_path):
        print(f"Error: New database '{new_db_path}' not found")
        print("Please run the application first to create the new database")
        return False
    
    print(f"Migrating data from '{old_db_path}' to '{new_db_path}'...")
    
    try:
        # Connect to both databases
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(new_db_path)
        
        # Check if air_quality_readings table exists in old database
        old_cursor = old_conn.cursor()
        old_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='air_quality_readings'
        """)
        if not old_cursor.fetchone():
            print("Error: 'air_quality_readings' table not found in old database")
            return False
        
        # Count existing records in old database
        old_cursor.execute("SELECT COUNT(*) FROM air_quality_readings")
        old_count = old_cursor.fetchone()[0]
        print(f"Found {old_count} records in old database")
        
        if old_count == 0:
            print("No records to migrate")
            return True
        
        # Check for existing data in new database to avoid duplicates
        new_cursor = new_conn.cursor()
        new_cursor.execute("SELECT COUNT(*) FROM air_quality_readings")
        existing_count = new_cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Warning: New database already contains {existing_count} air quality records")
            response = input("Do you want to continue and potentially create duplicates? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled")
                return False
        
        # Get the oldest and newest timestamps from old database
        old_cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM air_quality_readings
        """)
        min_time, max_time = old_cursor.fetchone()
        print(f"Data range: {min_time} to {max_time}")
        
        # Fetch all records from old database
        old_cursor.execute("""
            SELECT timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level, 
                   temperature, humidity, sample_count
            FROM air_quality_readings
            ORDER BY timestamp
        """)
        
        records = old_cursor.fetchall()
        
        # Insert records into new database
        print(f"Migrating {len(records)} records...")
        
        new_cursor = new_conn.cursor()
        inserted = 0
        errors = 0
        
        for record in records:
            try:
                new_cursor.execute("""
                    INSERT INTO air_quality_readings 
                    (timestamp, pm1_0, pm2_5, pm10, aqi, aqi_level, 
                     temperature, humidity, sample_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, record)
                inserted += 1
                
                # Show progress every 100 records
                if inserted % 100 == 0:
                    print(f"  Migrated {inserted} records...")
                    
            except sqlite3.IntegrityError as e:
                # Skip duplicates
                errors += 1
                continue
            except Exception as e:
                print(f"Error inserting record: {e}")
                errors += 1
                continue
        
        # Commit the changes
        new_conn.commit()
        
        print(f"\nMigration complete!")
        print(f"  Records migrated: {inserted}")
        print(f"  Errors/skipped: {errors}")
        
        # Verify the migration
        new_cursor.execute("SELECT COUNT(*) FROM air_quality_readings")
        final_count = new_cursor.fetchone()[0]
        print(f"  Total records in new database: {final_count}")
        
        # Close connections
        old_conn.close()
        new_conn.close()
        
        # Ask if user wants to backup and remove old database
        print(f"\nOld database '{old_db_path}' still exists.")
        response = input("Do you want to rename it to 'air_quality_backup.db'? (Y/n): ")
        if response.lower() != 'n':
            backup_path = "air_quality_backup.db"
            if os.path.exists(backup_path):
                print(f"Backup already exists at '{backup_path}'")
                response = input("Overwrite existing backup? (y/N): ")
                if response.lower() != 'y':
                    print("Keeping original database as is")
                    return True
            
            os.rename(old_db_path, backup_path)
            print(f"Old database renamed to '{backup_path}'")
        
        return True
        
    except Exception as e:
        print(f"Migration failed with error: {e}")
        return False

if __name__ == "__main__":
    print("Air Quality Data Migration Tool")
    print("================================")
    print("This will migrate air quality data from the old database")
    print("to the new unified monitoring database.")
    print()
    
    # Change to the pi_air directory if we're in scripts/
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')
        print(f"Changed to directory: {os.getcwd()}")
    
    success = migrate_air_quality_data()
    
    if success:
        print("\nMigration successful!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)