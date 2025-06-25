#!/bin/bash
# Setup script for Raspberry Pi Zero 2 W

echo "Setting up Pi Air Monitor on Raspberry Pi..."

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
echo "Installing Python and system dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git

# Clone or update repository (if using git)
if [ -d "/home/pi/pi_air" ]; then
    echo "Updating existing installation..."
    cd /home/pi/pi_air
    git pull
else
    echo "Cloning repository..."
    cd /home/pi
    # Replace with your actual repository URL
    git clone https://github.com/andrewrweber/pi_air.git
    cd pi_air
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install packages
echo "Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy systemd service file
echo "Installing systemd service..."
sudo cp pimonitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pimonitor.service

# Start the service
echo "Starting Pi Monitor service..."
sudo systemctl start pimonitor.service

# Show status
echo "Setup complete! Service status:"
sudo systemctl status pimonitor.service

echo ""
echo "Access the monitor at: http://$(hostname -I | awk '{print $1}'):5000"
echo "To view logs: sudo journalctl -u pimonitor.service -f"