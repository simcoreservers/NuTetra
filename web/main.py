#!/usr/bin/env python3
# Entry point for the NuTetra web application

import os
import sys
import json
import time
import signal
import logging
import threading
from pathlib import Path

# Adjust paths for new location - IMPROVED PATH HANDLING
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# Also add the project root to handle absolute imports
project_root = os.path.abspath(parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Print paths for debugging
print(f"Current directory: {current_dir}")
print(f"Parent directory: {parent_dir}")
print(f"System path: {sys.path}")

# Try to display directory contents for debugging
try:
    print(f"Parent directory contents: {os.listdir(parent_dir)}")
except Exception as e:
    print(f"Error listing parent directory: {e}")

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

# Import the updated components
try:
    print("Attempting to import modules...")
    from dosing.pump_manager import PumpManager
    print("Imported PumpManager")
    from dosing.dosing_controller import DosingController
    print("Imported DosingController")
    from atlas.atlas_interface import AtlasInterface
    print("Imported AtlasInterface")

    # System imports
    from system.config_manager import ConfigManager
    print("Imported ConfigManager")
    from system.data_logger import DataLogger
    print("Imported DataLogger")
except ImportError as e:
    print(f"CRITICAL ERROR importing modules: {e}")
    print(f"Current sys.path: {sys.path}")
    raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/NuTetra/logs/nutetra.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NuTetra")

# Create Flask application
app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)
app.config['SECRET_KEY'] = 'nutetra-secret-key'
socketio = SocketIO(app)

class NuTetraSystem:
    def __init__(self):
        logger.info("Initializing NuTetra Hydroponic Automation System")
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Initialize system components
        self.config = ConfigManager()
        
        # Initialize new components
        self.atlas = AtlasInterface(self.config)
        self.pumps = PumpManager(self.config)
        self.dosing = DosingController(self.config, self.atlas, self.pumps)
        self.data_logger = DataLogger()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        # Start data broadcasting thread
        self.broadcasting = True
        self.broadcast_thread = threading.Thread(target=self._broadcast_data, daemon=True)
        self.broadcast_thread.start()
        
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for directory in ["/NuTetra/logs", "/NuTetra/data/history"]:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _broadcast_data(self):
        """Broadcast sensor data via Socket.IO"""
        while self.broadcasting:
            try:
                # Get sensor readings
                readings = {
                    'ph': self.atlas.get_ph(),
                    'ec': self.atlas.get_ec(),
                    'tds': self.atlas.get_tds(),
                    'temperature': self.atlas.get_temperature(),
                    'timestamp': time.time()
                }
                
                # Emit to connected clients
                socketio.emit('sensor_update', readings)
                
                # Also emit pump status
                pump_status = {
                    'ph_up': self.pumps.get_pump_state('ph_up')['state'] == 'running',
                    'ph_down': self.pumps.get_pump_state('ph_down')['state'] == 'running',
                    'nutrient_a': self.pumps.get_pump_state('nutrient_a')['state'] == 'running',
                    'nutrient_b': self.pumps.get_pump_state('nutrient_b')['state'] == 'running',
                    'main_pump': self.pumps.get_pump_state('main')['state'] == 'running'
                }
                socketio.emit('pump_status', pump_status)
                
                # Sleep for a short interval
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error broadcasting data: {e}")
                time.sleep(5.0)
    
    def start(self):
        """Start the NuTetra system"""
        logger.info("Starting NuTetra system")
        
        # Initialize Atlas interface
        self.atlas.initialize()
        
        # Start the dosing controller
        self.dosing.start()
    
    def cleanup(self, signum=None, frame=None):
        """Clean up system resources on shutdown"""
        logger.info("Shutting down NuTetra system")
        self.broadcasting = False
        
        # Clean up resources
        self.dosing.stop()
        self.pumps.cleanup()
        self.atlas.cleanup()
        
        if signum is not None:
            sys.exit(0)

# Create the global system instance
nutetra = NuTetraSystem()

