#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Web Application
Main Flask application that provides API endpoints and web interface
"""
import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from logging.handlers import RotatingFileHandler

# Add parent directory to path so we can import our modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our system modules
from system.system_manager import SystemManager

# Initialize logging
logger = logging.getLogger('NuTetra.Web')

# Initialize Flask app
app = Flask(__name__, 
    static_folder='static',
    template_folder='templates')

# Configure Flask app
app.config['SECRET_KEY'] = 'nutetra-hydroponic-system'
app.config['JSON_SORT_KEYS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize SocketIO with CORS allowed
socketio = SocketIO(app, cors_allowed_origins="*")

# Global system manager instance
system_manager = None


@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')


@app.route('/settings')
def settings():
    """Render the settings page"""
    return render_template('system_settings.html')


@app.route('/calibration')
def calibration():
    """Render the calibration page"""
    return render_template('calibration.html')


@app.route('/logs')
def logs():
    """Render the logs page"""
    return render_template('logs.html')


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


# API Endpoints

@app.route('/api/system/info', methods=['GET'])
def api_system_info():
    """API endpoint to get system information"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Get system status
        status = system_manager.get_system_status()
        
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        logger.error(f"Error in /api/system/info: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/readings', methods=['GET'])
def api_readings():
    """API endpoint to get current sensor readings"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Get readings
        readings = system_manager.get_readings()
        
        return jsonify({
            'status': 'success',
            'data': readings
        })
    except Exception as e:
        logger.error(f"Error in /api/readings: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/status', methods=['GET'])
def api_dosing_status():
    """API endpoint to get dosing status"""
    try:
        if system_manager is None or system_manager.dosing_controller is None:
            return jsonify({
                'status': 'error',
                'message': 'Dosing controller not initialized'
            }), 500
        
        # Get dosing status
        status = system_manager.dosing_controller.get_status()
        history = system_manager.dosing_controller.get_dosing_history()
        
        return jsonify({
            'status': 'success',
            'data': {
                'status': status,
                'history': history
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/dosing/status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/start', methods=['POST'])
def api_start_dosing():
    """API endpoint to start automatic dosing"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        result = system_manager.start_dosing()
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Automatic dosing started'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start dosing'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/start: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/stop', methods=['POST'])
def api_stop_dosing():
    """API endpoint to stop automatic dosing"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        result = system_manager.stop_dosing()
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Automatic dosing stopped'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to stop dosing'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/stop: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/manual', methods=['POST'])
def api_manual_dose():
    """API endpoint for manual dosing"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        data = request.json
        if not data or 'pump' not in data or 'volume' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing pump or volume parameter'
            }), 400
        
        pump = data['pump']
        volume = float(data['volume'])
        
        # Validate pump name
        valid_pumps = ['ph_up', 'ph_down', 'nutrient_a', 'nutrient_b']
        if pump not in valid_pumps:
            return jsonify({
                'status': 'error',
                'message': f'Invalid pump name. Must be one of: {", ".join(valid_pumps)}'
            }), 400
        
        # Validate volume
        if volume <= 0 or volume > 50:
            return jsonify({
                'status': 'error',
                'message': 'Volume must be between 0 and 50 ml'
            }), 400
        
        result = system_manager.manual_dose(pump, volume)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Manual dose of {volume} ml using {pump} pump initiated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to perform manual dose'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/manual: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """API endpoint to get system settings"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Get settings from config manager
        settings = {
            'dosing': system_manager.config_manager.get_setting('dosing', {}),
            'pumps': system_manager.config_manager.get_setting('pumps', {}),
            'i2c': system_manager.config_manager.get_setting('i2c', {}),
            'alerts': system_manager.config_manager.get_setting('alerts', {})
        }
        
        return jsonify({
            'status': 'success',
            'data': settings
        })
    except Exception as e:
        logger.error(f"Error in /api/settings: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/settings/<section>', methods=['PUT'])
def api_update_settings(section):
    """API endpoint to update system settings"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Validate section
        valid_sections = ['dosing', 'pumps', 'i2c', 'alerts']
        if section not in valid_sections:
            return jsonify({
                'status': 'error',
                'message': f'Invalid settings section. Must be one of: {", ".join(valid_sections)}'
            }), 400
        
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No settings data provided'
            }), 400
        
        # Update settings
        result = system_manager.update_settings(section, data)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Settings updated for {section}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to update settings for {section}'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/settings/{section}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/calibration/sensor', methods=['POST'])
def api_calibrate_sensor():
    """API endpoint for sensor calibration"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        data = request.json
        if not data or 'sensor' not in data or 'value' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing sensor or value parameter'
            }), 400
        
        sensor = data['sensor']
        value = float(data['value'])
        
        # Validate sensor type
        valid_sensors = ['ph', 'ec']
        if sensor not in valid_sensors:
            return jsonify({
                'status': 'error',
                'message': f'Invalid sensor type. Must be one of: {", ".join(valid_sensors)}'
            }), 400
        
        result = system_manager.calibrate_sensor(sensor, value)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Calibration of {sensor} sensor to {value} successful'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to calibrate {sensor} sensor'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/calibration/sensor: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/calibration/pump', methods=['POST'])
