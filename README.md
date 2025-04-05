# NuTetra Hydroponic System

A comprehensive automation system for hydroponic growing, featuring pH and EC monitoring, automated nutrient dosing, and a web interface for control and monitoring.

## Features

- **Sensor Monitoring**: pH, EC/TDS, and temperature monitoring with Atlas Scientific sensors
- **Automated Dosing**: Precise dosing of pH adjusters and nutrients based on readings
- **Web Interface**: Browser-based control panel accessible from any device
- **Configurable Alerts**: Get notified when readings are outside acceptable ranges
- **Data Logging**: Track system performance over time
- **Calibration Tools**: Easy sensor and pump calibration

## Hardware Requirements

- Raspberry Pi (4 or 5 recommended)
- Atlas Scientific pH, EC, and temperature sensors with EZO circuits
- Peristaltic pumps for dosing
- I2C interface for sensor communication

## Installation

### Option 1: Automated Installation (recommended)

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/nutetra.git
   cd nutetra
   ```

2. Run the installation script:
   ```
   sudo bash install.sh
   ```

3. Access the web interface:
   ```
   http://your-pi-ip:5000
   ```

### Option 2: Manual Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/nutetra.git
   cd nutetra
   ```

2. Create required directories:
   ```
   sudo mkdir -p /NuTetra/logs /NuTetra/data /NuTetra/config /NuTetra/exports
   sudo chmod -R 777 /NuTetra
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python web/start.py
   ```

5. Access the web interface:
   ```
   http://your-pi-ip:5000
   ```

## Configuration

Configuration is stored in `/NuTetra/config/config.json`. The system will create a default configuration if none exists.

Key configuration sections:

- **System**: General system settings
- **I2C**: Sensor addresses and communication settings
- **Pumps**: Pump pin assignments and flow rates
- **Dosing**: Dosing controller settings, target values, and tolerances
- **Alerts**: Alert thresholds and notification settings

All configurations can be modified through the web interface.

## Troubleshooting

### "System manager not initialized" error

If you see this error, check the following:

1. Ensure all required directories exist and are writable:
   ```
   sudo mkdir -p /NuTetra/logs /NuTetra/data /NuTetra/config /NuTetra/exports
   sudo chmod -R 777 /NuTetra
   ```

2. Create a basic configuration file:
   ```
   mkdir -p /NuTetra/config
   echo '{"system":{"name":"NuTetra"},"gpio":{"simulation_mode":true}}' > /NuTetra/config/config.json
   ```

3. Check the logs for specific errors:
   ```
   cat /NuTetra/logs/nutetra.log
   ```

### Sensor Connection Issues

If sensors aren't responding:

1. Enable I2C on your Raspberry Pi:
   ```
   sudo raspi-config
   ```
   Navigate to Interface Options > I2C > Enable

2. Check your I2C connections with:
   ```
   i2cdetect -y 1
   ```

3. Edit your config to enable simulation mode for testing:
   ```
   nano /NuTetra/config/config.json
   ```
   Add `"simulation_mode": true` to the gpio section

### Service Issues

If running as a service and encountering problems:

1. Check service status:
   ```
   sudo systemctl status nutetra.service
   ```

2. View logs:
   ```
   sudo journalctl -u nutetra.service -f
   ```

3. Restart the service:
   ```
   sudo systemctl restart nutetra.service
   ```

## Development

For development and testing, run with the debug flag:
```
python web/start.py --debug
```

This enables Flask debug mode and more verbose logging.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses [Flask](https://flask.palletsprojects.com/) for the web framework
- Real-time updates with [Socket.IO](https://socket.io/)
- Charts powered by [Chart.js](https://www.chartjs.org/)