# Flask routes
@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/dosing-settings')
def dosing_settings():
    """Render the dosing settings page"""
    return render_template('dosing_settings.html')

@app.route('/pump-control')
def pump_control():
    """Render the pump control page"""
    return render_template('pump_control.html')

@app.route('/calibration')
def calibration():
    """Render the sensor calibration page"""
    return render_template('calibration.html')

@app.route('/alerts')
def alerts():
    """Render the alerts page"""
    return render_template('alerts.html')

@app.route('/logs')
def logs():
    """Render the logs page"""
    return render_template('logs.html')

@app.route('/system-settings')
def system_settings():
    """Render the system settings page"""
    return render_template('system_settings.html')

# API endpoints
@app.route('/api/sensor-readings')
def get_sensor_readings():
    """Get the latest sensor readings"""
    readings = {
        'ph': nutetra.atlas.get_ph(),
        'ec': nutetra.atlas.get_ec(),
        'tds': nutetra.atlas.get_tds(),
        'temperature': nutetra.atlas.get_temperature(),
        'timestamp': time.time()
    }
    return jsonify(readings)

@app.route('/api/dosing/status')
def get_dosing_status():
    """Get the dosing controller status"""
    return jsonify(nutetra.dosing.get_status())

@app.route('/api/dosing/settings')
def get_dosing_settings():
    """Get dosing settings"""
    return jsonify(nutetra.dosing.get_settings())

