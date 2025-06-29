from flask import Flask, render_template, jsonify, request
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
from database import (get_latest_reading, get_hourly_averages_24h, get_15min_averages_24h, get_database_stats,
                     insert_system_reading, get_latest_system_reading, get_system_readings_last_24h, 
                     get_system_hourly_averages_24h, init_database, get_interval_averages, 
                     get_temperature_history_optimized, get_readings_last_24h)
from services.forecast_service import forecast_service
from config import config

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

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
    if platform.system() != 'Linux':
        logger.debug("Not on Linux system, skipping temperature reading")
        return None
        
    if not os.path.exists('/usr/bin/vcgencmd'):
        logger.warning("vcgencmd not found at /usr/bin/vcgencmd")
        return None
        
    try:
        # Use full path to vcgencmd for systemd service compatibility
        result = subprocess.run(
            ['/usr/bin/vcgencmd', 'measure_temp'], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        
        if result.returncode == 0:
            # Parse temperature from format: temp=45.6'C
            temp_str = result.stdout.strip()
            logger.debug(f"vcgencmd output: '{temp_str}'")
            temp_value = temp_str.split('=')[1].split("'")[0]
            return float(temp_value)
        else:
            logger.warning(f"vcgencmd failed with return code {result.returncode}: {result.stderr.strip()}")
            
    except subprocess.TimeoutExpired:
        logger.warning("vcgencmd command timed out")
    except subprocess.SubprocessError as e:
        logger.warning(f"vcgencmd subprocess error: {e}")
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse temperature from vcgencmd output: {e}")
    except FileNotFoundError:
        logger.warning("vcgencmd command not found")
    except Exception as e:
        logger.warning(f"Unexpected error reading temperature: {e}")
        
    return None

def sample_temperature_and_system_stats():
    """Background thread to sample CPU temperature and system stats every 5 seconds"""
    global latest_temperature
    last_db_write = 0
    db_write_interval = 30  # Write to database every 30 seconds
    
    logger.info("Starting temperature and system stats collection thread")
    
    while True:
        try:
            current_time = time.time()
            
            # Get system metrics
            temp = get_cpu_temperature()
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent
            
            # Always update real-time history, even if temp is None (for debugging)
            timestamp = datetime.datetime.now().isoformat()
            with temperature_lock:
                temperature_history.append((timestamp, temp))
                if temp is not None:
                    latest_temperature = temp
            
            # Log temperature collection for debugging
            if temp is not None:
                logger.debug(f"Temperature collected: {temp}°C at {timestamp}")
            else:
                logger.debug(f"Temperature collection failed at {timestamp}")
            
            # Write to database every 30 seconds (only if we have valid temperature)
            time_diff = current_time - last_db_write
            should_write_time = time_diff >= db_write_interval
            temp_valid = temp is not None
            
            if should_write_time:
                if temp_valid:
                    try:
                        insert_system_reading(
                            cpu_temp=temp,
                            cpu_usage=cpu_usage,
                            memory_usage=memory_usage,
                            disk_usage=disk_usage
                        )
                        logger.debug(f"Database write successful: temp={temp}°C, CPU={cpu_usage}%, mem={memory_usage}%")
                        last_db_write = current_time
                    except Exception as e:
                        logger.error(f"Database write failed: {e}")
                else:
                    logger.debug(f"Skipping database write: temperature is None")
                    # Still update last_db_write to avoid spam, but try again sooner
                    last_db_write = current_time - (db_write_interval // 2)
                    
        except Exception as e:
            logger.error(f"Error sampling system stats: {e}")
        time.sleep(5)  # Sample every 5 seconds for real-time display

# Start system monitoring thread
system_monitor_thread = threading.Thread(target=sample_temperature_and_system_stats, daemon=True)
system_monitor_thread.start()

def initialize_air_quality_sensor():
    """Initialize PMS7003 sensor if on Raspberry Pi"""
    global air_quality_sensor
    # Disabled - air quality monitoring is now handled by the separate service
    # The web app will read data from the database instead
    logger.info("Air quality data will be read from database (managed by air-quality-monitor service)")
    air_quality_sensor = None

# Initialize database and air quality sensor
init_database()
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
        
        # Add air quality data from database (preferred) or direct sensor
        air_data = get_latest_reading()
        if air_data:
            stats['air_quality'] = {
                'pm1_0': air_data['pm1_0'],
                'pm2_5': air_data['pm2_5'],
                'pm10': air_data['pm10'],
                'aqi': air_data['aqi'],
                'aqi_level': air_data['aqi_level'],
                'source': 'database'
            }
        elif air_quality_sensor:
            # Fallback to direct sensor reading if no database data
            sensor_data = air_quality_sensor.get_data()
            if sensor_data:
                stats['air_quality'] = {
                    'pm1_0': sensor_data['pm1_0'],
                    'pm2_5': sensor_data['pm2_5'],
                    'pm10': sensor_data['pm10'],
                    'aqi': sensor_data['aqi'],
                    'aqi_level': sensor_data['aqi_level'],
                    'source': 'sensor'
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
    """API endpoint for temperature history (both real-time and database)"""
    try:
        # Get real-time history for immediate display (last 10 minutes)
        with temperature_lock:
            real_time_history = [
                {'timestamp': ts, 'temperature': temp} 
                for ts, temp in temperature_history
                if temp is not None  # Filter out None values
            ]
        
        # If real-time history is empty, try to get recent data from database
        if not real_time_history:
            logger.warning("Real-time temperature history is empty, falling back to recent database data")
            recent_data = get_temperature_history_optimized(hours=0.5, max_points=60)  # Last 30 minutes, 60 points
            real_time_history = [
                {'timestamp': row['timestamp'], 'temperature': row['cpu_temp']}
                for row in recent_data
                if row['cpu_temp'] is not None
            ]
        
        # Get optimized database history for longer term trends (24 hours, max 100 points)
        db_history = get_temperature_history_optimized(hours=24, max_points=100)
        
        response_data = {
            'real_time_history': real_time_history,
            'database_history': db_history
        }
        
        logger.debug(f"Temperature API: real-time={len(real_time_history)} points, database={len(db_history)} points")
        
        response = jsonify(response_data)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error in temperature_history_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-history')
def system_history_api():
    """API endpoint for system metrics history"""
    try:
        # Get hourly averages for the chart
        hourly_data = get_system_hourly_averages_24h()
        
        # Get latest system reading
        latest_reading = get_latest_system_reading()
        
        # Log for debugging temperature issues
        temp_count = sum(1 for row in hourly_data if row.get('avg_cpu_temp') is not None)
        logger.debug(f"System history API: {len(hourly_data)} hourly records, {temp_count} with valid temperature")
        
        if hourly_data:
            logger.debug(f"Latest hourly record: {hourly_data[-1]}")
        
        response_data = {
            'hourly_averages': hourly_data,
            'latest_reading': latest_reading
        }
        
        response = jsonify(response_data)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error in system_history_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/air-quality-latest')
def air_quality_latest_api():
    """API endpoint for the latest single air quality reading"""
    try:
        # Get the actual latest reading (not averaged)
        latest_reading = get_latest_reading()
        
        response_data = {
            'latest_reading': latest_reading
        }
        
        response = jsonify(response_data)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error in air_quality_latest_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/air-quality-worst-24h')
def air_quality_worst_24h_api():
    """API endpoint for the worst air quality reading in the last 24 hours"""
    try:
        # Get all readings from last 24 hours
        readings_24h = get_readings_last_24h()
        
        if not readings_24h:
            response_data = {'worst_reading': None}
        else:
            # Find the reading with the highest AQI (worst air quality)
            worst_reading = max(readings_24h, key=lambda x: x['aqi'] if x['aqi'] is not None else 0)
            response_data = {'worst_reading': worst_reading}
        
        response = jsonify(response_data)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error in air_quality_worst_24h_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/air-quality-history')
def air_quality_history_api():
    """API endpoint for air quality history with configurable time range"""
    try:
        # Get time range from query parameter, default to 24h
        time_range = request.args.get('range', '24h')
        
        # Get interval averages based on time range
        if time_range == '1h':
            # 1 hour with 2-minute intervals
            interval_data = get_interval_averages(hours=1, interval_minutes=2)
        elif time_range == '6h':
            # 6 hours with 5-minute intervals
            interval_data = get_interval_averages(hours=6, interval_minutes=5)
        else:
            # Default: 24 hours with 15-minute intervals
            interval_data = get_15min_averages_24h()
        
        # Get database stats
        db_stats = get_database_stats()
        
        response_data = {
            'interval_averages': interval_data,
            'stats': db_stats,
            'time_range': time_range
        }
        
        response = jsonify(response_data)
        # Add explicit CORS headers for development
        if os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error in air_quality_history_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/air-quality-forecast')
def air_quality_forecast_api():
    """Get air quality forecast data"""
    try:
        # Get forecast hours parameter (default 72 hours = 3 days)
        hours = request.args.get('hours', '72')
        try:
            hours = int(hours)
            hours = max(1, min(hours, 120))  # Limit between 1 and 120 hours
        except ValueError:
            hours = 72
        
        logger.info(f"Fetching {hours}-hour air quality forecast")
        
        forecast_data = forecast_service.get_forecast(hours=hours)
        
        if not forecast_data:
            logger.warning("No forecast data available")
            return jsonify({
                'forecast': [],
                'hours': hours,
                'location': {
                    'name': config.get('location.name'),
                    'latitude': config.get('location.latitude'),
                    'longitude': config.get('location.longitude')
                },
                'provider': config.get_forecast_provider(),
                'message': 'No forecast data available'
            })
        
        # Convert forecast data for API response
        forecast_points = []
        for point in forecast_data:
            forecast_points.append({
                'time': point['forecast_for_time'],
                'pm1_0': point['pm1_0'],
                'pm2_5': point['pm2_5'],
                'pm10': point['pm10'],
                'carbon_monoxide': point['carbon_monoxide'],
                'nitrogen_dioxide': point['nitrogen_dioxide'],
                'sulphur_dioxide': point['sulphur_dioxide'],
                'ozone': point['ozone'],
                'aqi': point['aqi'],
                'aqi_level': point['aqi_level'],
                'provider': point['provider']
            })
        
        response_data = {
            'forecast': forecast_points,
            'hours': hours,
            'count': len(forecast_points),
            'location': {
                'name': config.get('location.name'),
                'latitude': config.get('location.latitude'),
                'longitude': config.get('location.longitude')
            },
            'provider': config.get_forecast_provider(),
            'forecast_time': forecast_data[0]['forecast_time'] if forecast_data else None
        }
        
        logger.info(f"Returning {len(forecast_points)} forecast points")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in air_quality_forecast_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/air-quality-forecast-summary')
def air_quality_forecast_summary_api():
    """Get summarized air quality forecast (daily averages)"""
    try:
        # Get forecast days parameter (default 3 days)
        days = request.args.get('days', '3')
        try:
            days = int(days)
            days = max(1, min(days, 5))  # Limit between 1 and 5 days
        except ValueError:
            days = 3
        
        logger.info(f"Fetching {days}-day air quality forecast summary")
        
        # Get full hourly forecast
        forecast_data = forecast_service.get_forecast(hours=days * 24)
        
        if not forecast_data:
            return jsonify({
                'forecast': [],
                'days': days,
                'location': {
                    'name': config.get('location.name'),
                    'latitude': config.get('location.latitude'),
                    'longitude': config.get('location.longitude')
                },
                'provider': config.get_forecast_provider(),
                'message': 'No forecast data available'
            })
        
        # Group by date and calculate daily summaries
        from datetime import datetime
        daily_summaries = {}
        
        for point in forecast_data:
            try:
                # Parse forecast time
                forecast_time = datetime.fromisoformat(point['forecast_for_time'].replace('Z', '+00:00'))
                date_key = forecast_time.date().isoformat()
                
                if date_key not in daily_summaries:
                    daily_summaries[date_key] = {
                        'date': date_key,
                        'pm2_5_values': [],
                        'pm10_values': [],
                        'aqi_values': [],
                        'hourly_count': 0
                    }
                
                # Collect values for averaging
                if point['pm2_5'] is not None:
                    daily_summaries[date_key]['pm2_5_values'].append(point['pm2_5'])
                if point['pm10'] is not None:
                    daily_summaries[date_key]['pm10_values'].append(point['pm10'])
                if point['aqi'] is not None:
                    daily_summaries[date_key]['aqi_values'].append(point['aqi'])
                
                daily_summaries[date_key]['hourly_count'] += 1
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing forecast point: {e}")
                continue
        
        # Calculate daily averages
        daily_forecast = []
        for date_key in sorted(daily_summaries.keys()):
            summary = daily_summaries[date_key]
            
            # Calculate averages
            pm2_5_avg = sum(summary['pm2_5_values']) / len(summary['pm2_5_values']) if summary['pm2_5_values'] else None
            pm10_avg = sum(summary['pm10_values']) / len(summary['pm10_values']) if summary['pm10_values'] else None
            aqi_avg = sum(summary['aqi_values']) / len(summary['aqi_values']) if summary['aqi_values'] else None
            
            # Calculate max AQI for the day (worst air quality)
            aqi_max = max(summary['aqi_values']) if summary['aqi_values'] else None
            
            # Determine AQI level from average
            aqi_level = None
            if aqi_avg is not None:
                if aqi_avg <= 50:
                    aqi_level = "Good"
                elif aqi_avg <= 100:
                    aqi_level = "Moderate"
                elif aqi_avg <= 150:
                    aqi_level = "Unhealthy for Sensitive Groups"
                elif aqi_avg <= 200:
                    aqi_level = "Unhealthy"
                elif aqi_avg <= 300:
                    aqi_level = "Very Unhealthy"
                else:
                    aqi_level = "Hazardous"
            
            daily_forecast.append({
                'date': date_key,
                'pm2_5_avg': round(pm2_5_avg, 1) if pm2_5_avg is not None else None,
                'pm10_avg': round(pm10_avg, 1) if pm10_avg is not None else None,
                'aqi_avg': round(aqi_avg) if aqi_avg is not None else None,
                'aqi_max': aqi_max,
                'aqi_level': aqi_level,
                'hourly_count': summary['hourly_count']
            })
        
        response_data = {
            'forecast': daily_forecast,
            'days': days,
            'count': len(daily_forecast),
            'location': {
                'name': config.get('location.name'),
                'latitude': config.get('location.latitude'),
                'longitude': config.get('location.longitude')
            },
            'provider': config.get_forecast_provider(),
            'forecast_time': forecast_data[0]['forecast_time'] if forecast_data else None
        }
        
        logger.info(f"Returning {len(daily_forecast)} daily forecast summaries")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in air_quality_forecast_summary_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast-cache-stats')
def forecast_cache_stats_api():
    """Get forecast cache statistics"""
    try:
        stats = forecast_service.get_cache_stats()
        
        response_data = {
            'cache_stats': stats,
            'cache_enabled': config.is_forecast_enabled(),
            'cache_hours': config.get_cache_hours(),
            'provider': config.get_forecast_provider()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in forecast_cache_stats_api: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast-cache-clear', methods=['POST'])
def forecast_cache_clear_api():
    """Clear forecast cache"""
    try:
        forecast_service.clear_cache()
        
        return jsonify({
            'message': 'Forecast cache cleared successfully',
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in forecast_cache_clear_api: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Configuration should be environment-based
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')  # Default to localhost for security
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    logger.info(f"Starting Pi Air Quality Monitor on {host}:{port} (debug={debug_mode})")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")
    
    # Log data source status
    logger.info("Data sources: SQLite database (monitoring.db)")
    logger.info("Air quality data managed by: air-quality-monitor.service")
    logger.info("System metrics managed by: Flask app background thread")
    
    if os.environ.get('LOG_LEVEL') == 'DEBUG':
        logger.debug("Debug logging enabled")
    
    print(f"Starting server on {host}:{port} (debug={debug_mode})")
    print("To allow network access, set FLASK_HOST=0.0.0.0")
    
    # Use single-threaded mode on Raspberry Pi for better performance
    if platform.machine().startswith('arm'):
        app.run(host=host, port=port, debug=debug_mode, threaded=False)
    else:
        app.run(host=host, port=port, debug=debug_mode)