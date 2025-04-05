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
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

# Sensor and control imports
from hardware.sensors import SensorManager
from hardware.pumps import PumpController
from hardware.gpio_manager import GPIOManager

# System imports
from system.config_manager import ConfigManager
from system.data_logger import DataLogger

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
    static_folder='web/static',
    template_folder='web/templates'
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
        self.gpio = GPIOManager()
        self.sensors = SensorManager(self.gpio)
        self.pumps = PumpController(self.gpio)
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
                readings = self.sensors.get_readings()
                
                # Emit to connected clients
                socketio.emit('sensor_update', readings)
                
                # Sleep for a short interval
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error broadcasting data: {e}")
                time.sleep(5.0)
    
    def start(self):
        """Start the NuTetra system"""
        logger.info("Starting NuTetra system")
        
        # Start sensor monitoring
        self.sensors.start_monitoring()
    
    def cleanup(self, signum=None, frame=None):
        """Clean up system resources on shutdown"""
        logger.info("Shutting down NuTetra system")
        self.broadcasting = False
        self.sensors.stop_monitoring()
        self.gpio.cleanup()
        
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
    return jsonify(nutetra.sensors.get_readings())

@app.route('/api/pump-status')
def get_pump_status():
    """Get the status of all pumps"""
    return jsonify(nutetra.pumps.get_pump_status())

@app.route('/api/dosing', methods=['POST'])
def trigger_dosing():
    """Trigger a manual dosing"""
    data = request.json
    pump_id = data.get('pump_id')
    volume = data.get('volume')
    
    success, message = nutetra.pumps.dose(pump_id, volume)
    return jsonify({'success': success, 'message': message})

@app.route('/api/settings/<section>', methods=['GET'])
def get_settings(section):
    """Get settings for a specific section"""
    return jsonify(nutetra.config.get(section))

@app.route('/api/settings/<section>/<key>', methods=['POST'])
def update_setting(section, key):
    """Update a specific setting"""
    data = request.json
    value = data.get('value')
    success = nutetra.config.set(section, key, value)
    return jsonify({'success': success})

@app.route('/api/logs/sensor', methods=['GET'])
def get_sensor_logs():
    """Get sensor reading history"""
    days = request.args.get('days', 1, type=int)
    return jsonify(nutetra.data_logger.get_sensor_history(days=days))

@app.route('/api/logs/dosing', methods=['GET'])
def get_dosing_logs():
    """Get dosing event history"""
    days = request.args.get('days', 1, type=int)
    return jsonify(nutetra.data_logger.get_dosing_history(days=days))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Start the NuTetra system
    nutetra.start()
    
    # Run the web server
    host = os.environ.get('NUTETRA_HOST', '0.0.0.0')
    port = int(os.environ.get('NUTETRA_PORT', 5000))
    
    # Use Socket.IO to run the app
    socketio.run(app, host=host, port=port, debug=False)