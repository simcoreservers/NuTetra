#!/usr/bin/env python3
# NuTetra Sensor Manager
# Handles pH, EC (electrical conductivity), and temperature sensors

import time
import logging
import threading
from datetime import datetime

class SensorManager:
    def __init__(self, gpio_manager):
        self.logger = logging.getLogger("NuTetra.Sensors")
        self.logger.info("Initializing Sensor Manager")
        
        self.gpio = gpio_manager
        
        # Sensor pins (can be configured in config.json)
        self.pins = {
            'ph_data': 17,     # pH sensor data pin
            'ec_data': 27,     # EC sensor data pin
            'temp_data': 22,   # Temperature sensor data pin
        }
        
        # Sensor readings
        self.readings = {
            'ph': 7.0,            # Default neutral pH
            'ec': 0.0,            # EC in mS/cm
            'temperature': 20.0,  # Temperature in Celsius
            'last_update': datetime.now().isoformat()
        }
        
        # Calibration values
        self.calibration = {
            'ph': {
                'offset': 0.0,
                'scale': 1.0
            },
            'ec': {
                'offset': 0.0,
                'scale': 1.0
            },
            'temperature': {
                'offset': 0.0,
                'scale': 1.0
            }
        }
        
        # Monitoring thread
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start the sensor monitoring thread"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_sensors, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Sensor monitoring started")
        
    def stop_monitoring(self):
        """Stop the sensor monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        self.logger.info("Sensor monitoring stopped")
        
    def _monitor_sensors(self):
        """Background thread to continuously read sensors"""
        while self.monitoring:
            try:
                # Read all sensors
                self._read_ph_sensor()
                self._read_ec_sensor()
                self._read_temperature_sensor()
                
                # Update timestamp
                self.readings['last_update'] = datetime.now().isoformat()
                
                # Sleep for a short interval (don't read too frequently)
                time.sleep(2.0)
                
            except Exception as e:
                self.logger.error(f"Error in sensor monitoring: {e}")
                time.sleep(5.0)  # Longer delay on error
    
    def _read_ph_sensor(self):
        """Read and process pH sensor data"""
        try:
            # In a real implementation, this would read from an ADC
            # connected to a pH probe, but for this example we'll simulate
            
            # Simulated pH reading (would be replaced with actual sensor code)
            # For real implementation, might use Atlas Scientific pH sensor or similar
            raw_value = 512  # Simulated ADC value
            
            # Convert ADC value to pH and apply calibration
            voltage = (raw_value / 1023.0) * 5.0
            ph_value = 7.0 - ((2.5 - voltage) / 0.18)
            
            # Apply calibration
            calibrated_ph = (ph_value * self.calibration['ph']['scale']) + self.calibration['ph']['offset']
            
            # Update reading (with some noise for simulation)
            import random
            self.readings['ph'] = round(calibrated_ph + random.uniform(-0.05, 0.05), 2)
            self.logger.debug(f"pH reading: {self.readings['ph']}")
            
        except Exception as e:
            self.logger.error(f"Error reading pH sensor: {e}")
    
    def _read_ec_sensor(self):
        """Read and process EC (electrical conductivity) sensor data"""
        try:
            # Simulated EC reading (would be replaced with actual sensor code)
            # For real implementation, might use Atlas Scientific EC sensor or similar
            raw_value = 300  # Simulated ADC value
            
            # Convert ADC value to EC (mS/cm) and apply calibration
            voltage = (raw_value / 1023.0) * 5.0
            ec_value = voltage * 1.0  # Simple linear conversion for simulation
            
            # Apply calibration
            calibrated_ec = (ec_value * self.calibration['ec']['scale']) + self.calibration['ec']['offset']
            
            # Update reading (with some noise for simulation)
            import random
            self.readings['ec'] = round(calibrated_ec + random.uniform(-0.02, 0.02), 2)
            self.logger.debug(f"EC reading: {self.readings['ec']} mS/cm")
            
        except Exception as e:
            self.logger.error(f"Error reading EC sensor: {e}")
    
    def _read_temperature_sensor(self):
        """Read and process temperature sensor data"""
        try:
            # Simulated temperature reading (would be replaced with actual sensor code)
            # For real implementation, might use DS18B20 waterproof temperature sensor
            raw_value = 410  # Simulated ADC value
            
            # Convert ADC value to temperature and apply calibration
            voltage = (raw_value / 1023.0) * 5.0
            temp_value = (voltage - 0.5) * 100.0  # Simple linear conversion for simulation
            
            # Apply calibration
            calibrated_temp = (temp_value * self.calibration['temperature']['scale']) + self.calibration['temperature']['offset']
            
            # Update reading (with some noise for simulation)
            import random
            self.readings['temperature'] = round(calibrated_temp + random.uniform(-0.1, 0.1), 1)
            self.logger.debug(f"Temperature reading: {self.readings['temperature']}°C")
            
        except Exception as e:
            self.logger.error(f"Error reading temperature sensor: {e}")
    
    def get_readings(self):
        """Get the latest sensor readings"""
        return self.readings
    
    def calibrate_ph(self, solution_value, raw_reading):
        """Calibrate pH sensor using a buffer solution of known value"""
        self.logger.info(f"Calibrating pH sensor with solution value: {solution_value}")
        # Implement calibration logic based on the known solution value
        # This would adjust self.calibration['ph']['offset'] and self.calibration['ph']['scale']
        pass
    
    def calibrate_ec(self, solution_value, raw_reading):
        """Calibrate EC sensor using a solution of known value"""
        self.logger.info(f"Calibrating EC sensor with solution value: {solution_value} mS/cm")
        # Implement calibration logic based on the known solution value
        pass
    
    def calibrate_temperature(self, known_value, raw_reading):
        """Calibrate temperature sensor using a known value"""
        self.logger.info(f"Calibrating temperature sensor with known value: {known_value}°C")
        # Implement calibration logic based on the known temperature
        pass 