@app.route('/api/dosing/settings/target', methods=['POST'])
def update_target_settings():
    """Update target dosing settings"""
    try:
        data = request.json
        result = nutetra.dosing.update_target_settings(data)
        return jsonify({'success': True, 'message': 'Target settings updated'})
    except Exception as e:
        logger.error(f"Error updating target settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/dosing/settings/nutrient', methods=['POST'])
def update_nutrient_settings():
    """Update nutrient dosing settings"""
    try:
        data = request.json
        result = nutetra.dosing.update_nutrient_settings(data)
        return jsonify({'success': True, 'message': 'Nutrient settings updated'})
    except Exception as e:
        logger.error(f"Error updating nutrient settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/dosing/settings/safety', methods=['POST'])
def update_safety_settings():
    """Update safety settings"""
    try:
        data = request.json
        result = nutetra.dosing.update_safety_settings(data)
        return jsonify({'success': True, 'message': 'Safety settings updated'})
    except Exception as e:
        logger.error(f"Error updating safety settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/dosing/manual', methods=['POST'])
def manual_dosing():
    """Trigger manual dosing"""
    try:
        data = request.json
        pump = data.get('pump')
        volume = float(data.get('volume'))
        
        # Schedule the dosing
        success = nutetra.dosing.manual_dose(pump, volume)
        return jsonify({'success': success, 'message': f"Dosing {volume}ml with {pump} pump"})
    except Exception as e:
        logger.error(f"Error in manual dosing: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/dosing/run-cycle', methods=['POST'])
def run_dosing_cycle():
    """Run a full dosing cycle"""
    try:
        nutetra.dosing.run_cycle()
        return jsonify({'success': True, 'message': "Dosing cycle started"})
    except Exception as e:
        logger.error(f"Error starting dosing cycle: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/pumps/stop-all', methods=['POST'])
def stop_all_pumps():
    """Emergency stop all pumps"""
    try:
        nutetra.pumps.all_pumps_off()
        return jsonify({'success': True, 'message': "All pumps stopped"})
    except Exception as e:
        logger.error(f"Error stopping pumps: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/calibration/status')
def get_calibration_status():
    """Get sensor calibration status"""
    try:
        ph_status = nutetra.atlas.get_ph_calibration_status()
        ec_status = nutetra.atlas.get_ec_calibration_status()
        temp_status = nutetra.atlas.get_temperature_calibration_status()
        
        return jsonify({
            'ph': ph_status,
            'ec': ec_status,
            'temperature': temp_status
        })
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/calibration/ph', methods=['POST'])
def calibrate_ph():
    """Calibrate pH sensor"""
    try:
        data = request.json
        point = data.get('point')  # 'low', 'mid', or 'high'
        value = float(data.get('value', 0))
        
        result = nutetra.atlas.calibrate_ph(point, value)
        return jsonify({'success': True, 'message': f"pH calibration at {point} point complete"})
    except Exception as e:
        logger.error(f"Error calibrating pH: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/calibration/ec', methods=['POST'])
def calibrate_ec():
    """Calibrate EC sensor"""
    try:
        data = request.json
        point = data.get('point')  # 'dry', 'low', or 'high'
        value = float(data.get('value', 0)) if point != 'dry' else 0
        
        result = nutetra.atlas.calibrate_ec(point, value)
        return jsonify({'success': True, 'message': f"EC calibration at {point} point complete"})
    except Exception as e:
        logger.error(f"Error calibrating EC: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/calibration/temp', methods=['POST'])
def calibrate_temp():
    """Calibrate temperature sensor"""
    try:
        data = request.json
        value = float(data.get('value'))
        
        result = nutetra.atlas.calibrate_temperature(value)
        return jsonify({'success': True, 'message': f"Temperature calibration complete"})
    except Exception as e:
        logger.error(f"Error calibrating temperature: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/calibration/pump', methods=['POST'])
def calibrate_pump():
    """Calibrate pump flow rate"""
    try:
        data = request.json
        pump = data.get('pump')
        volume = float(data.get('volume'))
        run_time = float(data.get('run_time'))
        
        new_rate = nutetra.pumps.calibrate_pump_automated(pump, volume, run_time)
        return jsonify({
            'success': True, 
            'message': f"Pump {pump} calibrated",
            'new_flow_rate': new_rate
        })
    except Exception as e:
        logger.error(f"Error calibrating pump: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/info')
def get_system_info():
    """Get system information"""
    import platform
    import subprocess
    from datetime import datetime, timedelta
    
    # Try to determine if we're on a Raspberry Pi
    pi_model = "Unknown"
    try:
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model', 'r') as f:
                pi_model = f.read().strip('\0')
    except:
        pass
    
    # Determine GPIO interface type
    gpio_interface = "Unknown"
    gpio_chip = None
    try:
        if hasattr(nutetra.pumps, 'simulation_mode') and nutetra.pumps.simulation_mode:
            gpio_interface = "Simulation Mode"
        elif 'rpi_lgpio' in sys.modules:
            gpio_interface = "rpi-lgpio"
            gpio_chip = nutetra.pumps.chip_num if hasattr(nutetra.pumps, 'chip_num') else 4
        elif 'lgpio' in sys.modules:
            gpio_interface = "lgpio"
            gpio_chip = nutetra.pumps.chip_num if hasattr(nutetra.pumps, 'chip_num') else 0
    except:
        pass
    
    # Get system uptime
    uptime = "Unknown"
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime = str(timedelta(seconds=uptime_seconds))
    except:
        pass
    
    # Get CPU temperature
    cpu_temp = "Unknown"
    try:
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                cpu_temp = f"{float(f.read().strip()) / 1000:.1f}°C"
    except:
        pass
    
    return jsonify({
        'system_name': nutetra.config.get_setting('system', {}).get('name', 'NuTetra'),
        'version': '1.0.0',  # Replace with actual version
        'uptime': uptime,
        'platform': pi_model,
        'cpu_temp': cpu_temp,
        'gpio_interface': gpio_interface,
        'gpio_chip': gpio_chip
    })

@app.route('/api/system/gpio-settings', methods=['POST'])
def update_gpio_settings():
    """Update GPIO settings"""
    try:
        data = request.json
        gpio_chip = data.get('gpio_chip')
        gpio_library = data.get('gpio_library')
        
        # Save the settings to config
        gpio_config = nutetra.config.get_setting('gpio', {})
        gpio_config['chip'] = gpio_chip
        gpio_config['library'] = gpio_library
        nutetra.config.set_setting('gpio', gpio_config)
        nutetra.config.save_config()
        
        return jsonify({
            'success': True, 
            'message': "GPIO settings updated. Restart services to apply changes."
        })
    except Exception as e:
        logger.error(f"Error updating GPIO settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/pin-assignments', methods=['POST'])
def update_pin_assignments():
    """Update GPIO pin assignments"""
    try:
        data = request.json
        
        # Save to config
        pump_config = nutetra.config.get_setting('pumps', {})
        for pump_name in ['ph_up', 'ph_down', 'nutrient_a', 'nutrient_b', 'main']:
            if pump_name in data:
                if pump_name not in pump_config:
                    pump_config[pump_name] = {}
                pump_config[pump_name]['pin'] = data[pump_name]
        
        # Save I2C config
        i2c_config = nutetra.config.get_setting('i2c', {})
        i2c_config['bus'] = data.get('i2c_bus', 1)
        i2c_config['enabled'] = data.get('i2c_enabled', True)
        
        # Update settings
        nutetra.config.set_setting('pumps', pump_config)
        nutetra.config.set_setting('i2c', i2c_config)
        nutetra.config.save_config()
        
        return jsonify({
            'success': True, 
            'message': "Pin assignments saved. Restart services to apply changes."
        })
    except Exception as e:
        logger.error(f"Error updating pin assignments: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/test-gpio', methods=['POST'])
def test_gpio():
    """Test GPIO pins by toggling a pump"""
    try:
        data = request.json
        pump = data.get('pump')
        duration = float(data.get('duration', 1.0))
        
        if not pump:
            return jsonify({'success': False, 'message': 'No pump specified'})
        
        # Run the pump briefly
        success = nutetra.pumps.run_pump_for_seconds(pump, duration)
        
        return jsonify({
            'success': success,
            'message': f"Pump {pump} test {'successful' if success else 'failed'}"
        })
    except Exception as e:
        logger.error(f"Error testing GPIO: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/restart', methods=['POST'])
def restart_service():
    """Restart the nutetra service"""
    try:
        import subprocess
        # Run restart in a separate thread to allow response
        def restart_thread():
            time.sleep(1)  # Give time for response
            subprocess.call(['sudo', 'systemctl', 'restart', 'nutetra.service'])
        
        threading.Thread(target=restart_thread, daemon=True).start()
        return jsonify({'success': True, 'message': 'Restarting service...'})
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/reboot', methods=['POST'])
def reboot_system():
    """Reboot the system"""
    try:
        import subprocess
        # Run reboot in a separate thread to allow response
        def reboot_thread():
            time.sleep(1)  # Give time for response
            subprocess.call(['sudo', 'reboot'])
        
        threading.Thread(target=reboot_thread, daemon=True).start()
        return jsonify({'success': True, 'message': 'Rebooting system...'})
    except Exception as e:
        logger.error(f"Error rebooting system: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/clear-logs', methods=['POST'])
def clear_logs():
    """Clear system logs"""
    try:
        import glob
        log_files = glob.glob('/NuTetra/logs/*.log*')
        for file in log_files:
            try:
                if os.path.isfile(file):
                    os.truncate(file, 0)
            except Exception as e:
                logger.error(f"Error clearing log file {file}: {e}")
        
        return jsonify({'success': True, 'message': 'Logs cleared'})
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/system/factory-reset', methods=['POST'])
def factory_reset():
    """Factory reset the system"""
    try:
        # Reset config to defaults
        nutetra.config.reset_to_defaults()
        
        # Clear all history
        import shutil
        try:
            shutil.rmtree('/NuTetra/data/history')
            os.makedirs('/NuTetra/data/history', exist_ok=True)
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
        
        # Clear logs
        clear_logs()
        
        # Return success
        return jsonify({'success': True, 'message': 'Factory reset complete. Restart service to apply changes.'})
    except Exception as e:
        logger.error(f"Error performing factory reset: {e}")
        return jsonify({'success': False, 'message': str(e)})

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    logger.info(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    # Start the nutetra system
    nutetra.start()
    
    # Run the web server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False) 