def api_calibrate_pump():
    """API endpoint for pump calibration"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        data = request.json
        if not data or 'pump' not in data or 'volume' not in data or 'time' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing pump, volume, or time parameter'
            }), 400
        
        pump = data['pump']
        volume = float(data['volume'])
        time_sec = float(data['time'])
        
        # Validate pump name
        valid_pumps = ['ph_up', 'ph_down', 'nutrient_a', 'nutrient_b']
        if pump not in valid_pumps:
            return jsonify({
                'status': 'error',
                'message': f'Invalid pump name. Must be one of: {", ".join(valid_pumps)}'
            }), 400
        
        # Validate volume and time
        if volume <= 0 or time_sec <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Volume and time must be greater than 0'
            }), 400
        
        result = system_manager.calibrate_pump(pump, volume, time_sec)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Calibration of {pump} pump successful (flow rate: {volume/time_sec:.2f} ml/s)'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to calibrate {pump} pump'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/calibration/pump: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/export', methods=['GET'])
def api_export_data():
    """API endpoint to export system data"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        export_path = system_manager.export_data()
        
        if export_path:
            return jsonify({
                'status': 'success',
                'message': 'Data exported successfully',
                'path': export_path
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to export data'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/export: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/alerts/settings', methods=['GET'])
def api_get_alert_settings():
    """API endpoint to get alert settings"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Get alerts settings from config manager
        alerts = system_manager.config_manager.get_setting('alerts', {})
        
        return jsonify({
            'status': 'success',
            'data': alerts
        })
    except Exception as e:
        logger.error(f"Error in /api/alerts/settings: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/alerts/settings', methods=['POST'])
def api_update_alert_settings():
    """API endpoint to update alert settings"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No settings data provided'
            }), 400
        
        # Update settings
        result = system_manager.update_settings('alerts', data)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Alert settings updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update alert settings'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/alerts/settings (POST): {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/alerts/history', methods=['GET'])
