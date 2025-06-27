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
# Determine the project directory (should contain systemd folder)
if [ -d "$CURRENT_DIR/systemd" ]; then
    PROJECT_DIR="$CURRENT_DIR"
elif [ -d "$(dirname "$CURRENT_DIR")/systemd" ]; then
    PROJECT_DIR="$(dirname "$CURRENT_DIR")"
else
    echo "Error: Cannot find systemd directory. Please run from the pi_air project directory."
    exit 1
fi

echo "Using project directory: $PROJECT_DIR"

# Process both service files
for service in "pimonitor" "air-quality-monitor"; do
    echo "Installing $service.service..."
    
    if [ ! -f "$PROJECT_DIR/systemd/$service.service" ]; then
        echo "Error: $PROJECT_DIR/systemd/$service.service not found"
        exit 1
    fi
    
    sed -e "s|User=weber|User=$CURRENT_USER|g" \
        -e "s|Group=weber|Group=$CURRENT_USER|g" \
        -e "s|/home/weber/pi_air|$PROJECT_DIR|g" \
        "$PROJECT_DIR/systemd/$service.service" > /tmp/$service.service
    
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

# Unmask services (in case they were previously masked)
systemctl unmask pimonitor.service 2>/dev/null || true
systemctl unmask air-quality-monitor.service 2>/dev/null || true

# Stop and disable any existing services
systemctl stop pimonitor.service 2>/dev/null || true
systemctl stop air-quality-monitor.service 2>/dev/null || true
systemctl disable pimonitor.service 2>/dev/null || true
systemctl disable air-quality-monitor.service 2>/dev/null || true

# Reload systemd again after any changes
systemctl daemon-reload

# Enable and start services
systemctl enable pimonitor.service
systemctl enable air-quality-monitor.service
systemctl start pimonitor.service
systemctl start air-quality-monitor.service

echo "Services installed and started successfully!"
echo ""
echo "Service status:"
systemctl is-active pimonitor.service && echo "  ✓ pimonitor.service is running" || echo "  ✗ pimonitor.service failed to start"
systemctl is-active air-quality-monitor.service && echo "  ✓ air-quality-monitor.service is running" || echo "  ✗ air-quality-monitor.service failed to start"
echo ""
echo "To check service status:"
echo "  sudo systemctl status pimonitor.service"
echo "  sudo systemctl status air-quality-monitor.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u pimonitor.service -f"
echo "  sudo journalctl -u air-quality-monitor.service -f"