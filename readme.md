# Pi Air Monitor

A comprehensive Raspberry Pi monitoring system with real-time system metrics and air quality monitoring using the PMS7003 sensor.

## Features

### System Monitoring
- **Real-time CPU monitoring** - Usage percentage and temperature tracking
- **Memory usage** statistics with detailed breakdowns
- **Disk usage** visualization with progress bars for all mounted drives
- **Network information** display showing all interfaces and IP addresses
- **System information** including hostname, platform, architecture, and uptime
- **Historical data** with 24-hour graphs for all system metrics
- **Temperature history** with both real-time (10 min) and database (24h) views

### Air Quality Monitoring
- **Real-time air quality measurements** using PMS7003 sensor
- **Air Quality Index (AQI)** calculation and display with color-coded levels
- **Particle concentration monitoring** - PM1.0, PM2.5, and PM10 measurements
- **Historical air quality data** with 24-hour charts at 15-minute intervals
- **Persistent data storage** in SQLite database
- **Automatic sensor reconnection** on connection failures

### Web Interface
- **Responsive design** optimized for desktop and mobile devices
- **Tabbed interface** with Air Quality as the default view
- **Auto-updating dashboard** with configurable refresh intervals
- **Interactive charts** using Chart.js for data visualization
- **Dark theme** with Raspberry Pi inspired colors

## Prerequisites

- Raspberry Pi Zero 2 W (or any Raspberry Pi model)
- Python 3.7 or higher
- Git
- PMS7003 air quality sensor (optional, for air quality monitoring)

## Hardware Setup (for Air Quality Monitoring)

Connect the PMS7003 sensor to your Raspberry Pi:
- VCC → 5V (Pin 2 or 4)
- GND → Ground (Pin 6, 9, 14, 20, 25, 30, 34, or 39)
- TX → GPIO15/RXD (Pin 10)
- RX → GPIO14/TXD (Pin 8) (optional, for sending commands)

## Installation

### Quick Setup

1. Clone the repository on your Raspberry Pi:
```bash
git clone https://github.com/andrewrweber/pi_air.git
cd pi_air
```

2. Run the setup script:
```bash
chmod +x scripts/setup_pi.sh
./scripts/setup_pi.sh
```

This script will:
- Create a Python virtual environment
- Install all dependencies
- Set up the SQLite database
- Create systemd services
- Configure services to start on boot

### Manual Setup

If you prefer to set up manually:

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python -c "from src.database import init_db; init_db()"
```

4. Install systemd services:
```bash
sudo chmod +x scripts/install_service.sh
sudo ./scripts/install_service.sh
```

## Usage

### Running Services

Start the services:
```bash
sudo systemctl start pimonitor.service
sudo systemctl start air-quality-monitor.service
```

Check service status:
```bash
sudo systemctl status pimonitor.service
sudo systemctl status air-quality-monitor.service
```

View logs:
```bash
sudo journalctl -u pimonitor.service -f
sudo journalctl -u air-quality-monitor.service -f
```

### Accessing the Web Interface

1. Find your Pi's IP address:
```bash
hostname -I
```

2. Open a browser and navigate to:
```
http://YOUR_PI_IP_ADDRESS:5000
```

## API Endpoints

- `GET /` - Web dashboard interface
- `GET /api/system` - Complete system information (JSON)
- `GET /api/stats` - Real-time stats (CPU, memory, temperature, current air quality)
- `GET /api/temperature-history` - CPU temperature history data
- `GET /api/system-history` - Historical system metrics (24h)
- `GET /api/air-quality-latest` - Latest air quality sensor reading
- `GET /api/air-quality-history` - Historical air quality data (24h)

## Configuration

### Environment Variables

The Flask app supports the following environment variables:
- `FLASK_DEBUG` - Set to 'true' for debug mode (development only)
- `FLASK_HOST` - IP address to bind to (default: 127.0.0.1)
- `FLASK_PORT` - Port number (default: 5000)

Example:
```bash
FLASK_HOST=0.0.0.0 FLASK_PORT=8080 python src/app.py
```

### Database Location

The SQLite database is stored at `data/monitoring.db`. The database is automatically created on first run and includes tables for:
- System metrics (CPU, memory, disk usage, temperature)
- Air quality readings (PM values, AQI)

## Development Workflow

1. Make changes on your development machine
2. Commit and push to GitHub:
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

3. Pull changes on your Pi:
```bash
cd ~/pi_air
git pull origin main
```

4. Restart services if needed:
```bash
sudo systemctl restart pimonitor.service
sudo systemctl restart air-quality-monitor.service
```

## Testing

Run the PMS7003 sensor test:
```bash
cd ~/pi_air
source venv/bin/activate
python tests/test_pms_simple.py
```

## Troubleshooting

### Common Issues

1. **Can't access web interface from other devices**
   - Ensure the service is running with `FLASK_HOST=0.0.0.0`
   - Check firewall settings: `sudo ufw allow 5000`

2. **Temperature shows N/A**
   - The `vcgencmd` command is Raspberry Pi specific
   - Ensure you're running on actual Raspberry Pi hardware

3. **Air quality data not updating**
   - Check sensor connection: TX → GPIO15/RXD (Pin 10)
   - Verify serial port permissions: `sudo usermod -a -G dialout $USER`
   - Check service logs: `sudo journalctl -u air-quality-monitor.service -f`

4. **High CPU usage**
   - Normal for Pi Zero 2 W during data collection
   - Consider increasing update intervals in the web interface

### Database Maintenance

View database statistics:
```bash
sqlite3 data/monitoring.db "SELECT COUNT(*) FROM air_quality_readings;"
```

The database includes automatic cleanup to prevent unlimited growth.

## Project Structure

```
pi_air/
├── src/
│   ├── app.py                    # Flask web application
│   ├── air_quality_monitor.py    # Air quality monitoring service
│   ├── pms7003.py               # PMS7003 sensor driver
│   ├── database.py              # Database operations
│   └── logging_config.py        # Logging configuration
├── templates/
│   └── index.html               # Web dashboard
├── static/
│   └── style.css               # Dashboard styling
├── services/
│   ├── pimonitor.service       # System monitor service
│   └── air-quality-monitor.service  # Air quality service
├── scripts/
│   ├── setup_pi.sh            # Automated setup script
│   └── install_service.sh     # Service installation
├── tests/
│   └── test_pms_simple.py     # Sensor tests
├── data/
│   └── monitoring.db          # SQLite database (auto-created)
├── requirements.txt           # Python dependencies
├── CLAUDE.md                 # Project documentation for Claude Code
└── README.md                 # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with Flask and psutil
- Charts powered by Chart.js
- Designed for Raspberry Pi Zero 2 W
- Air quality calculations based on EPA AQI standards