#!/usr/bin/env python3
"""
Intelligent Alert System for Pi Air Monitoring
Provides configurable alerting for air quality thresholds and system health
"""

import time
import logging
import smtplib
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Import email components
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType(Enum):
    """Types of alerts"""
    AIR_QUALITY = "air_quality"
    SYSTEM_HEALTH = "system_health"
    SENSOR_FAILURE = "sensor_failure"
    DATA_STALENESS = "data_staleness"


@dataclass
class Alert:
    """Alert data structure"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: float
    alert_id: str = None
    
    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = f"{self.alert_type.value}_{int(self.timestamp)}"


class NotificationMethod:
    """Base class for notification methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
    
    def send(self, alert: Alert) -> bool:
        """Send alert notification - to be implemented by subclasses"""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """Test connection - to be implemented by subclasses"""
        return True


class EmailNotification(NotificationMethod):
    """Email notification method"""
    
    def send(self, alert: Alert) -> bool:
        """Send email notification"""
        if not self.enabled:
            return True
            
        try:
            smtp_config = self.config.get('smtp', {})
            if not all(k in smtp_config for k in ['server', 'port', 'username', 'password']):
                logger.error("Email notification: Missing SMTP configuration")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config['username']
            msg['To'] = ', '.join(self.config.get('recipients', []))
            msg['Subject'] = f"[Pi Air Monitor] {alert.severity.value.upper()}: {alert.title}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            logger.info(f"Email alert sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body"""
        severity_colors = {
            AlertSeverity.INFO: '#17a2b8',
            AlertSeverity.WARNING: '#ffc107',
            AlertSeverity.CRITICAL: '#dc3545',
            AlertSeverity.EMERGENCY: '#6f42c1'
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        timestamp_str = datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin: 0;">{alert.title}</h2>
                <p style="color: #666; margin: 5px 0;"><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p style="color: #666; margin: 5px 0;"><strong>Time:</strong> {timestamp_str}</p>
                <p style="color: #666; margin: 5px 0;"><strong>Type:</strong> {alert.alert_type.value.replace('_', ' ').title()}</p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 16px;">{alert.message}</p>
            </div>
            
            <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px;">
                <h4 style="margin-top: 0;">Alert Data:</h4>
                <pre style="background-color: white; padding: 10px; border-radius: 3px; overflow-x: auto;">{json.dumps(alert.data, indent=2)}</pre>
            </div>
            
            <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                This alert was generated by Pi Air Monitor at {timestamp_str}
            </p>
        </body>
        </html>
        """
        return html
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            smtp_config = self.config.get('smtp', {})
            if not all(k in smtp_config for k in ['server', 'port', 'username', 'password']):
                return False
                
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                return True
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False


