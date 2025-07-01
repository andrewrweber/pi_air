#!/usr/bin/env python3
"""
Test script for the Pi Air Monitor Alert System
"""

import sys
import os
import unittest
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from alerts import AlertManager, Alert, AlertType, AlertSeverity, EmailNotification, WebhookNotification, LogNotification
from config import Config


class TestAlertSystem(unittest.TestCase):
    """Test the alert system components"""
    
    def setUp(self):
        """Set up test configuration"""
        self.test_config = {
            'enabled': True,
            'default_rate_limit_minutes': 1,  # Short for testing
            'max_history_size': 10,
            'notifications': {
                'log': {'enabled': True, 'level': 'info'},
                'email': {'enabled': False},
                'webhook': {'enabled': False}
            },
            'rules': [
                {
                    'type': 'air_quality',
                    'enabled': True,
                    'severity': 'warning',
                    'title': 'Test Air Quality Alert',
                    'message': 'AQI is {aqi}',
                    'condition': {'aqi_above': 100}
                },
                {
                    'type': 'system_health',
                    'enabled': True,
                    'severity': 'critical',
                    'title': 'Test System Alert',
                    'message': 'CPU temp is {cpu_temp}°C',
                    'condition': {'cpu_temp_above': 70}
                }
            ],
            'rate_limits': {
                'air_quality_warning': 1,
                'system_health_critical': 1
            }
        }
    
    def test_alert_creation(self):
        """Test Alert object creation"""
        alert = Alert(
            alert_type=AlertType.AIR_QUALITY,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            data={'aqi': 150},
            timestamp=time.time()
        )
        
        self.assertEqual(alert.alert_type, AlertType.AIR_QUALITY)
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertEqual(alert.title, "Test Alert")
        self.assertIsNotNone(alert.alert_id)
    
    def test_log_notification(self):
        """Test log notification method"""
        config = {'enabled': True, 'level': 'info'}
        log_notifier = LogNotification(config)
        
        alert = Alert(
            alert_type=AlertType.AIR_QUALITY,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            data={},
            timestamp=time.time()
        )
        
        with patch('alerts.logger') as mock_logger:
            result = log_notifier.send(alert)
            self.assertTrue(result)
            mock_logger.info.assert_called()
    
    def test_email_notification_disabled(self):
        """Test email notification when disabled"""
        config = {'enabled': False}
        email_notifier = EmailNotification(config)
        
        alert = Alert(
            alert_type=AlertType.AIR_QUALITY,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            data={},
            timestamp=time.time()
        )
        
        result = email_notifier.send(alert)
        self.assertTrue(result)  # Should return True when disabled
    
    def test_webhook_notification_disabled(self):
        """Test webhook notification when disabled"""
        config = {'enabled': False}
        webhook_notifier = WebhookNotification(config)
        
        alert = Alert(
            alert_type=AlertType.AIR_QUALITY,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            data={},
            timestamp=time.time()
        )
        
        result = webhook_notifier.send(alert)
        self.assertTrue(result)  # Should return True when disabled
    
    def test_alert_manager_initialization(self):
        """Test AlertManager initialization"""
        manager = AlertManager(self.test_config)
        
        self.assertTrue(manager.enabled)
        self.assertEqual(len(manager.notification_methods), 3)  # log, email, webhook
        self.assertEqual(len(manager.alert_rules), 2)
    
    def test_air_quality_alert_condition(self):
        """Test air quality alert condition evaluation"""
        manager = AlertManager(self.test_config)
        
        # Test data that should trigger alert
        data = {'aqi': 150, 'pm2_5': 45, 'aqi_level': 'Unhealthy'}
        alerts = manager.check_air_quality_alerts(data)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.AIR_QUALITY)
        self.assertEqual(alerts[0].severity, AlertSeverity.WARNING)
    
    def test_air_quality_alert_no_trigger(self):
        """Test air quality alert when condition not met"""
        manager = AlertManager(self.test_config)
        
        # Test data that should NOT trigger alert
        data = {'aqi': 50, 'pm2_5': 15, 'aqi_level': 'Good'}
        alerts = manager.check_air_quality_alerts(data)
        
        self.assertEqual(len(alerts), 0)
    
    def test_system_health_alert_condition(self):
        """Test system health alert condition evaluation"""
        manager = AlertManager(self.test_config)
        
        # Test data that should trigger alert
        data = {'cpu_temp': 75, 'cpu_usage': 50, 'memory_usage': 60}
        alerts = manager.check_system_health_alerts(data)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.SYSTEM_HEALTH)
        self.assertEqual(alerts[0].severity, AlertSeverity.CRITICAL)
    
    def test_sensor_failure_alert(self):
        """Test sensor failure alert"""
        manager = AlertManager(self.test_config)
        
        alert = manager.check_sensor_failure_alert("Connection timeout", "PMS7003")
        
        # Note: Will be None because no sensor_failure rule is defined in test config
        # but the method should not crash
        self.assertIsNone(alert)
    
    def test_data_staleness_alert(self):
        """Test data staleness alert"""
        manager = AlertManager(self.test_config)
        
        # Test with stale data (5 minutes old)
        old_timestamp = time.time() - 300
        alert = manager.check_data_staleness_alert(old_timestamp, threshold_minutes=2)
        
        # Will be None because no data_staleness rule in test config
        self.assertIsNone(alert)
    
    def test_rate_limiting(self):
        """Test alert rate limiting"""
        manager = AlertManager(self.test_config)
        
        # Create same alert twice quickly
        data = {'aqi': 150, 'pm2_5': 45, 'aqi_level': 'Unhealthy'}
        
        # First alert should be sent
        alerts1 = manager.check_air_quality_alerts(data)
        self.assertEqual(len(alerts1), 1)
        
        # Second alert should be rate limited
        alerts2 = manager.check_air_quality_alerts(data)
        self.assertEqual(len(alerts2), 0)
    
    def test_alert_history(self):
        """Test alert history tracking"""
        manager = AlertManager(self.test_config)
        
        # Trigger an alert
        data = {'aqi': 150, 'pm2_5': 45, 'aqi_level': 'Unhealthy'}
        alerts = manager.check_air_quality_alerts(data)
        
        if alerts:  # Only if alert was actually created and not rate limited
            manager.send_alert(alerts[0])
            
            # Check history
            history = manager.get_alert_history()
            self.assertGreater(len(history), 0)
    
    def test_alert_stats(self):
        """Test alert statistics"""
        manager = AlertManager(self.test_config)
        
        stats = manager.get_alert_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('enabled', stats)
        self.assertIn('notification_methods', stats)
        self.assertIn('active_rules', stats)
        self.assertTrue(stats['enabled'])


