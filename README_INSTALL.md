# NuTetra Installation and Setup Guide

This guide provides step-by-step instructions for installing and setting up the NuTetra Hydroponic Automation System on a Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 (8GB RAM recommended)
- Raspberry Pi Touch Display 2 (or compatible touchscreen)
- Raspberry Pi OS (64-bit recommended)
- pH sensor (Atlas Scientific or compatible)
- EC sensor (Atlas Scientific or compatible)
- Temperature sensor (DS18B20 or compatible)
- Peristaltic dosing pumps (typically 12V)
- Relay board for controlling pumps
- Power supply for Raspberry Pi and pumps

## Hardware Setup

### Wiring Diagram

```
┌──────────────────┐
│  Raspberry Pi 5  │
└─────────┬────────┘
          │
┌─────────┴────────┐
│     GPIO Pins    │
└─────────┬────────┘
          │
     ┌────┴────┐
     │         │
┌────┴─┐   ┌───┴───┐
│ Relay│   │ Sensor│
│ Board│   │Interface
└────┬─┘   └───┬───┘
     │         │
┌────┴─┐   ┌───┴───┐
│ Pumps│   │Sensors│
└──────┘   └───────┘
```

### GPIO Pin Assignments

- GPIO 5: pH Up Pump
- GPIO 6: pH Down Pump
- GPIO 13: Nutrient A Pump
- GPIO 19: Nutrient B Pump
- GPIO 17: pH Sensor
- GPIO 27: EC Sensor
- GPIO 22: Temperature Sensor

## Software Installation

### Method 1: Automatic Installation (Recommended)

1. Download the NuTetra files to your Raspberry Pi:
   ```
   git clone https://github.com/simcoreservers/nutetra.git
   cd nutetra
   ```

2. Run the installation script:
   ```
   chmod +x install.sh
   sudo ./install.sh
   ```

3. Reboot your Raspberry Pi:
   ```
   sudo reboot
   ```

### Method 2: Manual Installation

1. Create the installation directory:
   ```
   sudo mkdir -p /NuTetra
   sudo mkdir -p /NuTetra/logs
   sudo mkdir -p /NuTetra/data/history
   ```

2. Install required packages:
   ```
   sudo apt update
   sudo apt install -y python3-pip python3-pyqt5 git python3-dev python3-numpy python3-pandas
   ```

3. Install Python dependencies:
   ```
   sudo pip3 install -r requirements.txt
   ```

4. Copy application files:
   ```
   sudo cp -r * /NuTetra/
   ```

5. Set permissions:
   ```
   sudo chmod +x /NuTetra/main.py
   sudo chown -R pi:pi /NuTetra
   ```

6. Create a desktop shortcut (optional):
   ```
   echo "[Desktop Entry]
   Type=Application
   Name=NuTetra
   Comment=NuTetra Hydroponic Automation System
   Exec=python3 /NuTetra/main.py
   Terminal=false
   Categories=Utility;" > ~/Desktop/NuTetra.desktop
   
   chmod +x ~/Desktop/NuTetra.desktop
   ```

## First-Time Setup

After installation, follow these steps to configure your NuTetra system:

### 1. Initial Configuration

1. Start NuTetra by clicking the desktop shortcut or running:
   ```
   python3 /NuTetra/main.py
   ```

2. The system will initialize with default settings. Navigate to the System Settings tab to configure basic system settings.

### 2. Sensor Calibration

1. Go to the Dashboard tab and click the "Calibrate" button.

2. Follow the on-screen instructions to calibrate:
   - **pH**: Use 7.0 and 4.0 buffer solutions
   - **EC**: Use standard EC solution (1.413 mS/cm recommended)
   - **Temperature**: Confirm with a known reference

### 3. Pump Calibration

1. Go to the Pump Control tab.

2. For each pump:
   - Run the pump for a fixed time (e.g., 10 seconds)
   - Measure the actual volume dispensed
   - Enter the measured volume to calibrate flow rate

### 4. Dosing Settings

1. Go to the Dosing Settings tab.

2. Configure:
   - Target pH and EC ranges
   - Dosing amounts
   - Maximum daily dosing limits

### 5. Alert Configuration

1. Go to the Alerts tab.

2. Set up alerts for out-of-range conditions (email or SMS).

## Troubleshooting

If you encounter issues:

1. Check the log files at `/NuTetra/logs/nutetra.log`

2. Verify hardware connections and GPIO pin assignments

3. Ensure all sensors are properly connected and functional

4. Restart the application or reboot the Raspberry Pi

## Support

For assistance or to report issues:
- Create an issue on GitHub
- Contact us at support@nutetra.com 