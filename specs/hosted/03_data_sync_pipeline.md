# Stage 3: Data Sync Pipeline

## Overview
Implement the cloud synchronization service that handles uploading sensor data from Raspberry Pi devices to the cloud, with robust offline support and automatic recovery.

## Goals
- Create resilient data sync service
- Handle network outages gracefully
- Implement efficient batch uploads
- Ensure zero data loss
- Provide sync status feedback

## Architecture

### Sync Queue Database Schema

```sql
-- Add to local SQLite database
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_type TEXT NOT NULL, -- 'air_quality' or 'system'
    reading_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    last_retry TIMESTAMP,
    sync_status TEXT DEFAULT 'pending', -- 'pending', 'syncing', 'failed', 'synced'
    error_message TEXT
);

CREATE INDEX idx_sync_queue_status ON sync_queue(sync_status, created_at);

-- Track sync metadata
CREATE TABLE sync_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation

### 1. Cloud Sync Service (`src/services/cloud_sync_service.py`)

```python
import threading
import time
import requests
import json
import gzip
from collections import deque
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from database import get_db_connection
from config import config

logger = logging.getLogger(__name__)

class CloudSyncService:
    """
    Handles syncing local sensor data to cloud service with robust offline support
    """
    
    def __init__(self):
        self.config = config
        self.is_online = False
        self.is_running = False
        self.retry_delay = 30  # seconds
        self.max_retry_delay = 1800  # 30 minutes
        self.sync_thread = None
        self.health_check_thread = None
        self.last_sync_timestamp = self._load_last_sync()
        self.pending_count = 0
        
    def start(self):
        """Start background sync and health check threads"""
        if not self.config.is_cloud_enabled():
            logger.info("Cloud sync disabled - running in self-hosted mode")
            return
            
        self.is_running = True
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        logger.info("Cloud sync service started")
        
    def stop(self):
        """Stop sync service"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            
    def _sync_loop(self):
        """Main sync loop"""
        while self.is_running:
            try:
                if self.is_online:
                    # Sync pending readings
                    synced = self._sync_batch()
                    if synced > 0:
                        logger.info(f"Synced {synced} readings")
                        self.retry_delay = 30  # Reset delay on success
                    
                # Wait before next sync
                time.sleep(self.config.get('cloud.sync_interval', 30))
                
            except Exception as e:
                logger.error(f"Sync error: {e}")
                self._handle_sync_error()
                
    def _health_check_loop(self):
        """Monitor network connectivity"""
        while self.is_running:
            try:
                # Ping health endpoint
                response = requests.get(
                    f"{self.config.get('cloud.api_endpoint')}/health",
                    timeout=5
                )
                
                was_offline = not self.is_online
                self.is_online = response.status_code == 200
                
                if was_offline and self.is_online:
                    logger.info("Connection restored - resuming sync")
                    self._on_reconnect()
                    
            except requests.RequestException:
                self.is_online = False
                
            # Exponential backoff for health checks
            delay = self.retry_delay if not self.is_online else 30
            time.sleep(delay)
            
    def _sync_batch(self) -> int:
        """Sync a batch of readings"""
        with get_db_connection() as conn:
            # Get pending readings
            air_quality_batch = self._get_pending_readings(conn, 'air_quality')
            system_batch = self._get_pending_readings(conn, 'system')
            
            synced_count = 0
            
            # Sync air quality readings
            if air_quality_batch:
                if self._upload_batch('air_quality', air_quality_batch):
                    self._mark_synced(conn, 'air_quality', [r['id'] for r in air_quality_batch])
                    synced_count += len(air_quality_batch)
                    
            # Sync system readings
            if system_batch:
                if self._upload_batch('system', system_batch):
                    self._mark_synced(conn, 'system', [r['id'] for r in system_batch])
                    synced_count += len(system_batch)
                    
            # Update pending count for UI
            self.pending_count = self._get_pending_count(conn)
            
            return synced_count
            
    def _get_pending_readings(self, conn, reading_type: str, limit: int = 100) -> List[Dict]:
        """Get pending readings from sync queue"""
        if reading_type == 'air_quality':
            query = """
                SELECT aq.*, sq.id as sync_id
                FROM air_quality_readings aq
                JOIN sync_queue sq ON sq.reading_id = aq.id
                WHERE sq.reading_type = ? 
                AND sq.sync_status = 'pending'
                ORDER BY aq.timestamp ASC
                LIMIT ?
            """
        else:
            query = """
                SELECT sr.*, sq.id as sync_id
                FROM system_readings sr
                JOIN sync_queue sq ON sq.reading_id = sr.id
                WHERE sq.reading_type = ?
                AND sq.sync_status = 'pending'
                ORDER BY sr.timestamp ASC
                LIMIT ?
            """
            
        cursor = conn.execute(query, (reading_type, limit))
        return [dict(row) for row in cursor.fetchall()]
        
    def _upload_batch(self, reading_type: str, readings: List[Dict]) -> bool:
        """Upload a batch of readings to cloud"""
        try:
            # Prepare payload
            payload = {
                'readings': readings,
                'type': reading_type,
                'batch_id': self._generate_batch_id(),
                'compressed': False
            }
            
            # Compress if large
            json_data = json.dumps(payload)
            if len(json_data) > 1024:  # 1KB threshold
                json_data = gzip.compress(json_data.encode())
                payload['compressed'] = True
                
            # Upload
            headers = {
                'X-API-Key': self.config.get_api_key(),
                'Content-Type': 'application/json'
            }
            
            if payload['compressed']:
                headers['Content-Encoding'] = 'gzip'
                
            response = requests.post(
                f"{self.config.get('cloud.api_endpoint')}/api/v1/device/data",
                data=json_data if payload['compressed'] else json.dumps(payload),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Update last sync timestamp
                result = response.json()
                self._save_last_sync(result.get('last_sync_timestamp'))
                return True
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
            
    def _mark_synced(self, conn, reading_type: str, reading_ids: List[int]):
        """Mark readings as synced"""
        placeholders = ','.join('?' * len(reading_ids))
        conn.execute(f"""
            UPDATE sync_queue 
            SET sync_status = 'synced', last_retry = CURRENT_TIMESTAMP
            WHERE reading_type = ? AND reading_id IN ({placeholders})
        """, [reading_type] + reading_ids)
        
    def add_reading(self, reading_type: str, reading_id: int):
        """Add a reading to the sync queue"""
        if not self.config.is_cloud_enabled():
            return
            
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO sync_queue (reading_type, reading_id)
                VALUES (?, ?)
            """, (reading_type, reading_id))
            
    def _on_reconnect(self):
        """Handle reconnection after offline period"""
        # Backfill any missed readings
        self._backfill_readings()
        
    def _backfill_readings(self):
        """Sync historical data after extended outage"""
        with get_db_connection() as conn:
            # Find readings not in sync queue
            conn.execute("""
                INSERT INTO sync_queue (reading_type, reading_id)
                SELECT 'air_quality', id FROM air_quality_readings
                WHERE id NOT IN (SELECT reading_id FROM sync_queue WHERE reading_type = 'air_quality')
                AND timestamp > ?
            """, (self.last_sync_timestamp,))
            
            conn.execute("""
                INSERT INTO sync_queue (reading_type, reading_id)
                SELECT 'system', id FROM system_readings
                WHERE id NOT IN (SELECT reading_id FROM sync_queue WHERE reading_type = 'system')
                AND timestamp > ?
            """, (self.last_sync_timestamp,))
            
    def get_sync_status(self) -> Dict:
        """Get current sync status for UI"""
        return {
            'is_online': self.is_online,
            'pending_count': self.pending_count,
            'last_sync': self.last_sync_timestamp,
            'retry_delay': self.retry_delay
        }
