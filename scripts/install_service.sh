#!/bin/bash
# Install script for Pi Air Monitor services

echo "Installing Pi Air Monitor services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Automatically detect current user and paths
# Use SUDO_USER if available, otherwise fall back to logname or current user
if [ -n "$SUDO_USER" ]; then
    CURRENT_USER=$SUDO_USER
elif command -v logname >/dev/null 2>&1; then
    CURRENT_USER=$(logname)
else
    CURRENT_USER=$(whoami)
fi

# Get the primary group for the user
CURRENT_GROUP=$(id -gn "$CURRENT_USER")

# Determine the project directory (should contain systemd folder)
CURRENT_DIR=$(pwd)
if [ -d "$CURRENT_DIR/systemd" ]; then
    PROJECT_DIR="$CURRENT_DIR"
elif [ -d "$(dirname "$CURRENT_DIR")/systemd" ]; then
    PROJECT_DIR="$(dirname "$CURRENT_DIR")"
else
    echo "Error: Cannot find systemd directory. Please run from the pi_air project directory."
    exit 1
fi

# Convert to absolute path
PROJECT_DIR=$(readlink -f "$PROJECT_DIR")

echo "Detected configuration:"
echo "  User: $CURRENT_USER"
echo "  Group: $CURRENT_GROUP" 
echo "  Project directory: $PROJECT_DIR"
echo

# Verify the virtual environment exists
if [ ! -f "$PROJECT_DIR/venv/bin/python" ]; then
    echo "Warning: Virtual environment not found at $PROJECT_DIR/venv/"
    echo "Please ensure you have created the virtual environment:"
    echo "  cd $PROJECT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Process both service files
for service in "pimonitor" "air-quality-monitor"; do
    echo "Installing $service.service..."
    
    if [ ! -f "$PROJECT_DIR/systemd/$service.service" ]; then
        echo "Error: $PROJECT_DIR/systemd/$service.service not found"
        exit 1
    fi
    
    # Replace template variables with actual values
    sed -e "s|{{USER}}|$CURRENT_USER|g" \
        -e "s|{{GROUP}}|$CURRENT_GROUP|g" \
        -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
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