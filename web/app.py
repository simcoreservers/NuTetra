#!/usr/bin/env python3
"""
nutetra Hydroponic System - Web Interface
Flask application that serves the web interface for monitoring and controlling the hydroponic system.
"""
import os
import json
import datetime
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'web_interface.log')

logger = logging.getLogger('nutetra_web')
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nutetra-secret-key'  # Change in production
socketio = SocketIO(app)

# Path to settings file
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings')
os.makedirs(SETTINGS_DIR, exist_ok=True)
DOSING_SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'dosing_settings.json')

# Default settings
DEFAULT_DOSING_SETTINGS = {
    'target_ph': 6.0,
    'ph_tolerance': 0.3,
    'target_ec': 1.8,
    'ec_tolerance': 0.2,
    'dosing_frequency': 60,  # minutes
    'dosing_cooldown': 15,   # minutes
    'mixing_time': 30,       # seconds
    'enable_night_mode': False,
    'night_start': '22:00',
    'night_end': '06:00',
    'ph_up_rate': 1.0,       # ml/sec
    'ph_down_rate': 1.0,     # ml/sec
    'nutrient_a_rate': 1.0,  # ml/sec
    'nutrient_b_rate': 1.0,  # ml/sec
    'max_ph_adjustment': 20, # ml
    'max_nutrient_dose': 20, # ml
    'max_daily_ph_up': 100,  # ml
    'max_daily_ph_down': 100,# ml
    'max_daily_nutrient': 200# ml
}

# Simulated data for development
# In production, this would be replaced with actual sensor readings and system status
simulated_sensor_data = {
    'ph': 6.1,
    'ec': 1.7,
    'temperature': 22.5
}

simulated_pump_status = {
    'main_pump': False,
    'ph_up': False,
    'ph_down': False,
    'nutrient_a': False,
    'nutrient_b': False
}

simulated_system_status = {
    'status': 'Running',
    'last_dosing': '2024-04-04 17:30:00',
    'next_dosing': '2024-04-04 18:30:00',
    'alerts_count': 0
}