```

### 2. Modified Air Quality Monitor (`src/air_quality_monitor.py`)

Add cloud sync integration:

```python
# In the existing AirQualityMonitor class

def __init__(self):
    # Existing initialization...
    self.cloud_sync = None
    if config.is_cloud_enabled():
        from services.cloud_sync_service import CloudSyncService
        self.cloud_sync = CloudSyncService()

def start(self):
    """Start the monitoring service"""
    # Existing start logic...
    
    # Start cloud sync if enabled
    if self.cloud_sync:
        self.cloud_sync.start()

def _write_averaged_data(self):
    """Calculate averages and write to database"""
    # Existing averaging logic...
    
    # Insert reading
    reading_id = insert_reading(avg_pm1_0, avg_pm2_5, avg_pm10, aqi, aqi_level)
    
    # Queue for sync if cloud enabled
    if self.cloud_sync:
        self.cloud_sync.add_reading('air_quality', reading_id)
```

### 3. API Endpoint (`src/api/device_data.py`)

```python
from flask import Blueprint, request, jsonify
import gzip
import json
from database import get_db_connection

device_api = Blueprint('device_api', __name__)

@device_api.route('/api/v1/device/data', methods=['POST'])
def upload_data():
    """Handle device data uploads"""
    # Verify API key
    api_key = request.headers.get('X-API-Key')
    if not verify_api_key(api_key):
        return jsonify({'error': 'Invalid API key'}), 401
        
    # Decompress if needed
    data = request.data
    if request.headers.get('Content-Encoding') == 'gzip':
        data = gzip.decompress(data)
        
    payload = json.loads(data)
    
    # Process readings
    accepted = 0
    errors = []
    
    for reading in payload['readings']:
        try:
            # Insert into database
            insert_cloud_reading(reading, payload['type'])
            accepted += 1
        except Exception as e:
            errors.append(str(e))
            
    return jsonify({
        'accepted': accepted,
        'errors': errors,
        'last_sync_timestamp': datetime.utcnow().isoformat()
    })
```

## Testing Requirements

### Unit Tests
- [ ] Test batch preparation
- [ ] Test compression logic
- [ ] Test retry mechanism
- [ ] Test offline detection

### Integration Tests
- [ ] Simulate network outage
- [ ] Verify data queued locally
- [ ] Test reconnection and backfill
- [ ] Verify no data loss

### Performance Tests
- [ ] Upload 1000 readings
- [ ] Test with slow connection
- [ ] Verify batch size limits
- [ ] Test concurrent syncs

## Success Criteria
- [ ] Data syncs within 1 minute of collection
- [ ] Zero data loss during outages
- [ ] Automatic recovery on reconnection
- [ ] Sync status visible in UI
- [ ] Efficient batch uploads

## Next Stage
Once data sync is working reliably, proceed to Stage 4: Authentication & Web Dashboard.