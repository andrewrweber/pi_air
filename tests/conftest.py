"""
Pytest configuration and fixtures for Pi Air Monitor tests
"""

import pytest
import tempfile
import os
import sqlite3
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import app
import database
import logging_config


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    # Use in-memory database for testing
    with tempfile.NamedTemporaryFile(delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    # Mock the database path
    with patch('database.DB_PATH', test_db_path):
        # Initialize test database
        database.init_database()
        
        # Configure Flask app for testing
        app.app.config['TESTING'] = True
        app.app.config['DATABASE'] = test_db_path
        
        with app.app.test_client() as client:
            with app.app.app_context():
                yield client
    
    # Clean up test database
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_db:
        test_db_path = tmp_db.name
    
    with patch('database.DB_PATH', test_db_path):
        database.init_database()
        yield test_db_path
    
    # Clean up
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture
def sample_air_quality_data():
    """Sample air quality data for testing"""
    return {
        'pm1_0': 5.2,
        'pm2_5': 12.8,
        'pm10': 18.5,
        'aqi': 52,
        'aqi_level': 'Moderate',
        'temperature': 23.5,
        'humidity': 45.2,
        'sample_count': 1
    }


@pytest.fixture
def sample_system_data():
    """Sample system data for testing"""
    return {
        'cpu_usage': 25.6,
        'memory_usage': 42.3,
        'disk_usage': 78.9,
        'cpu_temp': 56.7
    }


@pytest.fixture
def mock_psutil():
    """Mock psutil for system monitoring tests"""
    from collections import namedtuple
    
    with patch('psutil.cpu_percent') as mock_cpu, \
         patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.disk_partitions') as mock_partitions, \
         patch('psutil.cpu_count') as mock_cpu_count, \
         patch('psutil.cpu_freq') as mock_cpu_freq, \
         patch('psutil.boot_time') as mock_boot, \
         patch('psutil.net_if_addrs') as mock_net:
        
        # Configure mock returns with proper named tuples
        mock_cpu.return_value = 25.6
        mock_cpu_count.return_value = 4  # 4 cores
        mock_boot.return_value = 1640995200  # Mock boot time
        
        # Mock CPU frequency as named tuple
        CpuFreq = namedtuple('CpuFreq', ['current', 'min', 'max'])
        mock_cpu_freq.return_value = CpuFreq(current=1400.0, min=600.0, max=1400.0)
        
        # Mock memory as named tuple
        VirtualMemory = namedtuple('VirtualMemory', ['total', 'available', 'used', 'percent'])
        mock_memory.return_value = VirtualMemory(
            total=4096 * 1024 * 1024,  # 4GB
            available=2048 * 1024 * 1024,  # 2GB available
            used=2048 * 1024 * 1024,  # 2GB used
            percent=42.3
        )
        
        # Mock disk usage as named tuple
        DiskUsage = namedtuple('DiskUsage', ['total', 'used', 'free', 'percent'])
        mock_disk.return_value = DiskUsage(
            total=32 * 1024 * 1024 * 1024,  # 32GB
            used=15 * 1024 * 1024 * 1024,  # 15GB
            free=17 * 1024 * 1024 * 1024,  # 17GB
            percent=78.9
        )
        
        # Mock disk partitions as named tuples
        DiskPartition = namedtuple('DiskPartition', ['device', 'mountpoint', 'fstype'])
        mock_partitions.return_value = [
            DiskPartition(device='/dev/mmcblk0p2', mountpoint='/', fstype='ext4'),
            DiskPartition(device='/dev/mmcblk0p1', mountpoint='/boot', fstype='vfat')
        ]
        
        # Mock network interfaces with proper structure
        NetInterface = namedtuple('NetInterface', ['address', 'family', 'netmask', 'broadcast'])
        mock_net.return_value = {
            'eth0': [NetInterface(address='192.168.1.100', family=2, netmask='255.255.255.0', broadcast='192.168.1.255')],
            'wlan0': [NetInterface(address='192.168.1.101', family=2, netmask='255.255.255.0', broadcast='192.168.1.255')]
        }
        
        yield {
            'cpu': mock_cpu,
            'memory': mock_memory,
            'disk': mock_disk,
            'partitions': mock_partitions,
            'cpu_count': mock_cpu_count,
            'cpu_freq': mock_cpu_freq,
            'boot': mock_boot,
            'net': mock_net
        }


@pytest.fixture
def mock_serial():
    """Mock serial port for PMS7003 sensor tests"""
    with patch('serial.Serial') as mock_serial:
        mock_port = Mock()
        mock_port.read.return_value = b'\x42\x4d\x00\x1c\x00\x05\x00\x08\x00\x0c'
        mock_port.in_waiting = 32
        mock_serial.return_value = mock_port
        yield mock_port


@pytest.fixture
def mock_temperature_command():
    """Mock vcgencmd temperature command for Raspberry Pi"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.stdout = "temp=56.7'C\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Verify the mock is called with correct command and timeout
        def verify_call(*args, **kwargs):
            assert args[0] == ['/usr/bin/vcgencmd', 'measure_temp']
            assert kwargs.get('timeout', None) == 2
            return mock_result
        
        mock_run.side_effect = verify_call
        yield mock_run


@pytest.fixture
def disable_logging():
    """Disable logging during tests to reduce noise"""
    import logging
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# Pytest markers for organizing tests
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.database = pytest.mark.database
pytest.mark.frontend = pytest.mark.frontend
pytest.mark.slow = pytest.mark.slow
pytest.mark.hardware = pytest.mark.hardware