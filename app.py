from flask import Flask, render_template, jsonify
from flask_cors import CORS
import psutil
import platform
import datetime
import subprocess
import socket
from typing import Dict, List, Any, Optional, Tuple
import os
import threading
import time
from collections import deque
import logging

app = Flask(__name__)

# Enable CORS for development
if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
    CORS(app)  # Allow all origins in development

# Configure logging
from logging_config import setup_logging
logger = setup_logging(
    log_level=os.environ.get('LOG_LEVEL', 'INFO'),
    log_file=os.environ.get('LOG_FILE', None)
)
logger = logging.getLogger(__name__)

# Optimize for Raspberry Pi Zero 2 W - limit worker threads
if platform.machine().startswith('arm'):
    # Detect ARM architecture (Raspberry Pi)
    app.config['THREADED'] = False

# Temperature history storage
# Store tuples of (timestamp, temperature)
temperature_history = deque(maxlen=120)  # 10 minutes at 5-second intervals (10*60/5 = 120)
temperature_lock = threading.Lock()
latest_temperature = None

# Air quality sensor
air_quality_sensor = None
air_quality_data = None
air_quality_lock = threading.Lock()

def get_size(bytes: float, suffix: str = "B") -> str:
    """Convert bytes to human readable format"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor
    return f"{bytes:.2f}P{suffix}"

def get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature on Raspberry Pi"""
    # Skip temperature reading on non-Raspberry Pi systems
    if platform.system() != 'Linux' or not os.path.exists('/usr/bin/vcgencmd'):
        return None
        
    try:
        # Use subprocess for better security than os.popen
        result = subprocess.run(
            ['vcgencmd', 'measure_temp'], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        if result.returncode == 0:
            # Parse temperature from format: temp=45.6'C
            temp_str = result.stdout.strip()
            temp_value = temp_str.split('=')[1].split("'")[0]
            return float(temp_value)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, IndexError, FileNotFoundError):
        pass
    return None

def sample_temperature():
    """Background thread to sample CPU temperature every 5 seconds"""
    global latest_temperature
    while True:
        try:
            temp = get_cpu_temperature()
            if temp is not None:
                timestamp = datetime.datetime.now().isoformat()
                with temperature_lock:
                    temperature_history.append((timestamp, temp))
                    latest_temperature = temp
        except Exception as e:
            print(f"Error sampling temperature: {e}")
        time.sleep(5)  # Sample every 5 seconds

# Start temperature sampling thread
temperature_thread = threading.Thread(target=sample_temperature, daemon=True)
temperature_thread.start()

def initialize_air_quality_sensor():
    """Initialize PMS7003 sensor if on Raspberry Pi"""
    global air_quality_sensor
    if platform.system() == 'Linux' and os.path.exists('/dev/ttyS0'):
        try:
            from pms7003 import PMS7003
            air_quality_sensor = PMS7003()
            if air_quality_sensor.start():
                logger.info("PMS7003 air quality sensor initialized")
            else:
                logger.warning("Failed to start PMS7003 sensor")
                air_quality_sensor = None
        except ImportError:
            logger.info("PMS7003 module not available")
        except Exception as e:
            logger.error(f"Error initializing PMS7003: {e}")

# Initialize air quality sensor
initialize_air_quality_sensor()

