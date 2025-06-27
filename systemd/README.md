# Systemd Service Configuration

This directory contains systemd service files for the Pi Air Monitor application.

## Service Files

- `pimonitor.service` - Flask web application
- `air-quality-monitor.service` - PMS7003 sensor data collection

## Installation

To install these services on your Raspberry Pi:

```bash
# Copy service files to systemd directory
sudo cp systemd/*.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable pimonitor.service
sudo systemctl enable air-quality-monitor.service

# Start services immediately
sudo systemctl start pimonitor.service
sudo systemctl start air-quality-monitor.service
```

## Management Commands

```bash
# Check service status
sudo systemctl status pimonitor.service
sudo systemctl status air-quality-monitor.service

# View service logs
sudo journalctl -u pimonitor.service -f
sudo journalctl -u air-quality-monitor.service -f

# Restart services (after code updates)
sudo systemctl restart pimonitor.service
sudo systemctl restart air-quality-monitor.service

# Stop services
sudo systemctl stop pimonitor.service
sudo systemctl stop air-quality-monitor.service

# Disable auto-start (if needed)
sudo systemctl disable pimonitor.service
sudo systemctl disable air-quality-monitor.service
```

## Configuration

The services are configured for:
- **User**: `weber`
- **Project Path**: `/home/weber/pi_air`
- **Virtual Environment**: `/home/weber/pi_air/venv`
- **Auto-restart**: On failure
- **Logging**: systemd journal

## Troubleshooting

If services fail to start:

1. Check logs: `sudo journalctl -u [service-name] --since "10 minutes ago"`
2. Verify permissions: `sudo chown -R weber:weber /home/weber/pi_air`
3. Check Python environment: `ls -la /home/weber/pi_air/venv/bin/python`
4. Verify dependencies: `source /home/weber/pi_air/venv/bin/activate && pip list`