#!/usr/bin/env python3
"""
Alert Integration Module
Integrates the alert system with existing monitoring components
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime

from alerts import AlertManager, Alert, AlertType, AlertSeverity
from config import config
from database import get_latest_reading, get_latest_system_reading

logger = logging.getLogger(__name__)


class MonitoringAlertService:
    """Service that integrates alerting with monitoring systems"""
    
    def __init__(self):
        self.alert_manager = None
        self.last_air_quality_check = 0
        self.last_system_health_check = 0
        self.last_staleness_check = 0
        self.lock = threading.Lock()
        
        # Check intervals (seconds)
        self.air_quality_check_interval = 60  # Check air quality every minute
        self.system_health_check_interval = 300  # Check system health every 5 minutes
        self.staleness_check_interval = 120  # Check data staleness every 2 minutes
        
        self._initialize_alert_manager()
    
    def _initialize_alert_manager(self):
        """Initialize the alert manager with current configuration"""
        try:
            if config.is_alerts_enabled():
                self.alert_manager = AlertManager(config.alerts)
                logger.info("Alert manager initialized successfully")
            else:
                logger.info("Alerting is disabled in configuration")
        except Exception as e:
            logger.error(f"Failed to initialize alert manager: {e}")
            self.alert_manager = None
    
    def check_air_quality_alerts(self, air_quality_data: Dict[str, Any]) -> List[Alert]:
        """Check and send air quality alerts"""
        alerts = []
        
        if not self.alert_manager or not air_quality_data:
            return alerts
        
        try:
            # Check for air quality threshold alerts
            air_alerts = self.alert_manager.check_air_quality_alerts(air_quality_data)
            
            for alert in air_alerts:
                if self.alert_manager.send_alert(alert):
                    alerts.append(alert)
                    logger.info(f"Sent air quality alert: {alert.title}")
                else:
                    logger.error(f"Failed to send air quality alert: {alert.title}")
            
            self.last_air_quality_check = time.time()
            
        except Exception as e:
            logger.error(f"Error checking air quality alerts: {e}")
        
        return alerts
    
    def check_system_health_alerts(self, system_data: Dict[str, Any]) -> List[Alert]:
        """Check and send system health alerts"""
        alerts = []
        
        if not self.alert_manager or not system_data:
            return alerts
        
        try:
            # Check for system health alerts
            health_alerts = self.alert_manager.check_system_health_alerts(system_data)
            
            for alert in health_alerts:
                if self.alert_manager.send_alert(alert):
                    alerts.append(alert)
                    logger.info(f"Sent system health alert: {alert.title}")
                else:
                    logger.error(f"Failed to send system health alert: {alert.title}")
            
            self.last_system_health_check = time.time()
            
        except Exception as e:
            logger.error(f"Error checking system health alerts: {e}")
        
        return alerts
    
    def check_sensor_failure_alert(self, error_message: str, sensor_type: str = "PMS7003") -> Optional[Alert]:
        """Check and send sensor failure alert"""
        if not self.alert_manager:
            return None
        
        try:
            alert = self.alert_manager.check_sensor_failure_alert(error_message, sensor_type)
            
            if alert:
                if self.alert_manager.send_alert(alert):
                    logger.info(f"Sent sensor failure alert: {alert.title}")
                    return alert
                else:
                    logger.error(f"Failed to send sensor failure alert: {alert.title}")
            
        except Exception as e:
            logger.error(f"Error checking sensor failure alert: {e}")
        
        return None
    
    def check_data_staleness_alerts(self) -> Optional[Alert]:
        """Check for stale data alerts by examining database"""
        if not self.alert_manager:
            return None
        
        try:
            # Check air quality data staleness
            latest_reading = get_latest_reading()
            
            if latest_reading:
                # Parse timestamp from database
                timestamp_str = latest_reading['timestamp']
                # Handle different timestamp formats
                try:
                    if 'T' in timestamp_str:
                        # ISO format
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        # SQLite format
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    last_update = dt.timestamp()
                    
                    alert = self.alert_manager.check_data_staleness_alert(
                        last_update, 
                        threshold_minutes=5
                    )
                    
                    if alert:
                        if self.alert_manager.send_alert(alert):
                            logger.info(f"Sent data staleness alert: {alert.title}")
                            return alert
                        else:
                            logger.error(f"Failed to send data staleness alert: {alert.title}")
                
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing timestamp from database: {e}")
            
            self.last_staleness_check = time.time()
            
        except Exception as e:
            logger.error(f"Error checking data staleness alerts: {e}")
        
        return None
    
    def periodic_check(self):
        """Perform periodic alert checks"""
        if not self.alert_manager:
            return
        
        try:
            now = time.time()
            
            # Check data staleness
            if now - self.last_staleness_check > self.staleness_check_interval:
                self.check_data_staleness_alerts()
            
            # Check air quality (if we have recent data)
            if now - self.last_air_quality_check > self.air_quality_check_interval:
                latest_reading = get_latest_reading()
                if latest_reading:
                    # Convert database reading to the format expected by alerts
                    air_quality_data = {
                        'pm1_0': latest_reading['pm1_0'],
                        'pm2_5': latest_reading['pm2_5'],
                        'pm10': latest_reading['pm10'],
                        'aqi': latest_reading['aqi'],
                        'aqi_level': latest_reading['aqi_level']
                    }
                    self.check_air_quality_alerts(air_quality_data)
            
            # Check system health (if we have recent data)
            if now - self.last_system_health_check > self.system_health_check_interval:
                latest_system = get_latest_system_reading()
                if latest_system:
                    system_data = {
                        'cpu_temp': latest_system['cpu_temp'],
                        'cpu_usage': latest_system['cpu_usage'],
                        'memory_usage': latest_system['memory_usage'],
                        'disk_usage': latest_system['disk_usage']
                    }
                    self.check_system_health_alerts(system_data)
        
        except Exception as e:
            logger.error(f"Error in periodic alert check: {e}")
    
    def reload_configuration(self):
        """Reload alert configuration"""
        logger.info("Reloading alert configuration")
        self._initialize_alert_manager()
    
    def send_test_alert(self) -> bool:
        """Send a test alert"""
        if not self.alert_manager:
            logger.error("Alert manager not initialized")
            return False
        
        return self.alert_manager.send_test_alert()
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification methods"""
        if not self.alert_manager:
            return {"error": "Alert manager not initialized"}
        
        return self.alert_manager.test_notifications()
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        if not self.alert_manager:
            return []
        
        return self.alert_manager.get_alert_history(limit)
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        if not self.alert_manager:
            return {"enabled": False, "error": "Alert manager not initialized"}
        
        return self.alert_manager.get_alert_stats()
    
    def is_enabled(self) -> bool:
        """Check if alerting is enabled"""
        return self.alert_manager is not None and config.is_alerts_enabled()


