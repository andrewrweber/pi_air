"""
Detailed unit tests for PMS7003 sensor module
"""

import pytest
import threading
import time
from unittest.mock import patch, Mock, call
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pms7003


@pytest.mark.unit
class TestPMS7003Detailed:
    """Detailed tests for PMS7003 sensor functionality"""
    
    def test_pms7003_initialization_default(self):
        """Test PMS7003 initialization with default parameters"""
        sensor = pms7003.PMS7003()
        
        assert sensor.port == '/dev/ttyS0'
        assert sensor.baudrate == 9600
        assert sensor.timeout == 2
        assert sensor.serial is None
        assert sensor.running is False
        assert sensor.lock is not None
        assert sensor.latest_data is None
    
    def test_pms7003_initialization_custom(self):
        """Test PMS7003 initialization with custom parameters"""
        sensor = pms7003.PMS7003(port='/dev/ttyUSB0', baudrate=115200, timeout=5)
        
        assert sensor.port == '/dev/ttyUSB0'
        assert sensor.baudrate == 115200
        assert sensor.timeout == 5
    
    @patch('serial.Serial')
    def test_connect_success(self, mock_serial):
        """Test successful serial connection"""
        mock_conn = Mock()
        mock_serial.return_value = mock_conn
        
        sensor = pms7003.PMS7003()
        result = sensor.connect()
        
        assert result is True
        assert sensor.serial == mock_conn
        mock_serial.assert_called_once_with(
            port='/dev/ttyS0',
            baudrate=9600,
            timeout=2
        )
    
    @patch('serial.Serial')
    def test_connect_failure(self, mock_serial):
        """Test serial connection failure"""
        mock_serial.side_effect = Exception("Port not found")
        
        sensor = pms7003.PMS7003()
        result = sensor.connect()
        
        assert result is False
        assert sensor.serial is None
    
    @patch('serial.Serial')
    def test_start_success(self, mock_serial):
        """Test successful sensor start"""
        mock_conn = Mock()
        mock_serial.return_value = mock_conn
        
        sensor = pms7003.PMS7003()
        
        with patch.object(sensor, '_read_loop') as mock_read_loop:
            result = sensor.start()
            
            assert result is True
            assert sensor.running is True
            assert sensor.serial == mock_conn
            
            # Give thread time to start
            time.sleep(0.1)
            
            # Stop the sensor
            sensor.stop()
    
    @patch('serial.Serial')
    def test_start_connection_failure(self, mock_serial):
        """Test sensor start with connection failure"""
        mock_serial.side_effect = Exception("Connection failed")
        
        sensor = pms7003.PMS7003()
        result = sensor.start()
        
        assert result is False
        assert sensor.running is False
    
    def test_stop(self):
        """Test sensor stop functionality"""
        sensor = pms7003.PMS7003()
        sensor.running = True
        sensor.serial = Mock()
        
        sensor.stop()
        
        assert sensor.running is False
        sensor.serial.close.assert_called_once()
        assert sensor.serial is None
    
    def test_stop_without_connection(self):
        """Test stop when no connection exists"""
        sensor = pms7003.PMS7003()
        sensor.running = True
        sensor.serial = None
        
        # Should not raise exception
        sensor.stop()
        assert sensor.running is False
    
    def test_read_frame_valid_data(self):
        """Test reading valid PMS7003 frame"""
        # Create valid PMS7003 frame
        frame_data = bytearray([
            0x42, 0x4d,  # Start bytes
            0x00, 0x1c,  # Frame length (28 bytes)
            0x00, 0x05,  # PM1.0 (5 μg/m³)
            0x00, 0x0c,  # PM2.5 (12 μg/m³)
            0x00, 0x12,  # PM10 (18 μg/m³)
            0x00, 0x05,  # PM1.0 atmospheric
            0x00, 0x0c,  # PM2.5 atmospheric  
            0x00, 0x12,  # PM10 atmospheric
            0x00, 0x00,  # Particles >0.3μm (high byte)
            0x00, 0x32,  # Particles >0.3μm (low byte) = 50
            0x00, 0x00,  # Particles >0.5μm (high byte)
            0x00, 0x28,  # Particles >0.5μm (low byte) = 40
            0x00, 0x00,  # Particles >1.0μm (high byte)
            0x00, 0x1e,  # Particles >1.0μm (low byte) = 30
            0x00, 0x00,  # Particles >2.5μm (high byte)
            0x00, 0x14,  # Particles >2.5μm (low byte) = 20
            0x00, 0x00,  # Particles >5.0μm (high byte)
            0x00, 0x0a,  # Particles >5.0μm (low byte) = 10
            0x00, 0x00,  # Particles >10μm (high byte)
            0x00, 0x05,  # Particles >10μm (low byte) = 5
            0x00, 0x00,  # Reserved
        ])
        
        # Calculate checksum
        checksum = sum(frame_data) % (2**16)
        frame_data.extend([(checksum >> 8) & 0xFF, checksum & 0xFF])
        
        mock_conn = Mock()
        mock_conn.read.return_value = bytes(frame_data)
        mock_conn.in_waiting = len(frame_data)
        
        sensor = pms7003.PMS7003()
        sensor.serial = mock_conn
        
        result = sensor._read_frame()
        
        assert result is not None
        assert len(result) == len(frame_data)
    
    def test_read_frame_invalid_start(self):
        """Test reading frame with invalid start bytes"""
        invalid_frame = bytearray([0x41, 0x4c] + [0x00] * 30)  # Wrong start bytes
        
        mock_conn = Mock()
        mock_conn.read.return_value = bytes(invalid_frame)
        mock_conn.in_waiting = len(invalid_frame)
        
        sensor = pms7003.PMS7003()
        sensor.serial = mock_conn
        
        result = sensor._read_frame()
        assert result is None
    
    def test_read_frame_timeout(self):
        """Test read frame timeout"""
        mock_conn = Mock()
        mock_conn.read.side_effect = [b'', b'']  # Simulate timeout
        mock_conn.in_waiting = 0
        
        sensor = pms7003.PMS7003()
        sensor.serial = mock_conn
        
        result = sensor._read_frame()
        assert result is None
    
    def test_parse_data_valid(self):
        """Test parsing valid sensor data"""
        # Valid frame data (without start bytes and checksum)
        frame_data = bytes([
            0x00, 0x1c,  # Frame length
            0x00, 0x05,  # PM1.0 = 5
            0x00, 0x0c,  # PM2.5 = 12
            0x00, 0x12,  # PM10 = 18
        ] + [0x00] * 22)  # Rest of frame
        
        sensor = pms7003.PMS7003()
        result = sensor._parse_data(frame_data)
        
        assert result is not None
        assert result['pm1_0'] == 5
        assert result['pm2_5'] == 12
        assert result['pm10'] == 18
        assert 'aqi' in result
        assert 'aqi_level' in result
    
    def test_parse_data_invalid_length(self):
        """Test parsing data with invalid length"""
        short_frame = bytes([0x00, 0x10])  # Too short
        
        sensor = pms7003.PMS7003()
        result = sensor._parse_data(short_frame)
        
        assert result is None
    
    def test_calculate_aqi_ranges(self):
        """Test AQI calculation for different PM2.5 ranges"""
        sensor = pms7003.PMS7003()
        
        # Test Good range (0-12 μg/m³)
        assert sensor._calculate_aqi(0) == 0
        assert sensor._calculate_aqi(12) == 50
        
        # Test Moderate range (12.1-35.4 μg/m³)
        aqi_moderate = sensor._calculate_aqi(25)
        assert 51 <= aqi_moderate <= 100
        
        # Test Unhealthy for Sensitive range (35.5-55.4 μg/m³)
        aqi_sensitive = sensor._calculate_aqi(45)
        assert 101 <= aqi_sensitive <= 150
        
        # Test very high values
        aqi_high = sensor._calculate_aqi(250)
        assert aqi_high >= 250
    
    def test_get_aqi_level_ranges(self):
        """Test AQI level determination"""
        sensor = pms7003.PMS7003()
        
        assert sensor._get_aqi_level(25) == "Good"
        assert sensor._get_aqi_level(75) == "Moderate"
        assert sensor._get_aqi_level(125) == "Unhealthy for Sensitive Groups"
        assert sensor._get_aqi_level(175) == "Unhealthy"
        assert sensor._get_aqi_level(225) == "Very Unhealthy"
        assert sensor._get_aqi_level(350) == "Hazardous"
    
    def test_linear_scale_calculation(self):
        """Test linear scaling function"""
        sensor = pms7003.PMS7003()
        
        # Test linear interpolation
        result = sensor._linear_scale(25, 12.1, 35.4, 51, 100)
        
        # Should be between 51 and 100
        assert 51 <= result <= 100
        
        # Test exact boundaries
        assert sensor._linear_scale(12.1, 12.1, 35.4, 51, 100) == 51
        assert sensor._linear_scale(35.4, 12.1, 35.4, 51, 100) == 100
    
    @patch('threading.Thread')
    def test_read_loop_thread_management(self, mock_thread):
        """Test read loop thread management"""
        sensor = pms7003.PMS7003()
        sensor.serial_conn = Mock()
        sensor.running = True
        
        # Mock thread to prevent actual threading
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        with patch.object(sensor, '_read_frame', return_value=None):
            # Start read loop
            sensor._read_loop()
            
            # Should handle running state properly
            assert sensor.running is True
    
    def test_get_data_with_available_data(self):
        """Test get_data when data is available"""
        sensor = pms7003.PMS7003()
        
        test_data = {
            'pm1_0': 5,
            'pm2_5': 12,
            'pm10': 18,
            'aqi': 50,
            'aqi_level': 'Good'
        }
        
        sensor.latest_data = test_data
        
        result = sensor.get_data()
        assert result == test_data
    
    def test_get_data_no_data_available(self):
        """Test get_data when no data is available"""
        sensor = pms7003.PMS7003()
        sensor.latest_data = None
        
        result = sensor.get_data()
        assert result is None
    
    def test_get_data_thread_safety(self):
        """Test get_data thread safety with lock"""
        sensor = pms7003.PMS7003()
        test_data = {'pm1_0': 5, 'pm2_5': 12, 'pm10': 18}
        sensor.latest_data = test_data
        
        # Test that data access uses the lock
        with patch.object(sensor.lock, '__enter__', return_value=None) as mock_enter, \
             patch.object(sensor.lock, '__exit__', return_value=None) as mock_exit:
            result = sensor.get_data()
            assert result == test_data
            mock_enter.assert_called_once()
            mock_exit.assert_called_once()
    
    def test_checksum_validation(self):
        """Test checksum validation in frame parsing"""
        sensor = pms7003.PMS7003()
        
        # Create frame with correct checksum
        frame_data = bytearray([0x42, 0x4d, 0x00, 0x1c] + [0x00] * 28)
        correct_checksum = sum(frame_data[:-2]) % (2**16)
        frame_data[-2:] = [(correct_checksum >> 8) & 0xFF, correct_checksum & 0xFF]
        
        mock_conn = Mock()
        mock_conn.read.return_value = bytes(frame_data)
        mock_conn.in_waiting = len(frame_data)
        
        sensor.serial = mock_conn
        
        # Should successfully read frame with correct checksum
        result = sensor._read_frame()
        assert result is not None
        
        # Test with incorrect checksum
        frame_data[-1] = 0xFF  # Corrupt checksum
        mock_conn.read.return_value = bytes(frame_data)
        
        result = sensor._read_frame()
        assert result is None  # Should reject frame with bad checksum