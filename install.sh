#!/bin/bash
# nutetra Hydroponic System Installation Script
# This script installs and configures the nutetra web application to start automatically on boot

set -e # Exit on error

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}nutetra Hydroponic System Installation${NC}"
echo -e "${GREEN}=======================================${NC}"

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (use sudo).${NC}"
  exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Create log directory
mkdir -p logs
touch logs/install.log
LOGFILE="$SCRIPT_DIR/logs/install.log"

# Log function
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

# Install dependencies
install_dependencies() {
  log "Installing system dependencies..."
  apt-get update
  apt-get install -y python3 python3-pip python3-venv chromium-browser

  log "Creating Python virtual environment..."
  python3 -m venv venv
  source venv/bin/activate

  log "Installing Python dependencies..."
  pip install --upgrade pip
  pip install -r requirements.txt

  log "Dependencies installed successfully."
}

# Create necessary directories
create_directories() {
  log "Creating necessary directories..."
  mkdir -p logs
  mkdir -p settings
  mkdir -p data/history
  
  log "Setting permissions..."
  # Set owner to the user who will run the application
  chown -R $SUDO_USER:$SUDO_USER "$SCRIPT_DIR"
  
  log "Directories created successfully."
}

# Create systemd service for auto-start
create_systemd_service() {
  log "Creating systemd service..."
  
  # Create nutetra service file
  cat > /etc/systemd/system/nutetra.service << EOF
[Unit]
Description=nutetra Hydroponic System
After=network.target

[Service]
User=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python web/start.py --no-setup
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

  # Enable and start the service
  systemctl daemon-reload
  systemctl enable nutetra.service
  
  log "Systemd service created successfully."
}

# Setup Chromium kiosk mode (optional)
setup_kiosk_mode() {
  log "Setting up Chromium kiosk mode..."
  
  # Create autostart directory if it doesn't exist
  mkdir -p /home/$SUDO_USER/.config/autostart
  
  # Create desktop entry for Chromium kiosk mode
  cat > /home/$SUDO_USER/.config/autostart/nutetra-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=nutetra Kiosk
Exec=chromium-browser --kiosk --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/dev/null http://localhost:5000
X-GNOME-Autostart-enabled=true
EOF

  # Set proper ownership
  chown -R $SUDO_USER:$SUDO_USER /home/$SUDO_USER/.config/autostart
  
  log "Kiosk mode setup successfully."
}

# Main installation process
main() {
  echo -e "${YELLOW}Starting installation...${NC}"
  log "Beginning nutetra installation"
  
  # Install dependencies
  install_dependencies
  
  # Create directories
  create_directories
  
  # Create systemd service
  create_systemd_service
  
  # Ask about kiosk mode
  echo -e "${YELLOW}Do you want to set up Chromium kiosk mode? (y/n)${NC}"
  read -r answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    setup_kiosk_mode
  fi
  
  # Start the service
  echo -e "${YELLOW}Starting nutetra service...${NC}"
  systemctl start nutetra.service
  
  echo -e "${GREEN}Installation completed successfully!${NC}"
  echo -e "${GREEN}nutetra is running at: http://localhost:5000${NC}"
  log "Installation completed successfully"
}

# Run the main installation process
main 