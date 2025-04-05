# nutetra Hydroponic Automation System

The nutetra Hydroponic Automation System is a web-based application designed to monitor and control hydroponic systems. It provides real-time monitoring of pH, EC, temperature, and automated dosing to maintain optimal growing conditions.

![nutetra Dashboard](web/static/img/dashboard-preview.png)

## Features

- Real-time monitoring of pH, EC, and temperature sensors
- Automated dosing of pH adjusters and nutrients
- Manual pump controls for maintenance
- Customizable dosing schedules and settings
- Visual alerts and system status monitoring
- Mobile-friendly responsive web interface

## Hardware Requirements

- Raspberry Pi 5 (recommended) or compatible single-board computer
- pH sensor
- EC (Electrical Conductivity) sensor
- Temperature sensor
- Peristaltic pumps for dosing
- Main circulation pump

## Installation

### Easy Installation (Recommended)

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/nutetra.git
   cd nutetra
   ```

2. Run the installation script:
   ```
   sudo bash install.sh
   ```

3. Follow the prompts to complete installation. The script will:
   - Install system dependencies
   - Set up Python virtual environment
   - Install Python dependencies
   - Configure the system to start automatically on boot
   - Optionally set up Chromium in kiosk mode

4. After installation, the web interface will be accessible at:
   ```
   http://localhost:5000
   ```

### Manual Installation

If you prefer to install manually:

1. Install system dependencies:
   ```
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv chromium-browser
   ```

2. Create a Python virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Start the application:
   ```
   python web/start.py
   ```

## Usage

### Web Interface

Access the web interface at `http://localhost:5000` or the IP address of your device.

The main dashboard provides:
- Current pH, EC, and temperature readings with status indicators
- Pump status display
- System status and alerts

### Pages

- **Dashboard**: Main monitoring view
- **Dosing Settings**: Configure target values and dosing parameters
- **Pump Control**: Manually control pumps for maintenance
- **Alerts**: View and manage system alerts
- **Logs**: Review system logs and data history
- **System Settings**: Configure system-wide settings

## Configuration

All configuration is done through the web interface. Key settings:

- **Target Values**: Set desired pH and EC levels, with tolerance ranges
- **Dosing Schedule**: Configure when and how often the system checks and adjusts levels
- **Pump Calibration**: Set flow rates for accurate dosing
- **Dosing Limits**: Set safety limits for chemical additions

## Development

To run the application in development mode:

```
python web/start.py --debug
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses [Flask](https://flask.palletsprojects.com/) for the web framework
- Real-time updates with [Socket.IO](https://socket.io/)
- Charts powered by [Chart.js](https://www.chartjs.org/)

