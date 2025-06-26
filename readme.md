# Raspberry Pi System Monitor

A lightweight Flask web application that displays real-time system information from your Raspberry Pi.

## Features

- **Real-time monitoring** of CPU usage and temperature
- **Memory usage** statistics
- **Disk usage** visualization with progress bars
- **Network information** display
- **System information** including hostname, platform, and uptime
- **RESTful API** endpoints for system data
- **Responsive design** that works on desktop and mobile

## Prerequisites

- Raspberry Pi Zero 2 W (or any Raspberry Pi)
- Python 3.7 or higher
- Git

## Setup Instructions

### On Your Development Machine

1. Create a new directory and initialize git:
```bash
mkdir raspberry-pi-server
cd raspberry-pi-server
git init
```

2. Create the project structure:
```bash
mkdir templates static
```

3. Copy all the provided files into their respective locations:
   - `src/app.py` - Main Flask application
   - `src/air_quality_monitor.py` - Air quality sensor monitoring service
   - `src/pms7003.py` - PMS7003 sensor driver
   - `src/database.py` - SQLite database interface
   - `src/logging_config.py` - Logging configuration
   - `templates/index.html` - Web dashboard template
   - `static/style.css` - Dashboard styling
   - `services/pimonitor.service` - Systemd service for web app
   - `services/air-quality-monitor.service` - Systemd service for sensor
   - `scripts/setup_pi.sh` - Raspberry Pi setup script
   - `scripts/install_service.sh` - Service installation script
   - `tests/test_pms_simple.py` - Simple sensor test
   - `requirements.txt` - Python dependencies
   - `.gitignore` - Git ignore rules
   - This `README.md` - Project documentation

4. Create a GitHub repository and push your code:
```bash
git add .
git commit -m "Initial commit: Flask system monitor"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### On Your Raspberry Pi

1. SSH into your Raspberry Pi:
```bash
ssh pi@YOUR_PI_IP_ADDRESS
```

2. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

3. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the server:
```bash
python src/app.py
```

6. Access the web interface:
   - Open a browser on any device on your network
   - Navigate to `http://YOUR_PI_IP_ADDRESS:5000`

## Running as a Service (Optional)

To run the server automatically on boot:

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/pimonitor.service
```

2. Add the following content:
```ini
[Unit]
Description=Raspberry Pi System Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/YOUR_REPO_NAME
Environment=PATH=/home/pi/YOUR_REPO_NAME/venv/bin
ExecStart=/home/pi/YOUR_REPO_NAME/venv/bin/python src/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl enable pimonitor.service
sudo systemctl start pimonitor.service
```

## API Endpoints

- `GET /` - Web interface
- `GET /api/system` - Complete system information (JSON)
- `GET /api/stats` - Real-time stats (CPU, memory, temperature)

## Customization

- Modify `src/app.py` to add more system metrics
- Edit `templates/index.html` to change the layout
- Update `static/style.css` to customize the appearance
- Add new API endpoints for specific monitoring needs

## Troubleshooting

- **Can't access from other devices**: Make sure the Pi's firewall allows port 5000
- **Temperature shows N/A**: The `vcgencmd` command is Raspberry Pi specific
- **High CPU usage**: Increase the update interval in `index.html`

## Development Workflow

1. Make changes on your laptop using Claude Code
2. Commit and push to GitHub
3. Pull changes on your Pi: `git pull origin main`
4. Restart the service: `sudo systemctl restart pimonitor.service`

## License

MIT License