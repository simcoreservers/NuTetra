#!/usr/bin/env python3
"""
NuTetra Hydroponic System - System Manager
Centralizes system control and management
"""
import os
import sys
import time
import json
import logging
import threading
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Import our modules
from system.config_manager import ConfigManager
from dosing.dosing_controller import DosingController
from atlas.atlas_interface import AtlasInterface

logger = logging.getLogger("NuTetra.System")

class SystemManager:
    """Manages the overall NuTetra Hydroponic System"""
    
    def __init__(self, config_path: str = None):
        """Initialize the System Manager
        
        Args:
            config_path: Optional path to config file
        """
        # Initialize logging
        self._setup_logging()
        
        logger.info("Initializing NuTetra System Manager")
        
        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        
        # System state tracking
        self.system_state = {
            'status': 'initializing',
            'last_reading': None,
            'last_dosing': None,
            'errors': [],
            'warnings': [],
            'startup_time': datetime.now().isoformat(),
            'uptime_seconds': 0,
            'system_load': 0,
            'memory_usage': 0,
            'disk_usage': 0
        }
        
        # Initialize components
        self.atlas = None
        self.dosing_controller = None
        
        # Sensor readings
        self.readings = {
            'ph': None,
            'ec': None,
            'tds': None,
            'temperature': None,
            'timestamp': None
        }
        
        # Monitoring thread
        self.monitor_thread = None
        self.monitor_running = False
        
        # Event for graceful shutdown
        self.shutdown_event = threading.Event()
        
        # Initialize the system
        self._initialize_system()
        
        logger.info("NuTetra System Manager initialization complete")
    
    def _setup_logging(self):
        """Setup logging for the application"""
        root_logger = logging.getLogger()
        
        # Check if handlers are already configured
        if root_logger.hasHandlers():
            return
        
        root_logger.setLevel(logging.INFO)
        
        # Create log directory if needed
        log_dir = Path("/NuTetra/logs")
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except:
            # Fallback to current directory
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
        
        # File handler
        log_file = log_dir / "nutetra.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def _initialize_system(self):
        """Initialize system components"""
        try:
            # Initialize Atlas Sensors
            try:
                self._initialize_atlas()
            except Exception as e:
                logger.error(f"Failed to initialize Atlas sensors: {e}")
                self.atlas = None
                self.system_state['errors'].append(f"Atlas initialization error: {e}")
            
            # Initialize Dosing Controller
            try:
                self._initialize_dosing_controller()
            except Exception as e:
                logger.error(f"Failed to initialize dosing controller: {e}")
                self.dosing_controller = None
                self.system_state['errors'].append(f"Dosing controller initialization error: {e}")
            
            # Update system state
            self.system_state['status'] = 'ready'
            
            # Start monitoring thread
            self._start_monitoring()
            
            logger.info("System initialization complete")
            return True
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.system_state['status'] = 'error'
            self.system_state['errors'].append(f"Initialization error: {e}")
            return False
    
    def _initialize_atlas(self):
        """Initialize Atlas Scientific sensors"""
        try:
            i2c_config = self.config_manager.get_setting('i2c', {})
            self.atlas = AtlasInterface(
                bus=i2c_config.get('bus', 1),
                addresses={
                    'ph': i2c_config.get('ph_address', 0x63),
                    'ec': i2c_config.get('ec_address', 0x64),
                    'temp': i2c_config.get('temp_address', 0x66),
                }
            )
            logger.info("Atlas sensors initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Atlas sensors: {e}")
            raise
    
    def _initialize_dosing_controller(self):
        """Initialize the dosing controller"""
        try:
            # Create the dosing controller with our config manager
            self.dosing_controller = DosingController(
                config_manager=self.config_manager,
                atlas=self.atlas
            )
            logger.info("Dosing controller initialized")
        except Exception as e:
            logger.error(f"Failed to initialize dosing controller: {e}")
            raise
    
    def _start_monitoring(self):
        """Start system monitoring thread"""
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            logger.warning("Monitor thread already running")
            return
        
        self.monitor_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("System monitoring thread started")
    
    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread"""
        logger.info("Starting system monitoring")
        last_reading_time = 0
        last_system_update = 0
        
        while not self.shutdown_event.is_set() and self.monitor_running:
            try:
                # Update system metrics periodically (every 30 seconds)
                current_time = time.time()
                if current_time - last_system_update > 30:
                    self._update_system_metrics()
                    last_system_update = current_time
                
                # Read sensors periodically
                if self.atlas and (current_time - last_reading_time > 10):  # Every 10 seconds
                    self._read_sensors()
                    last_reading_time = current_time
                
                # Check for alerts
                self._check_alerts()
                
                # Sleep briefly to prevent high CPU usage
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                self.system_state['errors'].append(f"Monitor error: {e}")
                time.sleep(5)  # Sleep longer on error
    
    def _read_sensors(self):
        """Read values from all sensors"""
        try:
            # Check if Atlas interface is initialized
            if self.atlas is None:
                logger.warning("Atlas interface not initialized, marking sensors as not detected")
                # Instead of simulated values, mark sensors as not detected
                ph = "sensor not detected"
                ec = "sensor not detected"
                tds = "sensor not detected"
                temp = "sensor not detected"
            else:
                # Get readings from Atlas sensors
                ph = self.atlas.read_ph()
                ec = self.atlas.read_ec()
                tds = self.atlas.read_tds()
                temp = self.atlas.read_temperature()
            
            # Update readings
            self.readings = {
                'ph': ph,
                'ec': ec,
                'tds': tds,
                'temperature': temp,
                'timestamp': datetime.now().isoformat()
            }
            
            # Update system state
            self.system_state['last_reading'] = self.readings['timestamp']
            
            # Log readings periodically
            if self.atlas is None:
                logger.debug("Sensor readings - all sensors not detected")
            else:
                logger.debug(f"Sensor readings - pH: {ph}, EC: {ec}, TDS: {tds}, Temp: {temp}")
            
            return self.readings
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
            
            # Ensure we have some values even on error
            if self.readings['timestamp'] is None:
                # Mark sensors as not detected instead of generating values
                self.readings = {
                    'ph': "sensor not detected",
                    'ec': "sensor not detected",
                    'tds': "sensor not detected",
                    'temperature': "sensor not detected",
                    'timestamp': datetime.now().isoformat()
                }
                self.system_state['last_reading'] = self.readings['timestamp']
            
            return self.readings
    
    def _update_system_metrics(self):
        """Update system metrics like uptime, load, etc."""
        try:
            # Calculate uptime
            uptime_seconds = (datetime.now() - datetime.fromisoformat(
                self.system_state['startup_time'])).total_seconds()
            self.system_state['uptime_seconds'] = uptime_seconds
            
            # Try to get system metrics if psutil is available
            try:
                import psutil
                self.system_state['system_load'] = psutil.cpu_percent()
                self.system_state['memory_usage'] = psutil.virtual_memory().percent
                self.system_state['disk_usage'] = psutil.disk_usage('/').percent
            except ImportError:
                # psutil not available, use simpler metrics
                self.system_state['system_load'] = 0
                self.system_state['memory_usage'] = 0
                self.system_state['disk_usage'] = 0
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions based on sensor readings"""
        if not self.readings['timestamp']:
            return  # No readings yet
        
        alerts_config = self.config_manager.get_setting('alerts', {})
        if not alerts_config.get('enabled', True):
            return  # Alerts disabled
        
        # Add an alert if sensors are not detected
        if (self.readings['ph'] == "sensor not detected" or 
            self.readings['ec'] == "sensor not detected" or 
            self.readings['tds'] == "sensor not detected" or 
            self.readings['temperature'] == "sensor not detected"):
            self._add_warning("One or more sensors not detected")
            return
        
        # Check pH alerts - only if it's a numeric value
        if isinstance(self.readings['ph'], (int, float)):
            if self.readings['ph'] < alerts_config.get('ph_min', 5.0):
                self._add_warning(f"pH too low: {self.readings['ph']}")
            elif self.readings['ph'] > alerts_config.get('ph_max', 7.0):
                self._add_warning(f"pH too high: {self.readings['ph']}")
        
        # Check EC alerts - only if it's a numeric value
        if isinstance(self.readings['ec'], (int, float)):
            if self.readings['ec'] < alerts_config.get('ec_min', 1.0):
                self._add_warning(f"EC too low: {self.readings['ec']}")
            elif self.readings['ec'] > alerts_config.get('ec_max', 3.0):
                self._add_warning(f"EC too high: {self.readings['ec']}")
        
        # Check temperature alerts - only if it's a numeric value
        if isinstance(self.readings['temperature'], (int, float)):
            if self.readings['temperature'] < alerts_config.get('temp_min', 15.0):
                self._add_warning(f"Temperature too low: {self.readings['temperature']}")
            elif self.readings['temperature'] > alerts_config.get('temp_max', 30.0):
                self._add_warning(f"Temperature too high: {self.readings['temperature']}")
    
    def _add_warning(self, message: str):
        """Add a warning to the system state"""
        timestamp = datetime.now().isoformat()
        warning = {
            'message': message,
            'timestamp': timestamp
        }
        
        # Avoid duplicate warnings
        for existing in self.system_state['warnings']:
            if existing['message'] == message:
                return
        
        # Add warning and log it
        self.system_state['warnings'].append(warning)
        logger.warning(message)
        
        # Limit warnings list to last 20
        if len(self.system_state['warnings']) > 20:
            self.system_state['warnings'] = self.system_state['warnings'][-20:]
    
    def _add_error(self, message: str):
        """Add an error to the system state"""
        timestamp = datetime.now().isoformat()
        error = {
            'message': message,
            'timestamp': timestamp
        }
        
        # Add error and log it
        self.system_state['errors'].append(error)
        logger.error(message)
        
        # Limit errors list to last 20
        if len(self.system_state['errors']) > 20:
            self.system_state['errors'] = self.system_state['errors'][-20:]
    
    def start_dosing(self):
        """Start automatic dosing"""
        try:
            if self.dosing_controller:
                self.dosing_controller.start()
                logger.info("Automatic dosing started")
                return True
            else:
                logger.error("Dosing controller not initialized")
                return False
        except Exception as e:
            logger.error(f"Error starting dosing: {e}")
            self._add_error(f"Failed to start dosing: {e}")
            return False
    
    def stop_dosing(self):
        """Stop automatic dosing"""
        try:
            if self.dosing_controller:
                self.dosing_controller.stop()
                logger.info("Automatic dosing stopped")
                return True
            else:
                logger.error("Dosing controller not initialized")
                return False
        except Exception as e:
            logger.error(f"Error stopping dosing: {e}")
            self._add_error(f"Failed to stop dosing: {e}")
            return False
    
    def get_readings(self) -> Dict[str, Any]:
        """Get current sensor readings
        
        Returns:
            Dict with current sensor readings
        """
        # If readings are outdated (> 30 seconds old), read sensors again
        if self.readings['timestamp'] is None or \
           (datetime.now() - datetime.fromisoformat(
               self.readings['timestamp'])).total_seconds() > 30:
            self._read_sensors()
        
        return self.readings
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status
        
        Returns:
            Dict with system status
        """
        # Update system metrics
        self._update_system_metrics()
        
        # Get current readings
        readings = self.get_readings()
        
        # Get dosing status
        if self.dosing_controller:
            dosing_status = self.dosing_controller.get_status()
            dosing_history = self.dosing_controller.get_dosing_history()
            dosing_settings = self.dosing_controller.get_settings()
        else:
            dosing_status = {"status": "not_initialized"}
            dosing_history = []
            dosing_settings = {}
        
        # Build complete status
        status = {
            'system': self.system_state,
            'readings': readings,
            'dosing': {
                'status': dosing_status,
                'history': dosing_history,
                'settings': dosing_settings
            }
        }
        
        return status
    
    def manual_dose(self, pump_name: str, volume_ml: float) -> bool:
        """Perform a manual dose
        
        Args:
            pump_name: Name of the pump ('ph_up', 'ph_down', 'nutrient_a', 'nutrient_b')
            volume_ml: Volume to dose in milliliters
            
        Returns:
            True if successful
        """
        try:
            if self.dosing_controller:
                result = self.dosing_controller.manual_dose(pump_name, volume_ml)
                logger.info(f"Manual dose: {pump_name}, {volume_ml}ml - result: {result}")
                return result
            else:
                logger.error("Dosing controller not initialized")
                return False
        except Exception as e:
            logger.error(f"Error performing manual dose: {e}")
            self._add_error(f"Failed to perform manual dose: {e}")
            return False
    
    def update_settings(self, section: str, settings: Dict[str, Any]) -> bool:
        """Update system settings
        
        Args:
            section: Settings section to update
            settings: New settings values
            
        Returns:
            True if successful
        """
        try:
            # Update in config manager
            if section in ['dosing', 'pumps', 'i2c', 'alerts']:
                self.config_manager.set_setting(section, settings)
                
                # Apply settings to appropriate component
                if section == 'dosing' and self.dosing_controller:
                    self.dosing_controller.update_settings(settings)
                
                logger.info(f"Updated {section} settings")
                return True
            else:
                logger.warning(f"Unknown settings section: {section}")
                return False
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            self._add_error(f"Failed to update settings: {e}")
            return False
    
    def calibrate_sensor(self, sensor_type: str, value: float) -> bool:
        """Calibrate a sensor
        
        Args:
            sensor_type: The sensor to calibrate ('ph', 'ec')
            value: The known value to calibrate to
            
        Returns:
            True if successful
        """
        try:
            if self.atlas:
                if sensor_type == 'ph':
                    result = self.atlas.calibrate_ph(value)
                elif sensor_type == 'ec':
                    result = self.atlas.calibrate_ec(value)
                else:
                    logger.warning(f"Unknown sensor type: {sensor_type}")
                    return False
                
                logger.info(f"Calibrated {sensor_type} sensor to {value} - result: {result}")
                return result
            else:
                logger.error("Atlas sensors not initialized")
                return False
        except Exception as e:
            logger.error(f"Error calibrating sensor: {e}")
            self._add_error(f"Failed to calibrate {sensor_type} sensor: {e}")
            return False
    
    def calibrate_pump(self, pump_name: str, volume_ml: float, time_sec: float) -> bool:
        """Calibrate a dosing pump
        
        Args:
            pump_name: The pump to calibrate ('ph_up', 'ph_down', 'nutrient_a', 'nutrient_b')
            volume_ml: The actual volume dispensed in ml
            time_sec: The time it took to dispense in seconds
            
        Returns:
            True if successful
        """
        try:
            if self.dosing_controller:
                result = self.dosing_controller.calibrate_pump(pump_name, volume_ml, time_sec)
                logger.info(f"Calibrated {pump_name} pump - flow rate: {volume_ml/time_sec:.2f} ml/sec")
                return result
            else:
                logger.error("Dosing controller not initialized")
                return False
        except Exception as e:
            logger.error(f"Error calibrating pump: {e}")
            self._add_error(f"Failed to calibrate {pump_name} pump: {e}")
            return False
    
    def export_data(self, export_path: str = None) -> str:
        """Export system data to a JSON file
        
        Args:
            export_path: Optional path to export to (if None, generates a timestamped path)
            
        Returns:
            Path to the exported file, or None if failed
        """
        try:
            if export_path is None:
                # Generate timestamped filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_dir = Path("/NuTetra/exports")
                try:
                    export_dir.mkdir(parents=True, exist_ok=True)
                except:
                    # Fallback to current directory
                    export_dir = Path("exports")
                    export_dir.mkdir(exist_ok=True)
                
                export_path = str(export_dir / f"nutetra_export_{timestamp}.json")
            
            # Get current system status
            status = self.get_system_status()
            
            # Add configuration
            export_data = {
                'status': status,
                'config': self.config_manager.config,
                'export_time': datetime.now().isoformat()
            }
            
            # Write to file
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=4)
            
            logger.info(f"Exported system data to {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            self._add_error(f"Failed to export data: {e}")
            return None
    
    def shutdown(self):
        """Gracefully shutdown the system"""
        logger.info("System shutdown initiated")
        
        # Signal monitor thread to stop
        self.shutdown_event.set()
        self.monitor_running = False
        
        # Stop dosing
        if self.dosing_controller:
            self.dosing_controller.stop()
        
        # Wait for monitor thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # Clean up resources
        if self.atlas:
            self.atlas.cleanup()
        
        logger.info("System shutdown complete")


if __name__ == "__main__":
    # Example usage when run directly
    system = SystemManager()
    
    try:
        # Start the system
        system.start_dosing()
        
        # Run for a while
        for _ in range(10):
            print(json.dumps(system.get_readings(), indent=2))
            time.sleep(10)
    
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Shutdown properly
        system.shutdown() 