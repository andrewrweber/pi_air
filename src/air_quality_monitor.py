#!/usr/bin/env python3
"""
Air Quality Monitoring Service
Continuously reads from PMS7003 sensor and stores averaged data to database
"""

import time
import signal
import sys
import logging
from datetime import datetime
from collections import deque
from statistics import mean

from pms7003 import PMS7003
from database import init_database, insert_reading, cleanup_old_readings
from logging_config import setup_logging
from alert_integration import check_air_quality_alerts, check_sensor_failure_alert, periodic_alert_check

# Configuration
SAMPLE_INTERVAL = 30  # seconds between database writes
CLEANUP_INTERVAL = 3600  # cleanup old data every hour
ALERT_CHECK_INTERVAL = 60  # check alerts every minute

class AirQualityMonitor:
    def __init__(self):
        self.running = False
        self.sensor = None
        self.readings_buffer = deque()
        self.last_write_time = time.time()
        self.last_cleanup_time = time.time()
        self.last_alert_check_time = time.time()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the monitoring service"""
        self.logger.info("Starting Air Quality Monitor Service")
        
        # Initialize database
        init_database()
        
        # Initialize sensor
        try:
            self.sensor = PMS7003()
            if not self.sensor.start():
                self.logger.error("Failed to start PMS7003 sensor")
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize sensor: {e}")
            return False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        self.logger.info("Air Quality Monitor started successfully")
        
        # Main monitoring loop
        self._monitor_loop()
        
        return True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get sensor data
                data = self.sensor.get_data()
                
                if data:
                    # Add to buffer
                    self.readings_buffer.append({
                        'timestamp': time.time(),
                        'pm1_0': data['pm1_0'],
                        'pm2_5': data['pm2_5'],
                        'pm10': data['pm10'],
                        'aqi': data['aqi'],
                        'aqi_level': data['aqi_level']
                    })
                    
                    self.logger.debug(f"Buffer size: {len(self.readings_buffer)}, " +
                                    f"Latest PM2.5: {data['pm2_5']}")
                    
                    # Check for air quality alerts with latest data
                    try:
                        alerts = check_air_quality_alerts(data)
                        if alerts:
                            self.logger.info(f"Triggered {len(alerts)} air quality alerts")
                    except Exception as e:
                        self.logger.error(f"Error checking air quality alerts: {e}")
                
                # Check if it's time to write to database
                if time.time() - self.last_write_time >= SAMPLE_INTERVAL:
                    self._write_averaged_data()
                
                # Check if it's time to cleanup old data
                if time.time() - self.last_cleanup_time >= CLEANUP_INTERVAL:
                    self._cleanup_old_data()
                
                # Check if it's time for periodic alert checks
                if time.time() - self.last_alert_check_time >= ALERT_CHECK_INTERVAL:
                    self._check_periodic_alerts()
                
                # Short sleep to prevent CPU spinning
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}", exc_info=True)
                # Check for sensor failure alert
                try:
                    alert = check_sensor_failure_alert(str(e), "PMS7003")
                    if alert:
                        self.logger.info("Sent sensor failure alert")
                except Exception as alert_error:
                    self.logger.error(f"Error sending sensor failure alert: {alert_error}")
                time.sleep(5)  # Wait longer on error
        
        # Cleanup on exit
        self._shutdown()
    
    def _write_averaged_data(self):
        """Calculate averages and write to database"""
        if not self.readings_buffer:
            self.logger.warning("No readings to average")
            return
        
        try:
            # Calculate averages
            avg_pm1_0 = mean(r['pm1_0'] for r in self.readings_buffer)
            avg_pm2_5 = mean(r['pm2_5'] for r in self.readings_buffer)
            avg_pm10 = mean(r['pm10'] for r in self.readings_buffer)
            avg_aqi = int(mean(r['aqi'] for r in self.readings_buffer))
            
            # Determine AQI level based on averaged AQI
            aqi_level = self._get_aqi_level(avg_aqi)
            
            # Insert into database
            insert_reading(
                pm1_0=avg_pm1_0,
                pm2_5=avg_pm2_5,
                pm10=avg_pm10,
                aqi=avg_aqi,
                aqi_level=aqi_level,
                sample_count=len(self.readings_buffer)
            )
            
            self.logger.info(f"Wrote averaged data to DB: PM2.5={avg_pm2_5:.1f}, " +
                           f"AQI={avg_aqi}, Samples={len(self.readings_buffer)}")
            
            # Clear buffer
            self.readings_buffer.clear()
            self.last_write_time = time.time()
            
        except Exception as e:
            self.logger.error(f"Error writing to database: {e}", exc_info=True)
    
    def _cleanup_old_data(self):
        """Clean up old database entries"""
        try:
            cleanup_old_readings()
            self.last_cleanup_time = time.time()
        except Exception as e:
            self.logger.error(f"Error cleaning up database: {e}", exc_info=True)
    
    def _check_periodic_alerts(self):
        """Perform periodic alert checks"""
        try:
            periodic_alert_check()
            self.last_alert_check_time = time.time()
        except Exception as e:
            self.logger.error(f"Error in periodic alert check: {e}", exc_info=True)
    
    def _get_aqi_level(self, aqi):
        """Get AQI level description"""
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def _shutdown(self):
        """Clean shutdown"""
        self.logger.info("Shutting down Air Quality Monitor")
        
        # Write any remaining data
        if self.readings_buffer:
            self._write_averaged_data()
        
        # Stop sensor
        if self.sensor:
            self.sensor.stop()
        
        self.logger.info("Air Quality Monitor stopped")

def main():
    """Main entry point"""
    # Set up logging - try /var/log first, fall back to local directory
    log_file = None
    try:
        # Try to create log in /var/log
        with open('/var/log/air_quality_monitor.log', 'a'):
            log_file = '/var/log/air_quality_monitor.log'
    except (IOError, OSError):
        # Fall back to local directory
        log_file = 'air_quality_monitor.log'
    
    logger = setup_logging(
        log_level='INFO',
        log_file=log_file
    )
    
    # Create and start monitor
    monitor = AirQualityMonitor()
    
    try:
        monitor.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()