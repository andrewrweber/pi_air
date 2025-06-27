# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application designed for monitoring Raspberry Pi system resources. It provides a real-time dashboard with system metrics and a RESTful API for accessing this data programmatically.

## Development Commands

### Setup and Installation
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Development mode (debug disabled by default for security)
python src/app.py

# With environment variables for production
FLASK_HOST=0.0.0.0 FLASK_PORT=5000 python src/app.py

# Enable debug mode (development only)
FLASK_DEBUG=true python src/app.py

# The server runs on http://127.0.0.1:5000 by default (localhost only)
```

### Git Workflow
```bash
# Typical workflow for updates
git add .
git commit -m "Your commit message"
git push origin main

# On Raspberry Pi to pull updates (from /home/weber/pi_air)
cd /home/weber/pi_air
git pull origin main

# If running as systemd service, restart after pulling
sudo systemctl restart pimonitor.service
sudo systemctl restart air-quality-monitor.service
```

### Systemd Service Setup
```bash
# Enable auto-start services on boot
sudo systemctl enable pimonitor.service
sudo systemctl enable air-quality-monitor.service

# Start services immediately
sudo systemctl start pimonitor.service
sudo systemctl start air-quality-monitor.service

# Check service status
sudo systemctl status pimonitor.service
sudo systemctl status air-quality-monitor.service

# View service logs
sudo journalctl -u pimonitor.service -f
sudo journalctl -u air-quality-monitor.service -f
```

## Architecture Overview

### Core Components

1. **Flask Application (src/app.py)**
   - Main entry point with three routes:
     - `/` - Serves the web dashboard
     - `/api/system` - Returns complete system information as JSON
     - `/api/stats` - Returns real-time stats (CPU, memory, temperature)
   - Uses psutil for cross-platform system monitoring
   - Raspberry Pi specific temperature monitoring via vcgencmd

2. **Frontend Structure**
   - **templates/index.html**: Single-page dashboard with auto-updating stats
   - **static/style.css**: Responsive CSS with Raspberry Pi themed colors
   - Updates every 2 seconds via JavaScript fetch to `/api/stats`

3. **Key Design Patterns**
   - RESTful API design for system data access
   - Real-time updates using client-side polling
   - Responsive card-based UI layout
   - Error handling for Raspberry Pi specific features

### Raspberry Pi Specific Features

The application includes Raspberry Pi specific functionality:
- CPU temperature monitoring using `vcgencmd measure_temp` in src/app.py
- Graceful fallback when vcgencmd is not available (shows "N/A")

### Data Flow

1. Client requests dashboard → Flask serves index.html
2. JavaScript initiates periodic fetch to `/api/stats`
3. Flask gathers system metrics via psutil
4. Data returned as JSON and displayed in UI
5. Process repeats every 2 seconds

## Deployment

### Raspberry Pi Setup

The application is designed to run on Raspberry Pi with the user directory at `/home/weber/pi_air`.

**Prerequisites:**
- Python 3.7+
- PMS7003 air quality sensor (connected via serial)
- Virtual environment setup

**Installation paths:**
- Project directory: `/home/weber/pi_air`
- Virtual environment: `/home/weber/pi_air/venv`
- Service user: `weber`

### Systemd Services

Two systemd services handle automatic startup:

1. **pimonitor.service** - Flask web application
2. **air-quality-monitor.service** - PMS7003 sensor data collection

Service files are located in `/etc/systemd/system/` and configured to:
- Start automatically on boot
- Restart on failure
- Run as user `weber`
- Log to systemd journal

## Important Considerations

- The application runs with debug=False by default for security
- Binds to 127.0.0.1:5000 by default (localhost only) - use FLASK_HOST=0.0.0.0 for network access
- No authentication implemented - suitable for trusted networks only
- Virtual environment (venv/) is gitignored
- Uses subprocess instead of os.popen for better security when reading CPU temperature
- Environment variables for configuration:
  - FLASK_DEBUG: 'true' to enable debug mode (development only)
  - FLASK_HOST: IP to bind to (default: 127.0.0.1)
  - FLASK_PORT: Port number (default: 5000)