#!/bin/bash
# NuTetra Hydroponic System Installation Script
# This script sets up the NuTetra system as a service

# Exit on error
set -e

echo "NuTetra Hydroponic System Installation"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Determine script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Installing from directory: $SCRIPT_DIR"

# Create required directories
echo "Creating required directories..."
mkdir -p /NuTetra/logs
mkdir -p /NuTetra/data
mkdir -p /NuTetra/config
mkdir -p /NuTetra/exports
chmod -R 777 /NuTetra

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv /NuTetra/venv
source /NuTetra/venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r $SCRIPT_DIR/requirements.txt

# Copy application files
echo "Copying application files..."
rsync -av --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" $SCRIPT_DIR/ /NuTetra/app/

# Create systemd service file
echo "Creating systemd service..."
cat > /etc/systemd/system/nutetra.service << EOF
[Unit]
Description=NuTetra Hydroponic System
After=network.target

[Service]
ExecStart=/NuTetra/venv/bin/python /NuTetra/app/web/start.py
WorkingDirectory=/NuTetra/app
StandardOutput=journal
StandardError=journal
Restart=always
User=root
Group=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for web kiosk mode (optional)
echo "Creating kiosk mode service (optional)..."
cat > /etc/systemd/system/nutetra-kiosk.service << EOF
[Unit]
Description=NuTetra Kiosk Mode
After=nutetra.service
Requires=nutetra.service

[Service]
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium-browser --kiosk --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/dev/null http://localhost:5000
Restart=always
RestartSec=5
User=pi
Group=pi

[Install]
WantedBy=graphical.target
EOF

# Enable and start services
echo "Enabling and starting NuTetra service..."
systemctl daemon-reload
systemctl enable nutetra.service
systemctl start nutetra.service

echo "Installation complete!"
echo ""
echo "To start the kiosk mode (only on Raspberry Pi with desktop):"
echo "sudo systemctl enable nutetra-kiosk.service"
echo "sudo systemctl start nutetra-kiosk.service"
echo ""
echo "The web interface is available at: http://localhost:5000"
echo "Visit this URL from any device on your network using your Raspberry Pi's IP address"
echo ""
echo "Check logs with: sudo journalctl -u nutetra.service -f" 