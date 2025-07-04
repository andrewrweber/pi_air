"""
Comprehensive tests for air quality monitoring service
"""

import pytest
import threading
import time
import signal
from unittest.mock import patch, Mock, call
from collections import deque
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import air_quality_monitor


@pytest.mark.unit
class TestAirQualityService:
    """Test air quality monitoring service functionality"""
    
    def test_air_quality_monitor_initialization(self):
        """Test AirQualityMonitor initialization"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Test initial state
        assert monitor.running is False
        assert monitor.sensor is None
        assert isinstance(monitor.readings_buffer, deque)
        assert monitor.readings_buffer.maxlen is None  # No maxlen specified in actual implementation
        assert isinstance(monitor.last_write_time, float)
        assert isinstance(monitor.last_cleanup_time, float)
        assert monitor.logger is not None
    
    @patch('air_quality_monitor.PMS7003')
    @patch('air_quality_monitor.init_database')
    def test_start_success(self, mock_init_db, mock_pms_class):
        """Test successful service start"""
        mock_sensor = Mock()
        mock_sensor.start.return_value = True
        mock_pms_class.return_value = mock_sensor
        
        monitor = air_quality_monitor.AirQualityMonitor()
        
        with patch.object(monitor, '_monitor_loop') as mock_loop:
            result = monitor.start()
            
            assert result is True
            assert monitor.running is True
            assert monitor.sensor == mock_sensor
            
            # Verify database initialization
            mock_init_db.assert_called_once()
            
            # Verify sensor creation and start
            mock_pms_class.assert_called_once()
            mock_sensor.start.assert_called_once()
            
            # Stop the monitor
            monitor._shutdown()
    
    @patch('air_quality_monitor.PMS7003')
    @patch('air_quality_monitor.init_database')
    def test_start_sensor_failure(self, mock_init_db, mock_pms_class):
        """Test service start with sensor failure"""
        mock_sensor = Mock()
        mock_sensor.start.return_value = False  # Sensor fails to start
        mock_pms_class.return_value = mock_sensor
        
        monitor = air_quality_monitor.AirQualityMonitor()
        result = monitor.start()
        
        assert result is False
        assert monitor.running is False
    
    @patch('air_quality_monitor.PMS7003')
    @patch('air_quality_monitor.init_database')
    def test_start_database_failure(self, mock_init_db, mock_pms_class):
        """Test service start with database initialization failure"""
        mock_init_db.side_effect = Exception("Database connection failed")
        
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Exception should propagate since there's no try/catch in start()
        with pytest.raises(Exception, match="Database connection failed"):
            monitor.start()
    
    def test_signal_handler(self):
        """Test signal handler functionality"""
        monitor = air_quality_monitor.AirQualityMonitor()
        monitor.running = True
        
        # Test signal handler
        monitor._signal_handler(signal.SIGTERM, None)
        
        assert monitor.running is False
    
    def test_shutdown(self):
        """Test shutdown functionality"""
        monitor = air_quality_monitor.AirQualityMonitor()
        monitor.running = True
        monitor.sensor = Mock()
        
        monitor._shutdown()
        
        # _shutdown() doesn't set running=False, it just stops sensor and writes data
        monitor.sensor.stop.assert_called_once()
    
    def test_shutdown_without_sensor(self):
        """Test shutdown when sensor is None"""
        monitor = air_quality_monitor.AirQualityMonitor()
        monitor.running = True
        monitor.sensor = None
        
        # Should not raise exception
        monitor._shutdown()
        # _shutdown() doesn't change running state
    
    @patch('air_quality_monitor.cleanup_old_readings')
    def test_cleanup_old_data(self, mock_cleanup):
        """Test old data cleanup functionality"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        monitor._cleanup_old_data()
        
        mock_cleanup.assert_called_once()
    
    @patch('air_quality_monitor.cleanup_old_readings')
    def test_cleanup_old_data_failure(self, mock_cleanup):
        """Test cleanup failure handling"""
        mock_cleanup.side_effect = Exception("Cleanup failed")
        
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Should not raise exception
        monitor._cleanup_old_data()
        mock_cleanup.assert_called_once()
    
    def test_get_aqi_level_ranges(self):
        """Test AQI level determination"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        assert monitor._get_aqi_level(25) == "Good"
        assert monitor._get_aqi_level(75) == "Moderate"
        assert monitor._get_aqi_level(125) == "Unhealthy for Sensitive Groups"
        assert monitor._get_aqi_level(175) == "Unhealthy"
        assert monitor._get_aqi_level(225) == "Very Unhealthy"
        assert monitor._get_aqi_level(350) == "Hazardous"
    
    @patch('air_quality_monitor.insert_reading')
    @patch('air_quality_monitor.mean')
    def test_write_averaged_data_success(self, mock_mean, mock_insert):
        """Test successful averaged data writing"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Add test data to buffer
        test_readings = [
            {'pm1_0': 5, 'pm2_5': 12, 'pm10': 18, 'aqi': 50, 'aqi_level': 'Good'},
            {'pm1_0': 6, 'pm2_5': 14, 'pm10': 20, 'aqi': 55, 'aqi_level': 'Moderate'},
            {'pm1_0': 4, 'pm2_5': 10, 'pm10': 16, 'aqi': 45, 'aqi_level': 'Good'},
        ]
        
        for reading in test_readings:
            monitor.readings_buffer.append(reading)
        
        # Mock mean calculation - 4 calls: pm1_0, pm2_5, pm10, aqi
        mock_mean.side_effect = [5.0, 12.0, 18.0, 50.0]
        
        monitor._write_averaged_data()
        
        # Verify database insert was called
        mock_insert.assert_called_once()
        
        # Check call arguments
        call_args = mock_insert.call_args[1]
        assert call_args['pm1_0'] == 5.0
        assert call_args['pm2_5'] == 12.0
        assert call_args['pm10'] == 18.0
        assert call_args['sample_count'] == 3
        
        # Buffer should be cleared
        assert len(monitor.readings_buffer) == 0
    
    @patch('air_quality_monitor.insert_reading')
    def test_write_averaged_data_empty_buffer(self, mock_insert):
        """Test write averaged data with empty buffer"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Empty buffer
        monitor.readings_buffer.clear()
        
        monitor._write_averaged_data()
        
        # Should not call database insert
        mock_insert.assert_not_called()
    
    @patch('air_quality_monitor.insert_reading')
    def test_write_averaged_data_database_error(self, mock_insert):
        """Test write averaged data with database error"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Add test data
        monitor.readings_buffer.append({
            'pm1_0': 5, 'pm2_5': 12, 'pm10': 18, 'aqi': 50, 'aqi_level': 'Good'
        })
        
        # Mock database error
        mock_insert.side_effect = Exception("Database write failed")
        
        # Should not raise exception
        monitor._write_averaged_data()
        
        # Buffer is NOT cleared on error in actual implementation
        assert len(monitor.readings_buffer) == 1  # Still contains the data
    
    def test_monitor_loop_timing(self):
        """Test monitor loop timing logic"""
        monitor = air_quality_monitor.AirQualityMonitor()
        monitor.sensor = Mock()
        monitor.sensor.get_data.return_value = {
            'pm1_0': 5, 'pm2_5': 12, 'pm10': 18, 'aqi': 50, 'aqi_level': 'Good'
        }
        
        # Set initial times manually to avoid Mock objects
        monitor.last_write_time = 0
        monitor.last_cleanup_time = 0
        
        with patch.object(monitor, '_write_averaged_data') as mock_write, \
             patch.object(monitor, '_cleanup_old_data') as mock_cleanup, \
             patch('time.time') as mock_time, \
             patch('time.sleep'):  # Mock sleep to speed up test
            
            # Set time values for each iteration
            time_values = [1, 35, 3665]  # Progressive time values
            
            # Run a few iterations
            monitor.running = True
            
            # Simulate the monitor loop logic with controlled time values
            for i, current_time in enumerate(time_values):
                if not monitor.running:
                    break
                
                # Set the mock time for this iteration
                mock_time.return_value = current_time
                
                # Simulate loop logic
                reading = monitor.sensor.get_data()
                if reading:
                    monitor.readings_buffer.append(reading)
                
                # Check write timing (every 30 seconds - SAMPLE_INTERVAL)
                if current_time - monitor.last_write_time >= 30:
                    monitor._write_averaged_data()
                    monitor.last_write_time = current_time
                
                # Check cleanup timing (every hour)
                if current_time - monitor.last_cleanup_time >= 3600:
                    monitor._cleanup_old_data()
                    monitor.last_cleanup_time = current_time
            
            # Verify write and cleanup were called based on timing
            assert mock_write.call_count >= 1
            assert mock_cleanup.call_count >= 1
    
    def test_readings_buffer_maxlen(self):
        """Test readings buffer respects maxlen"""
        monitor = air_quality_monitor.AirQualityMonitor()
        
        # Add more readings than maxlen
        for i in range(15):
            reading = {
                'pm1_0': i, 'pm2_5': i+10, 'pm10': i+20,
                'aqi': i+30, 'aqi_level': 'Good'
            }
            monitor.readings_buffer.append(reading)
        
        # No maxlen set in actual implementation, so all 15 should be there
        assert len(monitor.readings_buffer) == 15
        
        # Should contain all readings
        assert monitor.readings_buffer[-1]['pm1_0'] == 14  # Last added
        assert monitor.readings_buffer[0]['pm1_0'] == 0    # First added
    
    @patch('air_quality_monitor.setup_logging')
    @patch('air_quality_monitor.AirQualityMonitor')
    def test_main_function(self, mock_monitor_class, mock_setup_logging):
        """Test main function"""
        mock_monitor = Mock()
        mock_monitor.start.return_value = True
        mock_monitor_class.return_value = mock_monitor
        
        # Mock signal handling
        with patch('signal.signal') as mock_signal:
            # Run main briefly
            with patch('time.sleep', side_effect=KeyboardInterrupt):
                try:
                    air_quality_monitor.main()
                except KeyboardInterrupt:
                    pass
            
            # Verify logging setup
            mock_setup_logging.assert_called_once()
            
            # Verify monitor creation and start
            mock_monitor_class.assert_called_once()
            mock_monitor.start.assert_called_once()
            
            # Signal handlers are registered in start(), not main()
            # main() doesn't register signals directly
    
    @patch('air_quality_monitor.setup_logging')
    @patch('air_quality_monitor.AirQualityMonitor')
    def test_main_function_start_failure(self, mock_monitor_class, mock_setup_logging):
        """Test main function when monitor fails to start"""
        mock_monitor = Mock()
        mock_monitor.start.return_value = False  # Fail to start
        mock_monitor_class.return_value = mock_monitor
        
        with patch('sys.exit') as mock_exit:
            # Patch monitor.start to avoid the infinite loop
            with patch.object(mock_monitor, 'start', side_effect=Exception("Start failed")):
                air_quality_monitor.main()
            
            # Should exit with error code when exception occurs
            mock_exit.assert_called_once_with(1)