class TestConfigIntegration(unittest.TestCase):
    """Test configuration integration"""
    
    def test_config_alert_methods(self):
        """Test config alert accessor methods"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_config = {
                'alerts': {
                    'enabled': True,
                    'notifications': {'log': {'enabled': True}},
                    'rules': [{'type': 'test', 'enabled': True}],
                    'rate_limits': {'test': 30}
                }
            }
            json.dump(test_config, f)
            config_path = f.name
        
        try:
            config = Config(config_path)
            
            self.assertTrue(config.is_alerts_enabled())
            self.assertIsInstance(config.get_alert_notifications(), dict)
            self.assertIsInstance(config.get_alert_rules(), list)
            self.assertIsInstance(config.get_alert_rate_limits(), dict)
            
        finally:
            os.unlink(config_path)


def run_basic_tests():
    """Run basic functionality tests"""
    print("Running Basic Alert System Tests")
    print("=" * 35)
    
    # Test 1: Alert creation
    print("1. Testing Alert creation...")
    try:
        alert = Alert(
            alert_type=AlertType.AIR_QUALITY,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test",
            data={'test': True},
            timestamp=time.time()
        )
        print("   ✓ Alert created successfully")
    except Exception as e:
        print(f"   ✗ Alert creation failed: {e}")
        return False
    
    # Test 2: AlertManager initialization
    print("2. Testing AlertManager initialization...")
    try:
        test_config = {
            'enabled': True,
            'notifications': {'log': {'enabled': True}},
            'rules': [],
            'rate_limits': {}
        }
        manager = AlertManager(test_config)
        print("   ✓ AlertManager initialized successfully")
    except Exception as e:
        print(f"   ✗ AlertManager initialization failed: {e}")
        return False
    
    # Test 3: Notification methods
    print("3. Testing notification methods...")
    try:
        log_notifier = LogNotification({'enabled': True, 'level': 'info'})
        email_notifier = EmailNotification({'enabled': False})
        webhook_notifier = WebhookNotification({'enabled': False})
        print("   ✓ Notification methods created successfully")
    except Exception as e:
        print(f"   ✗ Notification method creation failed: {e}")
        return False
    
    print("\n✓ All basic tests passed!")
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'basic':
        # Run basic tests
        success = run_basic_tests()
        sys.exit(0 if success else 1)
    else:
        # Run full test suite
        unittest.main()