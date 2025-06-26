#!/bin/bash
# Install script for Air Quality Monitor service

echo "Installing Air Quality Monitor service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Update service file with current user and paths
CURRENT_USER=$(logname)
CURRENT_DIR=$(pwd)

# Create service file from template
sed -e "s|User=pi|User=$CURRENT_USER|g" \
    -e "s|Group=pi|Group=$CURRENT_USER|g" \
    -e "s|/home/pi/pi_air|$CURRENT_DIR|g" \
    air-quality-monitor.service > /tmp/air-quality-monitor.service

# Copy service file
cp /tmp/air-quality-monitor.service /etc/systemd/system/

# Create log directory
mkdir -p /var/log
touch /var/log/air_quality_monitor.log
chown $CURRENT_USER:$CURRENT_USER /var/log/air_quality_monitor.log

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable air-quality-monitor.service

echo "Service installed successfully!"
echo ""
echo "To start the service now:"
echo "  sudo systemctl start air-quality-monitor"
echo ""
echo "To check service status:"
echo "  sudo systemctl status air-quality-monitor"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u air-quality-monitor -f"