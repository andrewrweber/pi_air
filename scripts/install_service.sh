#!/bin/bash
# Install script for Pi Air Monitor services

echo "Installing Pi Air Monitor services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Update service file with current user and paths
# Use SUDO_USER if available, otherwise fall back to logname or current user
if [ -n "$SUDO_USER" ]; then
    CURRENT_USER=$SUDO_USER
elif command -v logname >/dev/null 2>&1; then
    CURRENT_USER=$(logname)
else
    CURRENT_USER=$(whoami)
fi

CURRENT_DIR=$(pwd)

# Create service files from templates
# Use the systemd directory in the project
PARENT_DIR=$(dirname "$CURRENT_DIR")

# Process both service files
for service in "pimonitor" "air-quality-monitor"; do
    echo "Installing $service.service..."
    sed -e "s|User=weber|User=$CURRENT_USER|g" \
        -e "s|Group=weber|Group=$CURRENT_USER|g" \
        -e "s|/home/weber/pi_air|$PARENT_DIR|g" \
        $PARENT_DIR/systemd/$service.service > /tmp/$service.service
    
    # Copy service file
    cp /tmp/$service.service /etc/systemd/system/
    
    # Clean up temp file
    rm /tmp/$service.service
done

# Create log directory
mkdir -p /var/log
touch /var/log/air_quality_monitor.log
chown $CURRENT_USER:$CURRENT_USER /var/log/air_quality_monitor.log

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable pimonitor.service
systemctl enable air-quality-monitor.service

echo "Services installed successfully!"
echo ""
echo "To start the services now:"
echo "  sudo systemctl start pimonitor.service"
echo "  sudo systemctl start air-quality-monitor.service"
echo ""
echo "To check service status:"
echo "  sudo systemctl status pimonitor.service"
echo "  sudo systemctl status air-quality-monitor.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u pimonitor.service -f"
echo "  sudo journalctl -u air-quality-monitor.service -f"