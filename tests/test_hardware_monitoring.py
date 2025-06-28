"""
Unit tests for hardware monitoring components
"""

import pytest
from unittest.mock import patch, Mock, call
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import app
import air_quality_monitor
import pms7003


@pytest.mark.unit
class TestSystemMonitoring:
    """Test system monitoring functions"""
    
    def test_get_system_info(self, mock_psutil):
        """Test system information gathering"""
        with patch('platform.platform', return_value='Linux-5.4.0-armv7l'), \
             patch('platform.machine', return_value='armv7l'), \
             patch('platform.processor', return_value='arm'), \
             patch('socket.gethostname', return_value='raspberrypi'):
            
            info = app.get_system_info()
            
            assert 'platform' in info
            assert 'hostname' in info
            assert 'cpu_usage' in info
            assert 'memory_percentage' in info
            assert 'disk_info' in info
            assert 'network_info' in info
            assert info['hostname'] == 'raspberrypi'
    
    def test_format_bytes(self):
        """Test byte formatting function"""
        from app import format_bytes
        
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert format_bytes(500) == "500.00 B"
    
    def test_cpu_temperature_raspberry_pi(self, mock_temperature_command):
        """Test CPU temperature on Raspberry Pi"""
        temp = app.get_cpu_temperature()
        assert temp == 56.7
        
        # Verify the command was called correctly
        mock_temperature_command.assert_called_with(
            ['vcgencmd', 'measure_temp'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
    
    def test_cpu_temperature_command_failure(self):
        """Test CPU temperature when vcgencmd fails"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command not found")
            
            temp = app.get_cpu_temperature()
            assert temp is None
    
    def test_cpu_temperature_invalid_output(self):
        """Test CPU temperature with invalid output format"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout = "invalid_output"
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            temp = app.get_cpu_temperature()
            assert temp is None
    
    def test_temperature_history_storage(self):
        """Test temperature history storage"""
        # Clear existing history
        app.temperature_history.clear()
        
        # Add some temperatures
        app.store_temperature(55.0)
        app.store_temperature(56.0)
        app.store_temperature(57.0)
        
        assert len(app.temperature_history) == 3
        assert app.temperature_history[-1][1] == 57.0  # Latest temperature
        
        # Test that history is limited (maxlen=120)
        for i in range(150):
            app.store_temperature(float(i))
        
        assert len(app.temperature_history) <= 120


@pytest.mark.unit
class TestPMS7003Sensor:
    """Test PMS7003 air quality sensor"""
    
    def test_pms7003_initialization(self, mock_serial):
        """Test PMS7003 sensor initialization"""
        sensor = pms7003.PMS7003('/dev/ttyS0')
        assert sensor.port == '/dev/ttyS0'
        assert sensor.baudrate == 9600
    
    def test_pms7003_read_data_success(self, mock_serial):
        """Test successful PMS7003 data reading"""
        # Mock valid PMS7003 data packet
        valid_packet = (
            b'\x42\x4d'  # Start bytes
            b'\x00\x1c'  # Frame length (28 bytes)
            b'\x00\x05'  # PM1.0 (5 μg/m³)
            b'\x00\x08'  # PM2.5 (8 μg/m³)
            b'\x00\x0c'  # PM10 (12 μg/m³)
            b'\x00\x05'  # PM1.0 atmospheric
            b'\x00\x08'  # PM2.5 atmospheric
            b'\x00\x0c'  # PM10 atmospheric
            b'\x00\x00'  # Particles >0.3μm
            b'\x00\x00'  # Particles >0.5μm
            b'\x00\x00'  # Particles >1.0μm
            b'\x00\x00'  # Particles >2.5μm
            b'\x00\x00'  # Particles >5.0μm
            b'\x00\x00'  # Particles >10μm
            b'\x00\x00'  # Reserved
            b'\x01\x5e'  # Checksum
        )
        
        mock_serial.read.return_value = valid_packet
        mock_serial.in_waiting = len(valid_packet)
        
        sensor = pms7003.PMS7003('/dev/ttyS0')
        data = sensor.read_data()
        
        assert data is not None
        assert data['pm1_0'] == 5
        assert data['pm2_5'] == 8
        assert data['pm10'] == 12
    
    def test_pms7003_invalid_start_bytes(self, mock_serial):
        """Test PMS7003 with invalid start bytes"""
        invalid_packet = b'\x41\x4c' + b'\x00' * 30  # Wrong start bytes
        mock_serial.read.return_value = invalid_packet
        mock_serial.in_waiting = len(invalid_packet)
        
        sensor = pms7003.PMS7003('/dev/ttyS0')
        data = sensor.read_data()
        
        assert data is None
    
    def test_pms7003_checksum_validation(self, mock_serial):
        """Test PMS7003 checksum validation"""
        # Create packet with incorrect checksum
        invalid_packet = (
            b'\x42\x4d'  # Start bytes
            b'\x00\x1c'  # Frame length
            b'\x00\x05'  # PM1.0
            b'\x00\x08'  # PM2.5
            b'\x00\x0c'  # PM10
            + b'\x00' * 18  # Rest of data
            + b'\xFF\xFF'  # Invalid checksum
        )
        
        mock_serial.read.return_value = invalid_packet
        mock_serial.in_waiting = len(invalid_packet)
        
        sensor = pms7003.PMS7003('/dev/ttyS0')
        data = sensor.read_data()
        
        # Should return None due to checksum failure
        assert data is None


@pytest.mark.unit
class TestAirQualityMonitor:
    """Test air quality monitoring service"""
    
    def test_aqi_calculation(self):
        """Test AQI calculation from PM2.5"""
        from air_quality_monitor import calculate_aqi
        
        # Test various PM2.5 levels
        assert calculate_aqi(0) == 0
        assert calculate_aqi(12) == 50    # Good range
        assert calculate_aqi(35.4) == 100 # Moderate range
        assert calculate_aqi(55.4) == 150 # Unhealthy for sensitive
        assert calculate_aqi(250.4) == 300 # Hazardous
    
    def test_aqi_level_determination(self):
        """Test AQI level string determination"""
        from air_quality_monitor import get_aqi_level
        
        assert get_aqi_level(25) == "Good"
        assert get_aqi_level(75) == "Moderate"
        assert get_aqi_level(125) == "Unhealthy for Sensitive Groups"
        assert get_aqi_level(175) == "Unhealthy"
        assert get_aqi_level(225) == "Very Unhealthy"
        assert get_aqi_level(350) == "Hazardous"
    
    @patch('air_quality_monitor.PMS7003')
    @patch('air_quality_monitor.database')
    def test_monitor_loop_success(self, mock_db, mock_pms_class):
        """Test successful monitoring loop iteration"""
        # Setup mocks
        mock_sensor = Mock()
        mock_sensor.read_data.return_value = {
            'pm1_0': 5,
            'pm2_5': 12,
            'pm10': 18
        }
        mock_pms_class.return_value = mock_sensor
        
        # Mock temperature reading
        with patch('air_quality_monitor.get_cpu_temperature', return_value=55.0):
            monitor = air_quality_monitor.AirQualityMonitor()
            monitor.setup()
            
            # Run one iteration
            monitor.read_and_store_data()
            
            # Verify database insertion was called
            mock_db.insert_air_quality_reading.assert_called_once()
            call_args = mock_db.insert_air_quality_reading.call_args[1]
            assert call_args['pm2_5'] == 12
            assert call_args['aqi'] == 50  # Should be calculated
    
    @patch('air_quality_monitor.PMS7003')
    def test_monitor_loop_sensor_failure(self, mock_pms_class):
        """Test monitoring loop with sensor read failure"""
        mock_sensor = Mock()
        mock_sensor.read_data.return_value = None  # Sensor read failure
        mock_pms_class.return_value = mock_sensor
        
        monitor = air_quality_monitor.AirQualityMonitor()
        monitor.setup()
        
        # Should handle sensor failure gracefully
        result = monitor.read_and_store_data()
        assert result is False
    
    def test_monitor_signal_handling(self):
        """Test signal handling in monitor"""
        monitor = air_quality_monitor.AirQualityMonitor()
        assert monitor.running is True
        
        # Simulate signal
        monitor.signal_handler(None, None)
        assert monitor.running is False


@pytest.mark.hardware
@pytest.mark.slow
class TestHardwareIntegration:
    """Integration tests requiring actual hardware"""
    
    @pytest.mark.skipif(not Path('/dev/ttyS0').exists(), reason="No serial port available")
    def test_real_serial_port_access(self):
        """Test actual serial port access (Pi hardware required)"""
        try:
            sensor = pms7003.PMS7003('/dev/ttyS0')
            # Just test that we can create the object
            assert sensor.port == '/dev/ttyS0'
        except Exception as e:
            pytest.skip(f"Serial port access failed: {e}")
    
    @pytest.mark.skipif(not Path('/opt/vc/bin/vcgencmd').exists(), reason="vcgencmd not available")
    def test_real_cpu_temperature(self):
        """Test actual CPU temperature reading (Pi hardware required)"""
        temp = app.get_cpu_temperature()
        if temp is not None:
            assert 0 < temp < 100  # Reasonable temperature range
        else:
            pytest.skip("CPU temperature reading not available")