class WebhookNotification(NotificationMethod):
    """Webhook notification method"""
    
    def send(self, alert: Alert) -> bool:
        """Send webhook notification"""
        if not self.enabled:
            return True
            
        try:
            url = self.config.get('url')
            if not url:
                logger.error("Webhook notification: Missing URL")
                return False
            
            # Prepare payload
            payload = {
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'data': alert.data,
                'timestamp': alert.timestamp,
                'alert_id': alert.alert_id
            }
            
            # Add custom fields if configured
            custom_fields = self.config.get('custom_fields', {})
            payload.update(custom_fields)
            
            # Prepare request
            data = json.dumps(payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Pi-Air-Monitor/1.0'
            }
            
            # Add custom headers if configured
            custom_headers = self.config.get('headers', {})
            headers.update(custom_headers)
            
            # Send request
            req = urllib.request.Request(url, data=data, headers=headers)
            timeout = self.config.get('timeout', 10)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status >= 200 and response.status < 300:
                    logger.info(f"Webhook alert sent: {alert.title}")
                    return True
                else:
                    logger.error(f"Webhook failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test webhook connection"""
        try:
            url = self.config.get('url')
            if not url:
                return False
                
            # Send test payload
            test_payload = {
                'test': True,
                'message': 'Pi Air Monitor webhook test',
                'timestamp': time.time()
            }
            
            data = json.dumps(test_payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Pi-Air-Monitor/1.0'
            }
            
            custom_headers = self.config.get('headers', {})
            headers.update(custom_headers)
            
            req = urllib.request.Request(url, data=data, headers=headers)
            timeout = self.config.get('timeout', 10)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status >= 200 and response.status < 300
                
        except Exception as e:
            logger.error(f"Webhook connection test failed: {e}")
            return False


class LogNotification(NotificationMethod):
    """Log-only notification method"""
    
    def send(self, alert: Alert) -> bool:
        """Log alert notification"""
        if not self.enabled:
            return True
            
        log_level = self.config.get('level', 'info').upper()
        log_func = getattr(logger, log_level.lower(), logger.info)
        
        log_func(f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        logger.debug(f"Alert data: {json.dumps(alert.data, indent=2)}")
        
        return True


class AlertManager:
    """Main alert management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.alert_history = []
        self.rate_limits = {}
        self.lock = threading.Lock()
        
        # Initialize notification methods
        self.notification_methods = []
        self._init_notification_methods()
        
        # Load alert rules
        self.alert_rules = self._load_alert_rules()
        
        logger.info(f"AlertManager initialized: enabled={self.enabled}, "
                   f"methods={len(self.notification_methods)}, rules={len(self.alert_rules)}")
    
    def _init_notification_methods(self):
        """Initialize configured notification methods"""
        notifications_config = self.config.get('notifications', {})
        
        # Email
        if 'email' in notifications_config:
            self.notification_methods.append(
                EmailNotification(notifications_config['email'])
            )
        
        # Webhook
        if 'webhook' in notifications_config:
            self.notification_methods.append(
                WebhookNotification(notifications_config['webhook'])
            )
        
        # Log (always available)
        log_config = notifications_config.get('log', {'enabled': True})
        self.notification_methods.append(LogNotification(log_config))
    
    def _load_alert_rules(self) -> List[Dict[str, Any]]:
        """Load alert rules from configuration"""
        return self.config.get('rules', [])
    
    def check_air_quality_alerts(self, data: Dict[str, Any]) -> List[Alert]:
        """Check for air quality threshold alerts"""
        alerts = []
        
        if not self.enabled or not data:
            return alerts
        
        # Check AQI thresholds
        aqi = data.get('aqi', 0)
        aqi_level = data.get('aqi_level', 'Unknown')
        pm25 = data.get('pm2_5', 0)
        
        for rule in self.alert_rules:
            if rule.get('type') != 'air_quality' or not rule.get('enabled', True):
                continue
            
            condition = rule.get('condition', {})
            if self._evaluate_air_quality_condition(condition, data):
                alert = Alert(
                    alert_type=AlertType.AIR_QUALITY,
                    severity=AlertSeverity(rule.get('severity', 'warning')),
                    title=rule.get('title', f"Air Quality Alert - {aqi_level}"),
                    message=rule.get('message', '').format(**data),
                    data=data,
                    timestamp=time.time()
                )
                
                if self._should_send_alert(alert):
                    alerts.append(alert)
        
        return alerts
    
    def check_system_health_alerts(self, system_data: Dict[str, Any]) -> List[Alert]:
        """Check for system health alerts"""
        alerts = []
        
        if not self.enabled or not system_data:
            return alerts
        
        for rule in self.alert_rules:
            if rule.get('type') != 'system_health' or not rule.get('enabled', True):
                continue
            
            condition = rule.get('condition', {})
            if self._evaluate_system_condition(condition, system_data):
                alert = Alert(
                    alert_type=AlertType.SYSTEM_HEALTH,
                    severity=AlertSeverity(rule.get('severity', 'warning')),
                    title=rule.get('title', "System Health Alert"),
                    message=rule.get('message', '').format(**system_data),
                    data=system_data,
                    timestamp=time.time()
                )
                
                if self._should_send_alert(alert):
                    alerts.append(alert)
        
        return alerts
    
    def check_sensor_failure_alert(self, error_message: str, sensor_type: str = "PMS7003") -> Optional[Alert]:
        """Check for sensor failure alerts"""
        if not self.enabled:
            return None
        
        # Look for sensor failure rules
        for rule in self.alert_rules:
            if rule.get('type') != 'sensor_failure' or not rule.get('enabled', True):
                continue
            
            alert = Alert(
                alert_type=AlertType.SENSOR_FAILURE,
                severity=AlertSeverity(rule.get('severity', 'critical')),
                title=rule.get('title', f"{sensor_type} Sensor Failure"),
                message=rule.get('message', f"Sensor failure detected: {error_message}"),
                data={'sensor_type': sensor_type, 'error': error_message},
                timestamp=time.time()
            )
            
            if self._should_send_alert(alert):
                return alert
        
        return None
    
    def check_data_staleness_alert(self, last_update: float, threshold_minutes: int = 5) -> Optional[Alert]:
        """Check for stale data alerts"""
        if not self.enabled:
            return None
        
        age_minutes = (time.time() - last_update) / 60
        
        if age_minutes > threshold_minutes:
            for rule in self.alert_rules:
                if rule.get('type') != 'data_staleness' or not rule.get('enabled', True):
                    continue
                
                alert = Alert(
                    alert_type=AlertType.DATA_STALENESS,
                    severity=AlertSeverity(rule.get('severity', 'warning')),
                    title=rule.get('title', "Stale Data Alert"),
                    message=rule.get('message', f"Data is {age_minutes:.1f} minutes old"),
                    data={'age_minutes': age_minutes, 'threshold_minutes': threshold_minutes},
                    timestamp=time.time()
                )
                
                if self._should_send_alert(alert):
                    return alert
        
        return None
    
    def _evaluate_air_quality_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate air quality alert condition"""
        if not condition:
            return False
        
        # Check AQI threshold
        if 'aqi_above' in condition:
            if data.get('aqi', 0) <= condition['aqi_above']:
                return False
        
        # Check PM2.5 threshold
        if 'pm25_above' in condition:
            if data.get('pm2_5', 0) <= condition['pm25_above']:
                return False
        
        # Check PM10 threshold
        if 'pm10_above' in condition:
            if data.get('pm10', 0) <= condition['pm10_above']:
                return False
        
        # Check AQI level
        if 'aqi_level_in' in condition:
            if data.get('aqi_level') not in condition['aqi_level_in']:
                return False
        
        return True
    
    def _evaluate_system_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate system health alert condition"""
        if not condition:
            return False
        
        # Check CPU temperature
        if 'cpu_temp_above' in condition:
            cpu_temp = data.get('cpu_temp')
            if cpu_temp is None or cpu_temp <= condition['cpu_temp_above']:
                return False
        
        # Check CPU usage
        if 'cpu_usage_above' in condition:
            if data.get('cpu_usage', 0) <= condition['cpu_usage_above']:
                return False
        
        # Check memory usage
        if 'memory_usage_above' in condition:
            if data.get('memory_usage', 0) <= condition['memory_usage_above']:
                return False
        
        # Check disk usage
        if 'disk_usage_above' in condition:
            if data.get('disk_usage', 0) <= condition['disk_usage_above']:
                return False
        
        return True
    
    def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on rate limiting"""
        with self.lock:
            now = time.time()
            key = f"{alert.alert_type.value}_{alert.severity.value}"
            
            # Get rate limit configuration
            rate_limit_minutes = self.config.get('rate_limits', {}).get(key, 
                self.config.get('default_rate_limit_minutes', 15))
            
            # Check if we've sent this type of alert recently
            if key in self.rate_limits:
                last_sent = self.rate_limits[key]
                if now - last_sent < rate_limit_minutes * 60:
                    logger.debug(f"Rate limiting alert: {key}")
                    return False
            
            # Update rate limit
            self.rate_limits[key] = now
            
            # Add to history
            self.alert_history.append({
                'alert': asdict(alert),
                'sent_time': now
            })
            
            # Limit history size
            max_history = self.config.get('max_history_size', 100)
            if len(self.alert_history) > max_history:
                self.alert_history = self.alert_history[-max_history:]
            
            return True
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert using all configured notification methods"""
        if not self.enabled:
            return False
        
        success = True
        for method in self.notification_methods:
            try:
                if not method.send(alert):
                    success = False
            except Exception as e:
                logger.error(f"Error sending alert via {type(method).__name__}: {e}")
                success = False
        
        return success
    
    def send_test_alert(self) -> bool:
        """Send a test alert to verify configuration"""
        test_alert = Alert(
            alert_type=AlertType.SYSTEM_HEALTH,
            severity=AlertSeverity.INFO,
            title="Pi Air Monitor Test Alert",
            message="This is a test alert to verify the alerting system is working properly.",
            data={'test': True, 'timestamp': time.time()},
            timestamp=time.time()
        )
        
        return self.send_alert(test_alert)
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification methods"""
        results = {}
        
        for method in self.notification_methods:
            method_name = type(method).__name__
            try:
                results[method_name] = method.test_connection()
            except Exception as e:
                logger.error(f"Error testing {method_name}: {e}")
                results[method_name] = False
        
        return results
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        with self.lock:
            return self.alert_history[-limit:] if limit else self.alert_history.copy()
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        with self.lock:
            now = time.time()
            day_ago = now - 86400  # 24 hours
            
            recent_alerts = [a for a in self.alert_history if a['sent_time'] > day_ago]
            
            stats = {
                'enabled': self.enabled,
                'total_alerts_24h': len(recent_alerts),
                'alert_types_24h': {},
                'severity_counts_24h': {},
                'notification_methods': len(self.notification_methods),
                'active_rules': len([r for r in self.alert_rules if r.get('enabled', True)]),
                'rate_limits_active': len(self.rate_limits)
            }
            
            # Count by type and severity
            for alert_record in recent_alerts:
                alert_data = alert_record['alert']
                alert_type = alert_data['alert_type']
                severity = alert_data['severity']
                
                stats['alert_types_24h'][alert_type] = stats['alert_types_24h'].get(alert_type, 0) + 1
                stats['severity_counts_24h'][severity] = stats['severity_counts_24h'].get(severity, 0) + 1
            
            return stats