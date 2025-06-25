from flask import Flask, render_template, jsonify
import psutil
import platform
import datetime
import os

app = Flask(__name__)

def get_size(bytes, suffix="B"):
    """Convert bytes to human readable format"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_system_info():
    """Gather system information"""
    info = {}
    
    # System info
    info['platform'] = platform.system()
    info['platform_release'] = platform.release()
    info['platform_version'] = platform.version()
    info['architecture'] = platform.machine()
    info['hostname'] = platform.node()
    info['processor'] = platform.processor()
    
    # Boot time
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.datetime.fromtimestamp(boot_time_timestamp)
    info['boot_time'] = f"{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"
    
    # CPU info
    info['physical_cores'] = psutil.cpu_count(logical=False)
    info['total_cores'] = psutil.cpu_count(logical=True)
    cpufreq = psutil.cpu_freq()
    info['cpu_freq_current'] = f"{cpufreq.current:.2f}Mhz"
    info['cpu_usage'] = f"{psutil.cpu_percent(interval=1)}%"
    
    # CPU temperature (Raspberry Pi specific)
    try:
        temp = os.popen("vcgencmd measure_temp").readline()
        info['cpu_temp'] = temp.replace("temp=", "").strip()
    except:
        info['cpu_temp'] = "N/A"
    
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
        except PermissionError:
            continue
    info['disk_info'] = disk_info
    
    # Network info
    network_info = []
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            if str(address.family) == 'AddressFamily.AF_INET':
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
    return render_template('index.html')

@app.route('/api/system')
def system_api():
    """API endpoint for system information"""
    return jsonify(get_system_info())

@app.route('/api/stats')
def stats_api():
    """API endpoint for real-time stats"""
    stats = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    # CPU temperature for Raspberry Pi
    try:
        temp = os.popen("vcgencmd measure_temp").readline()
        stats['cpu_temp'] = float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        stats['cpu_temp'] = None
    
    return jsonify(stats)

if __name__ == '__main__':
    # Run on all network interfaces so you can access from other devices
    app.run(host='0.0.0.0', port=5000, debug=True)