# Global alert service instance
alert_service = MonitoringAlertService()


# Convenience functions for integration with existing code
def check_air_quality_alerts(air_quality_data: Dict[str, Any]) -> List[Alert]:
    """Convenience function to check air quality alerts"""
    return alert_service.check_air_quality_alerts(air_quality_data)


def check_system_health_alerts(system_data: Dict[str, Any]) -> List[Alert]:
    """Convenience function to check system health alerts"""
    return alert_service.check_system_health_alerts(system_data)


def check_sensor_failure_alert(error_message: str, sensor_type: str = "PMS7003") -> Optional[Alert]:
    """Convenience function to check sensor failure alerts"""
    return alert_service.check_sensor_failure_alert(error_message, sensor_type)


def periodic_alert_check():
    """Convenience function for periodic alert checks"""
    alert_service.periodic_check()


def send_test_alert() -> bool:
    """Convenience function to send test alert"""
    return alert_service.send_test_alert()


def test_alert_notifications() -> Dict[str, bool]:
    """Convenience function to test notifications"""
    return alert_service.test_notifications()


def get_alert_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Convenience function to get alert history"""
    return alert_service.get_alert_history(limit)


def get_alert_stats() -> Dict[str, Any]:
    """Convenience function to get alert stats"""
    return alert_service.get_alert_stats()


def is_alerting_enabled() -> bool:
    """Convenience function to check if alerting is enabled"""
    return alert_service.is_enabled()