# Helper functions
def load_dosing_settings():
    """Load dosing settings from file or return defaults if file doesn't exist."""
    try:
        if os.path.exists(DOSING_SETTINGS_FILE):
            with open(DOSING_SETTINGS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Save defaults if file doesn't exist
            save_dosing_settings(DEFAULT_DOSING_SETTINGS)
            return DEFAULT_DOSING_SETTINGS
    except Exception as e:
        logger.error(f"Error loading dosing settings: {e}")
        return DEFAULT_DOSING_SETTINGS

def save_dosing_settings(settings):
    """Save dosing settings to file."""
    try:
        with open(DOSING_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        logger.info("Dosing settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving dosing settings: {e}")
        return False

# Flask routes
@app.route('/')
def index():
    """Render the dashboard page."""
    return render_template('index.html')

@app.route('/dosing_settings')
def dosing_settings():
    """Render the dosing settings page."""
    return render_template('dosing_settings.html')

@app.route('/pump_control')
def pump_control():
    """Render the pump control page."""
    return render_template('pump_control.html')

@app.route('/alerts')
def alerts():
    """Render the alerts page."""
    return render_template('alerts.html')

@app.route('/logs')
def logs():
    """Render the logs page."""
    return render_template('logs.html')

@app.route('/system_settings')
def system_settings():
    """Render the system settings page."""
    return render_template('system_settings.html')

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect."""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_sensor_data')
def handle_request_sensor_data():
    """Send current sensor data to client."""
    # In production, this would get actual sensor readings
    emit('sensor_data', simulated_sensor_data)

@socketio.on('request_pump_status')
def handle_request_pump_status():
    """Send current pump status to client."""
    # In production, this would get actual pump status
    emit('pump_status', simulated_pump_status)

@socketio.on('request_system_status')
def handle_request_system_status():
    """Send current system status to client."""
    # In production, this would get actual system status
    emit('system_status', simulated_system_status)

@socketio.on('request_dosing_settings')
def handle_request_dosing_settings():
    """Send current dosing settings to client."""
    settings = load_dosing_settings()
    emit('dosing_settings', settings)

@socketio.on('update_dosing_settings')
def handle_update_dosing_settings(data):
    """Update dosing settings."""
    try:
        # Validate settings (basic validation example)
        if 'target_ph' not in data or not (4.0 <= float(data['target_ph']) <= 8.0):
            raise ValueError("Invalid target pH value")
        
        # In production, you'd do more extensive validation
        
        # Save settings
        success = save_dosing_settings(data)
        if success:
            emit('settings_updated', {'success': True})
            # In production, you'd also update the actual dosing system
        else:
            emit('settings_error', {'message': 'Failed to save settings'})
    
    except Exception as e:
        logger.error(f"Error updating dosing settings: {e}")
        emit('settings_error', {'message': str(e)})

@socketio.on('restore_default_dosing_settings')
def handle_restore_default_settings():
    """Restore default dosing settings."""
    try:
        success = save_dosing_settings(DEFAULT_DOSING_SETTINGS)
        if success:
            emit('dosing_settings', DEFAULT_DOSING_SETTINGS)
            emit('settings_updated', {'success': True})
        else:
            emit('settings_error', {'message': 'Failed to restore default settings'})
    except Exception as e:
        logger.error(f"Error restoring default settings: {e}")
        emit('settings_error', {'message': str(e)})

@socketio.on('control_pump')
def handle_control_pump(data):
    """Control a pump."""
    try:
        pump_id = data.get('pump_id')
        action = data.get('action')
        duration = data.get('duration', 0)
        
        if not pump_id or not action:
            raise ValueError("Missing pump_id or action")
        
        if action not in ['start', 'stop']:
            raise ValueError("Invalid action")
        
        # In production, this would control actual pumps
        # For now, just update the simulated status
        global simulated_pump_status
        
        if pump_id == 'main_pump':
            simulated_pump_status['main_pump'] = (action == 'start')
        elif pump_id == 'ph_up':
            simulated_pump_status['ph_up'] = (action == 'start')
        elif pump_id == 'ph_down':
            simulated_pump_status['ph_down'] = (action == 'start')
        elif pump_id == 'nutrient_a':
            simulated_pump_status['nutrient_a'] = (action == 'start')
        elif pump_id == 'nutrient_b':
            simulated_pump_status['nutrient_b'] = (action == 'start')
        else:
            raise ValueError(f"Unknown pump_id: {pump_id}")
        
        # Log the action
        logger.info(f"Pump control: {pump_id} {action} for {duration}s")
        
        # Emit updated status to all clients
        socketio.emit('pump_status', simulated_pump_status)
        
        emit('pump_control_result', {
            'success': True,
            'pump_id': pump_id,
            'action': action,
            'message': f"Pump {pump_id} {action}ed successfully"
        })
        
    except Exception as e:
        logger.error(f"Error controlling pump: {e}")
        emit('pump_control_result', {
            'success': False,
            'message': str(e)
        })

# Simulated sensor update (would be replaced with actual sensor readings in production)
def update_simulated_sensors():
    """Update simulated sensor values with small random changes."""
    import random
    global simulated_sensor_data
    
    # Small random changes
    simulated_sensor_data['ph'] = max(4.0, min(8.0, simulated_sensor_data['ph'] + random.uniform(-0.1, 0.1)))
    simulated_sensor_data['ec'] = max(0.5, min(3.0, simulated_sensor_data['ec'] + random.uniform(-0.05, 0.05)))
    simulated_sensor_data['temperature'] = max(15.0, min(30.0, simulated_sensor_data['temperature'] + random.uniform(-0.2, 0.2)))
    
    # Emit to all clients
    socketio.emit('sensor_data', simulated_sensor_data)

# Background task for sensor updates (in production would be a separate process)
@socketio.on('start_sensor_updates')
def start_sensor_updates():
    """Start periodic sensor updates."""
    def sensor_update_task():
        while True:
            update_simulated_sensors()
            socketio.sleep(5)  # Update every 5 seconds
    
    socketio.start_background_task(sensor_update_task)

if __name__ == '__main__':
    logger.info("Starting nutetra Web Interface")
    # In production, you'd use a proper WSGI server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 