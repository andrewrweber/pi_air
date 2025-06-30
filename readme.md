# Pi Air Monitor

A comprehensive Raspberry Pi monitoring system with real-time system metrics and air quality monitoring using the PMS7003 sensor.

## 🚀 Features

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
- **"Lowest Air Quality (24h)"** card showing worst readings with timestamps
- **Historical air quality data** with multiple time ranges (1h, 6h, 24h)
- **Air quality forecasting** with hourly predictions and daily summaries
- **Today/Tomorrow forecast cards** with timezone-aware date handling
- **Persistent data storage** in SQLite database with automatic cleanup
- **Automatic sensor reconnection** on connection failures

### Modern Web Interface
- **📱 Mobile-first responsive design** optimized for all screen sizes
- **🎨 Clean modular architecture** with organized JavaScript modules
- **📊 Interactive charts** with touch gestures and time range selection
- **🌍 Proper timezone handling** (UTC to Pacific Time conversion)
- **🎯 Touch-friendly controls** with enhanced mobile UX
- **⚡ Real-time updates** with configurable refresh intervals
- **🎨 AQI color coding** for instant air quality assessment

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
- Create systemd services with automatic user/path detection
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
python -c "from src.database import init_database; init_database()"
```

4. Install systemd services (automatically detects user and paths):
```bash
sudo chmod +x scripts/install_service.sh
sudo ./scripts/install_service.sh
```

The installation script automatically detects:
- Your current username (works with any user, not just 'pi')
- Project directory location
- User's primary group
- Virtual environment path

This ensures the services work regardless of your username or installation directory.

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

## 📡 API Endpoints

### Core Endpoints
- `GET /` - Web dashboard interface
- `GET /api/system` - Complete system information (JSON)
- `GET /api/stats` - Real-time stats (CPU, memory, temperature)

### Air Quality Endpoints
- `GET /api/air-quality-latest` - Latest air quality sensor reading
- `GET /api/air-quality-worst-24h` - Worst air quality reading from last 24h
- `GET /api/air-quality-history?range={1h|6h|24h}` - Historical air quality data
- `GET /api/air-quality-forecast?hours={12|24|48|72}` - Hourly air quality forecast
- `GET /api/air-quality-forecast-summary?days={1|2|3}` - Daily forecast summaries

### System History Endpoints
- `GET /api/temperature-history` - CPU temperature history data
- `GET /api/system-history` - Historical system metrics (24h)

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
cd /path/to/your/pi_air  # Or wherever you installed the project
git pull origin main
```

4. Restart services if needed:
```bash
sudo systemctl restart pimonitor.service
sudo systemctl restart air-quality-monitor.service
```

## 🧪 Testing

The project includes comprehensive test coverage for both backend and frontend components.

### Quick Test Commands

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all backend tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m api           # API tests only
pytest -m database      # Database tests only
pytest -m "not hardware"  # Skip hardware-specific tests

# Run with coverage
pytest --cov=src --cov-report=html
```

### Frontend Tests

Open the frontend test runner in your browser:
```bash
# Start local server (optional)
python -m http.server 8000

# Open in browser
open http://localhost:8000/tests/frontend/test_runner.html
```

### Test Categories

- **Unit Tests** (`@pytest.mark.unit`) - Individual component testing
- **Integration Tests** (`@pytest.mark.integration`) - Component interaction testing
- **API Tests** (`@pytest.mark.api`) - Flask endpoint testing
- **Database Tests** (`@pytest.mark.database`) - Database operation testing
- **Frontend Tests** - JavaScript module testing
- **Hardware Tests** (`@pytest.mark.hardware`) - Raspberry Pi specific tests

Tests are well-documented with comprehensive coverage of all major functionality.

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

## 🏗️ Architecture

### Frontend (Modular JavaScript)
- **config.js** - Centralized configuration and constants
- **utils.js** - Shared utility functions with timezone management
- **charts.js** - Chart management with ChartManager class
- **hardware.js** - Hardware monitoring functionality
- **air-quality.js** - Air quality monitoring and display
- **forecast.js** - Air quality forecasting with timezone-aware date handling
- **app.js** - Main application controller

### Backend (Python Flask)
- **app.py** - Flask web application and API routes
- **air_quality_monitor.py** - Air quality monitoring service
- **pms7003.py** - PMS7003 sensor driver
- **database.py** - Database operations and models
- **logging_config.py** - Logging configuration
- **services/forecast_service.py** - Air quality forecast integration

## 📁 Project Structure

```
pi_air/
├── src/                           # Backend Python modules
│   ├── app.py                    # Flask web application
│   ├── air_quality_monitor.py    # Air quality monitoring service
│   ├── pms7003.py               # PMS7003 sensor driver
│   ├── database.py              # Database operations
│   ├── logging_config.py        # Logging configuration
│   ├── services/
│   │   └── forecast_service.py   # Air quality forecast integration
│   └── utils/
│       └── timestamp_utils.py    # Timezone and timestamp utilities
├── static/
│   ├── js/                      # Frontend JavaScript modules
│   │   ├── config.js           # Configuration and constants
│   │   ├── utils.js            # Utility functions with timezone management
│   │   ├── charts.js           # Chart management
│   │   ├── hardware.js         # Hardware monitoring
│   │   ├── air-quality.js      # Air quality functionality
│   │   ├── forecast.js         # Air quality forecasting
│   │   └── app.js              # Main application controller
│   └── style.css               # Dashboard styling
├── templates/
│   └── index.html              # Web dashboard template
├── tests/                      # Comprehensive test suite
│   ├── conftest.py            # Test configuration and fixtures
│   ├── test_database.py       # Database tests
│   ├── test_api_routes.py     # API endpoint tests
│   ├── test_forecast_service.py # Forecast service tests
│   ├── test_hardware_monitoring.py # Hardware tests
│   ├── test_frontend_forecast.html # Frontend forecast tests
│   └── frontend/              # Frontend JavaScript tests
├── scripts/
│   ├── setup_pi.sh           # Automated setup script
│   └── install_service.sh    # Service installation
├── systemd/                   # Service templates
├── data/                      # Database storage
├── requirements.txt          # Python dependencies
├── pytest.ini              # Test configuration
├── CLAUDE.md              # Project documentation for Claude Code
└── README.md              # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest` and frontend tests)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Create a Pull Request

## 🧪 Quality Assurance

- **80%+ test coverage** with comprehensive backend and frontend tests
- **Mobile-first responsive design** tested across devices
- **API validation** with proper error handling
- **Database integrity** with automatic cleanup and migrations
- **Performance optimization** for Raspberry Pi Zero 2 W

## License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with Flask and psutil
- Charts powered by Chart.js
- Designed for Raspberry Pi Zero 2 W
- Air quality calculations based on EPA AQI standards
- Mobile UX optimized for touch interfaces
- Comprehensive testing with pytest framework