def get_system_info() -> Dict[str, Any]:
    """Gather system information"""
    info = {}
    
    # System info
    info['platform'] = platform.system()
    info['platform_release'] = platform.release()
    info['platform_version'] = platform.version()
    info['architecture'] = platform.machine()
    info['hostname'] = platform.node()
    info['processor'] = platform.processor()
    
    # Boot time with proper formatting
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.datetime.fromtimestamp(boot_time_timestamp)
    info['boot_time'] = bt.strftime("%Y/%m/%d %H:%M:%S")
    
    # CPU info
    info['physical_cores'] = psutil.cpu_count(logical=False)
    info['total_cores'] = psutil.cpu_count(logical=True)
    
    # Handle potential None from cpu_freq
    cpufreq = psutil.cpu_freq()
    if cpufreq:
        info['cpu_freq_current'] = f"{cpufreq.current:.2f}Mhz"
    else:
        info['cpu_freq_current'] = "N/A"
    
    # Non-blocking CPU usage (use 0 interval, let client handle sampling)
    info['cpu_usage'] = f"{psutil.cpu_percent(interval=0)}%"
    
    # CPU temperature (Raspberry Pi specific)
    temp = get_cpu_temperature()
    info['cpu_temp'] = f"{temp:.1f}'C" if temp else "N/A"
    
    # Memory info
    svmem = psutil.virtual_memory()
    info['memory_total'] = get_size(svmem.total)
    info['memory_available'] = get_size(svmem.available)
    info['memory_used'] = get_size(svmem.used)
    info['memory_percentage'] = f"{svmem.percent}%"
    
    # Disk info
    partitions = psutil.disk_partitions()
    disk_info = []
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'file_system': partition.fstype,
                'total_size': get_size(partition_usage.total),
                'used': get_size(partition_usage.used),
                'free': get_size(partition_usage.free),
                'percentage': f"{partition_usage.percent}%"
            })
        except (PermissionError, OSError):
            # Skip inaccessible partitions
            continue
    info['disk_info'] = disk_info
    
    # Network info - properly check for IPv4 addresses
    network_info = []
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            # Use proper enum comparison
            if address.family == socket.AF_INET:
                network_info.append({
                    'interface': interface_name,
                    'ip': address.address,
                    'netmask': address.netmask,
                    'broadcast': address.broadcast
                })
    info['network_info'] = network_info
    
    return info

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/system')
def system_api():
    """API endpoint for complete system information"""
    try:
        response = jsonify(get_system_info())
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        print(f"Error in system_api: {e}")  # Log the actual error
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def stats_api():
    """API endpoint for real-time stats"""
    try:
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),  # 1 second interval for Pi Zero 2 W
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Use stored temperature instead of real-time reading
        with temperature_lock:
            stats['cpu_temp'] = latest_temperature
        
        # Add air quality data if available
        if air_quality_sensor:
            air_data = air_quality_sensor.get_data()
            if air_data:
                stats['air_quality'] = {
                    'pm1_0': air_data['pm1_0'],
                    'pm2_5': air_data['pm2_5'],
                    'pm10': air_data['pm10'],
                    'aqi': air_data['aqi'],
                    'aqi_level': air_data['aqi_level']
                }
        
        response = jsonify(stats)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        print(f"Error in stats_api: {e}")  # Log the actual error
        return jsonify({'error': str(e)}), 500

@app.route('/api/temperature-history')
def temperature_history_api():
    """API endpoint for temperature history"""
    try:
        with temperature_lock:
            # Convert deque to list of dictionaries for JSON serialization
            history = [
                {'timestamp': ts, 'temperature': temp} 
                for ts, temp in temperature_history
            ]
        
        response = jsonify({'history': history})
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        print(f"Error in temperature_history_api: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Configuration should be environment-based
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')  # Default to localhost for security
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    logger.info(f"Starting Pi Air Quality Monitor on {host}:{port} (debug={debug_mode})")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")
    
    # Log sensor status
    if air_quality_sensor:
        logger.info("PMS7003 air quality sensor is active")
    else:
        logger.info("PMS7003 air quality sensor not available")
    
    if os.environ.get('LOG_LEVEL') == 'DEBUG':
        logger.debug("Debug logging enabled")
    
    print(f"Starting server on {host}:{port} (debug={debug_mode})")
    print("To allow network access, set FLASK_HOST=0.0.0.0")
    
    # Use single-threaded mode on Raspberry Pi for better performance
    if platform.machine().startswith('arm'):
        app.run(host=host, port=port, debug=debug_mode, threaded=False)
    else:
        app.run(host=host, port=port, debug=debug_mode)