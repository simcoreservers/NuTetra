# NuTetra Hydroponic System Deployment Guide

This guide outlines the steps to deploy the improved NuTetra system to your Raspberry Pi.

## System Improvements Summary

We've made the following improvements to make the system more robust:

1. **Added Simulation Mode**: The system now has a simulation mode that works even when hardware components are not available.
2. **Enhanced Error Handling**: Better error handling for sensor readings and initialization failures.
3. **Fixed Routing Issues**: Corrected navigation links in the web interface.
4. **Improved DosingController**: Updated to support simulation and better error handling.
5. **Enhanced PumpManager**: Added better safety features and simulation support.
6. **Robust AtlasInterface**: Better error handling and simulation capabilities for sensor readings.

## Deploying to Raspberry Pi

### 1. Copy Files to Raspberry Pi

Use SCP to copy the updated files to your Raspberry Pi:

```bash
# Navigate to your local NuTetra directory
cd /path/to/NuTetra

# Copy directories (create them first if they don't exist)
ssh pi@nutetra.local "mkdir -p /home/pi/nutetra/dosing /home/pi/nutetra/atlas /home/pi/nutetra/system /home/pi/nutetra/web"

# Copy individual files
scp dosing/dosing_controller.py pi@nutetra.local:/home/pi/nutetra/dosing/
scp dosing/pump_manager.py pi@nutetra.local:/home/pi/nutetra/dosing/
scp atlas/atlas_interface.py pi@nutetra.local:/home/pi/nutetra/atlas/
scp system/system_manager.py pi@nutetra.local:/home/pi/nutetra/system/
scp config/config_manager.py pi@nutetra.local:/home/pi/nutetra/config/
scp web/main.py pi@nutetra.local:/home/pi/nutetra/web/
scp web/templates/base.html pi@nutetra.local:/home/pi/nutetra/web/templates/

# Copy the main.py file
scp main.py pi@nutetra.local:/home/pi/nutetra/
```

### 2. Create or Update Configuration File

Ensure your configuration file is set up correctly on the Raspberry Pi:

```bash
ssh pi@nutetra.local

# Create/edit the configuration file
nano /home/pi/nutetra/config/nutetra_config.json
```

Example configuration:

```json
{
  "system": {
    "log_level": "INFO",
    "simulation_mode": false
  },
  "dosing": {
    "target_ph": 6.0,
    "ph_tolerance": 0.2,
    "target_ec": 1500,
    "ec_tolerance": 100,
    "dosing_interval": 1800,
    "max_daily_ph_up": 100,
    "max_daily_ph_down": 100,
    "max_daily_nutrient_a": 100,
    "max_daily_nutrient_b": 100,
    "mixing_time": 30,
    "night_mode_active": false,
    "night_mode_start": "22:00",
    "night_mode_end": "06:00"
  },
  "pumps": {
    "ph_up": {"pin": 17, "rate": 1.0},
    "ph_down": {"pin": 18, "rate": 1.0},
    "nutrient_a": {"pin": 22, "rate": 1.0},
    "nutrient_b": {"pin": 23, "rate": 1.0}
  },
  "atlas": {
    "i2c_bus": 1,
    "ph_address": 99,
    "ec_address": 100,
    "rtd_address": 102,
    "temp_compensation": true
  }
}
```

### 3. Restart the NuTetra Service

Restart the system service to apply all changes:

```bash
sudo systemctl restart nutetra.service
sudo systemctl status nutetra.service
```

### 4. Check Logs for Errors

Monitor the system logs to ensure everything is working correctly:

```bash
# View the last 100 lines of the log
tail -n 100 /home/pi/nutetra/logs/nutetra.log

# Follow the log in real-time
tail -f /home/pi/nutetra/logs/nutetra.log
```

## Troubleshooting

### Simulation Mode

If you're having issues with hardware, enable simulation mode by setting `"simulation_mode": true` in the configuration file.

### Web Interface Not Loading

Check the Flask application logs:

```bash
tail -n 100 /home/pi/nutetra/logs/web.log
```

### Sensor Reading Issues

If you encounter issues with sensor readings, check:
1. I2C connections
2. Atlas sensor addresses in the configuration
3. Enable simulation mode for testing without hardware

### Pump Control Issues

Check:
1. GPIO pin connections
2. Pump settings in the configuration
3. Permissions for GPIO access

## Additional Resources

For more information on the NuTetra system architecture and components, refer to the README.md file in the project repository. 