def api_get_alert_history():
    """API endpoint to get alert history"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Get warnings from system state
        warnings = system_manager.system_state.get('warnings', [])
        
        return jsonify({
            'status': 'success',
            'data': warnings
        })
    except Exception as e:
        logger.error(f"Error in /api/alerts/history: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/alerts/test', methods=['POST'])
def api_test_alert():
    """API endpoint to test alert notifications"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        # Add a test warning
        system_manager._add_warning("This is a test alert notification")
        
        return jsonify({
            'status': 'success',
            'message': 'Test alert notification sent'
        })
    except Exception as e:
        logger.error(f"Error in /api/alerts/test: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/settings', methods=['GET'])
def api_dosing_settings():
    """API endpoint to get dosing settings"""
    try:
        if system_manager is None or system_manager.dosing_controller is None:
            return jsonify({
                'status': 'error',
                'message': 'Dosing controller not initialized'
            }), 500
        
        settings = system_manager.dosing_controller.get_settings()
        
        return jsonify({
            'status': 'success',
            'data': settings
        })
    except Exception as e:
        logger.error(f"Error in /api/dosing/settings: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/settings/target', methods=['POST'])
def api_update_dosing_target():
    """API endpoint to update dosing target settings"""
    try:
        if system_manager is None or system_manager.dosing_controller is None:
            return jsonify({
                'status': 'error',
                'message': 'Dosing controller not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        result = system_manager.dosing_controller.update_target_settings(data)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Target settings updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update settings'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/settings/target: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/settings/nutrient', methods=['POST'])
def api_update_nutrient_settings():
    """API endpoint to update nutrient settings"""
    try:
        if system_manager is None or system_manager.dosing_controller is None:
            return jsonify({
                'status': 'error',
                'message': 'Dosing controller not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        result = system_manager.dosing_controller.update_nutrient_settings(data)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Nutrient settings updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update settings'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/settings/nutrient: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/dosing/settings/safety', methods=['POST'])
def api_update_safety_settings():
    """API endpoint to update safety settings"""
    try:
        if system_manager is None or system_manager.dosing_controller is None:
            return jsonify({
                'status': 'error',
                'message': 'Dosing controller not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        result = system_manager.dosing_controller.update_safety_settings(data)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': 'Safety settings updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update settings'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/dosing/settings/safety: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/pumps/info', methods=['GET'])
def api_pump_info():
    """API endpoint to get pump information"""
    try:
        if system_manager is None or system_manager.dosing_controller is None or system_manager.dosing_controller.pumps is None:
            return jsonify({
                'status': 'error',
                'message': 'Pump manager not initialized'
            }), 500
        
        pump_name = request.args.get('pump')
        if not pump_name:
            return jsonify({
                'status': 'error',
                'message': 'Pump name not provided'
            }), 400
        
        # Get pump state
        pump_state = system_manager.dosing_controller.pumps.get_pump_state(pump_name)
        
        # Get pump settings from config
        pump_settings = system_manager.config_manager.get_setting('pumps', {}).get(pump_name, {})
        
        return jsonify({
            'status': 'success',
            'data': {
                'state': pump_state,
                'settings': pump_settings
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/pumps/info: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/pumps/calibrate', methods=['POST'])
def api_calibrate_pump():
    """API endpoint to calibrate a pump"""
    try:
        if system_manager is None or system_manager.dosing_controller is None or system_manager.dosing_controller.pumps is None:
            return jsonify({
                'status': 'error',
                'message': 'Pump manager not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        pump_name = data.get('pump')
        run_time = data.get('time')
        
        if not pump_name or run_time is None:
            return jsonify({
                'status': 'error',
                'message': 'Pump name and time are required'
            }), 400
        
        # Run the pump for the specified time
        success = system_manager.dosing_controller.pumps.run_pump_for_seconds(pump_name, float(run_time))
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Pump {pump_name} ran for {run_time} seconds'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to run pump'
            }), 500
    except Exception as e:
        logger.error(f"Error in /api/pumps/calibrate: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/pumps/save-calibration', methods=['POST'])
def api_save_pump_calibration():
    """API endpoint to save pump calibration"""
    try:
        if system_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'System manager not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        pump_name = data.get('pump')
        volume = data.get('volume')
        time = data.get('time')
        
        if not pump_name or volume is None or time is None:
            return jsonify({
                'status': 'error',
                'message': 'Pump name, volume, and time are required'
            }), 400
        
        # Calculate flow rate
        flow_rate = float(volume) / float(time)
        
        # Update pump settings
        pumps_config = system_manager.config_manager.get_setting('pumps', {})
        
        if pump_name not in pumps_config:
            pumps_config[pump_name] = {}
        
        pumps_config[pump_name]['rate'] = flow_rate
        
        # Save to config
        system_manager.config_manager.set_setting('pumps', pumps_config)
        system_manager.config_manager.save_config()
        
        # Update dosing controller settings if needed
        if system_manager.dosing_controller:
            rate_key = f"{pump_name}_rate"
            system_manager.dosing_controller.settings[rate_key] = flow_rate
        
        return jsonify({
            'status': 'success',
            'message': f'Calibration saved: {pump_name} flow rate = {flow_rate:.2f} ml/sec'
        })
    except Exception as e:
        logger.error(f"Error in /api/pumps/save-calibration: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/pumps/stop-all', methods=['POST'])
def api_stop_all_pumps():
    """API endpoint to stop all pumps"""
    try:
        if system_manager is None or system_manager.dosing_controller is None or system_manager.dosing_controller.pumps is None:
            return jsonify({
                'status': 'error',
                'message': 'Pump manager not initialized'
            }), 500
        
        system_manager.dosing_controller.pumps.all_pumps_off()
        
        return jsonify({
            'status': 'success',
            'message': 'All pumps stopped'
        })
    except Exception as e:
        logger.error(f"Error in /api/pumps/stop-all: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# SocketIO events

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('request_readings')
def handle_request_readings():
    """Send current readings to the client"""
    if system_manager:
        readings = system_manager.get_readings()
        emit('readings_update', readings)


# Background task to push readings updates to connected clients
def background_readings_sender():
    """Background thread to send readings updates to connected clients"""
    logger.info("Starting background readings sender")
    
    while True:
        try:
            if system_manager:
                readings = system_manager.get_readings()
                socketio.emit('readings_update', readings)
            
            # Sleep for 5 seconds
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in background readings sender: {e}")
            time.sleep(10)  # Sleep longer on error


def initialize_system(config_path=None):
    """Initialize the system manager"""
    global system_manager
    
    try:
        # Initialize the system manager
        system_manager = SystemManager(config_path)
        
        # Start the background thread for sending readings updates
        thread = threading.Thread(target=background_readings_sender, daemon=True)
        thread.start()
        
        # Start automatic dosing if configured
        dosing_config = system_manager.config_manager.get_setting('dosing', {})
        if dosing_config.get('auto_dosing_enabled', True):
            system_manager.start_dosing()
        
        logger.info("System initialization complete")
        return True
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        return False


# Initialize logging for Flask
def setup_flask_logging():
    """Setup logging for Flask application"""
    log_dir = Path("/NuTetra/logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except:
        # Fallback to current directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "flask.log"
    
    handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=3)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add to Flask logger
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


# Entry point when run directly
if __name__ == "__main__":
    # Setup Flask logging
    setup_flask_logging()
    
    # Initialize the system
    success = initialize_system()
    
    if success:
        app.logger.info("Starting Flask application")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    else:
        app.logger.error("Failed to initialize system, exiting")
        sys.exit(1) 