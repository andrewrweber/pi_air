#!/bin/bash
# Setup script for Raspberry Pi (user-agnostic)

echo "Setting up Pi Air Monitor on Raspberry Pi..."

# Get current user's home directory
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)
PROJECT_NAME="pi_air"
PROJECT_DIR="$USER_HOME/$PROJECT_NAME"

echo "Setting up for user: $CURRENT_USER"
echo "Project directory: $PROJECT_DIR"

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
echo "Installing Python and system dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git

# Clone or update repository (if using git)
if [ -d "$PROJECT_DIR" ]; then
    echo "Updating existing installation..."
    cd "$PROJECT_DIR"
    git pull
else
    echo "Cloning repository..."
    cd "$USER_HOME"
    # Replace with your actual repository URL
    git clone https://github.com/andrewrweber/pi_air.git
    cd "$PROJECT_NAME"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install packages
echo "Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python -c "from src.database import init_database; init_database()"

# Install systemd services using the user-agnostic script
echo "Installing systemd services..."
sudo chmod +x scripts/install_service.sh
sudo ./scripts/install_service.sh

# Show status
echo "Setup complete! Service status:"
sudo systemctl status pimonitor.service
sudo systemctl status air-quality-monitor.service

echo ""
echo "Access the monitor at: http://$(hostname -I | awk '{print $1}'):5000"
echo "To view logs:"
echo "  sudo journalctl -u pimonitor.service -f"
echo "  sudo journalctl -u air-quality-monitor.service -f"