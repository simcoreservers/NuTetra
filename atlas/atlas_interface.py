#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Atlas Scientific Sensor Interface
Interfaces with Atlas Scientific pH, EC, and temperature sensors via I2C
"""
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("NuTetra.Atlas")

# Atlas Scientific I2C addresses (default)
ATLAS_SENSOR_ADDRESSES = {
    'pH': 0x63,    # Default pH sensor address
    'EC': 0x64,    # Default EC sensor address
    'TEMP': 0x66,  # Default temperature sensor address
    'RTD': 0x66,   # Alternative name for temperature probe
}

# Atlas command codes
ATLAS_COMMANDS = {
    'READ': 'R',        # Read current sensor value
    'CALIBRATE': 'Cal', # Calibrate sensor
    'FACTORY': 'X',     # Factory reset
    'INFO': 'I',        # Get device information
    'STATUS': 'Status', # Get calibration status
    'SLEEP': 'Sleep',   # Put device to sleep
    'TEMP_COMP': 'T',   # Set temperature compensation
}

class AtlasInterface:
    """Interface for Atlas Scientific sensors via I2C"""
    
    def __init__(self, config):
        """Initialize the Atlas interface
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.i2c_config = self.config.get_setting('i2c', {})
        
        # Default I2C settings if not in config
        self.i2c_bus = self.i2c_config.get('bus', 1)  # Default to I2C bus 1
        self.enabled = self.i2c_config.get('enabled', True)
        
        # Custom addresses if configured
        self.addresses = {
            'pH': self.i2c_config.get('ph_address', ATLAS_SENSOR_ADDRESSES['pH']),
            'EC': self.i2c_config.get('ec_address', ATLAS_SENSOR_ADDRESSES['EC']),
            'TEMP': self.i2c_config.get('temp_address', ATLAS_SENSOR_ADDRESSES['TEMP']),
        }
        
        # Sensor state
        self.lock = threading.RLock()
        self.last_readings = {
            'pH': {'value': 7.0, 'timestamp': 0},
            'EC': {'value': 1.5, 'timestamp': 0},
            'TDS': {'value': 750, 'timestamp': 0},
            'TEMP': {'value': 25.0, 'timestamp': 0}
        }
        
        # Cache time in seconds
        self.cache_time = self.i2c_config.get('cache_time', 2.0)
        
        # Temperature compensation
        self.temp_compensation = 25.0  # Default temperature compensation
        
        # I2C interface
        self.i2c = None
        self.simulation_mode = False
        
        # Try to initialize I2C
        success = self._init_i2c()
        if not success:
            logger.warning("Failed to initialize I2C. Running in simulation mode.")
            self.simulation_mode = True
        
        logger.info("Atlas sensor interface initialized")
    
    def _init_i2c(self) -> bool:
        """Initialize the I2C interface
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("I2C interface disabled in configuration")
            self.simulation_mode = True
            return False
        
        try:
            # Try to import smbus2
            import smbus2
            
            # Open I2C bus
            try:
                self.i2c = smbus2.SMBus(self.i2c_bus)
                logger.info(f"I2C initialized on bus {self.i2c_bus}")
                
                # Test if sensors are responsive
                if self._device_info('pH') and self._device_info('EC') and self._device_info('TEMP'):
                    logger.info("All Atlas sensors detected")
                else:
                    logger.warning("Some Atlas sensors not detected")
                
                return True
            except Exception as e:
                logger.error(f"Error opening I2C bus {self.i2c_bus}: {e}")
                return False
            
        except ImportError:
            logger.error("smbus2 module not available. Install with 'pip install smbus2'")
            return False
    
    def initialize(self):
        """Initialize sensors and apply temperature compensation"""
        if self.simulation_mode:
            logger.info("Simulation mode: Skipping sensor initialization")
            return
        
        try:
            logger.info("Initializing Atlas sensors...")
            
            # Try to get device information
            ph_info = self._device_info('pH')
            ec_info = self._device_info('EC')
            temp_info = self._device_info('TEMP')
            
            if ph_info:
                logger.info(f"pH sensor: {ph_info}")
            if ec_info:
                logger.info(f"EC sensor: {ec_info}")
            if temp_info:
                logger.info(f"Temperature sensor: {temp_info}")
            
            # Get initial temperature reading for compensation
            temp = self._read_temperature()
            if temp is not None and 0 < temp < 50:
                self.temp_compensation = temp
                # Set temperature compensation on pH and EC sensors
                self._set_temperature_compensation('pH', temp)
                self._set_temperature_compensation('EC', temp)
            
            logger.info("Atlas sensors initialized")
            
        except Exception as e:
            logger.error(f"Error initializing Atlas sensors: {e}")
    
    def _device_info(self, device_type: str) -> Optional[str]:
        """Get device information
        
        Args:
            device_type: The type of device ('pH', 'EC', 'TEMP')
            
        Returns:
            str: Device information or None if error
        """
        if self.simulation_mode:
            return f"Simulated {device_type} sensor"
        
        if device_type not in self.addresses:
            return None
        
        try:
            address = self.addresses[device_type]
            return self._send_command(address, ATLAS_COMMANDS['INFO'])
        except Exception as e:
            logger.error(f"Error getting {device_type} device info: {e}")
            return None
    
    def _send_command(self, address: int, command: str) -> Optional[str]:
        """Send command to Atlas sensor and get response
        
        Args:
            address: I2C address of the sensor
            command: Command to send
            
        Returns:
            str: Response from sensor or None if error
        """
        try:
            # Send command to device
            cmd_bytes = command.encode() + b'\r'
            self.i2c.write_i2c_block_data(address, 0, list(cmd_bytes))
            
            # Wait for processing
            time.sleep(0.3)  # Most commands need ~300ms
            
            # Read response (first byte is response length)
            data = self.i2c.read_i2c_block_data(address, 0, 31)
            length = data[0]
            
            # Convert response to string
            response = bytearray(data[1:1+length]).decode().rstrip('\0\r')
            return response
            
        except Exception as e:
            logger.error(f"I2C command error (addr: 0x{address:02x}, cmd: {command}): {e}")
            return None
    
    def _set_temperature_compensation(self, device_type: str, temp: float) -> bool:
        """Set temperature compensation for pH and EC sensors
        
        Args:
            device_type: The type of device ('pH' or 'EC')
            temp: Temperature in Celsius
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.simulation_mode:
            return True
        
        if device_type not in ['pH', 'EC']:
            return False
        
        try:
            address = self.addresses[device_type]
            command = f"{ATLAS_COMMANDS['TEMP_COMP']},{temp:.2f}"
            response = self._send_command(address, command)
            
            if response:
                logger.info(f"Set temperature compensation for {device_type} to {temp:.2f}°C")
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting temperature compensation for {device_type}: {e}")
            return False
    
    def _read_ph(self) -> Optional[float]:
        """Read pH value from sensor
        
        Returns:
            float: pH value or None if error
        """
        if self.simulation_mode:
            # Simulate pH between 5.5 and 7.0 with some noise
            import random
            return round(6.0 + random.uniform(-0.5, 1.0), 2)
        
        try:
            address = self.addresses['pH']
            response = self._send_command(address, ATLAS_COMMANDS['READ'])
            
            if response:
                return float(response)
            return None
        except Exception as e:
            logger.error(f"Error reading pH: {e}")
            return None
    
    def _read_ec(self) -> Optional[float]:
        """Read EC value from sensor
        
        Returns:
            float: EC value in mS/cm or None if error
        """
        if self.simulation_mode:
            # Simulate EC between 1.0 and 2.0 with some noise
            import random
            return round(1.5 + random.uniform(-0.5, 0.5), 2)
        
        try:
            address = self.addresses['EC']
            response = self._send_command(address, ATLAS_COMMANDS['READ'])
            
            if response:
                # Parse response - could contain EC,TDS,SAL,SG
                parts = response.split(',')
                return float(parts[0])
            return None
        except Exception as e:
            logger.error(f"Error reading EC: {e}")
            return None
    
    def _read_tds(self) -> Optional[int]:
        """Read TDS value from EC sensor
        
        Returns:
            int: TDS value in ppm or None if error
        """
        if self.simulation_mode:
            # Simulate TDS between 500 and 1000 ppm with some noise
            import random
            return int(750 + random.uniform(-250, 250))
        
        try:
            address = self.addresses['EC']
            response = self._send_command(address, ATLAS_COMMANDS['READ'])
            
            if response:
                # Parse response - could contain EC,TDS,SAL,SG
                parts = response.split(',')
                if len(parts) >= 2:
                    return int(float(parts[1]))
                else:
                    # Calculate TDS from EC if not provided
                    ec = float(parts[0])
                    return int(ec * 500)  # Approximate conversion
            return None
        except Exception as e:
            logger.error(f"Error reading TDS: {e}")
            return None
    
    def _read_temperature(self) -> Optional[float]:
        """Read temperature value from sensor
        
        Returns:
            float: Temperature in Celsius or None if error
        """
        if self.simulation_mode:
            # Simulate temperature between 20 and 25°C with some noise
            import random
            return round(22.5 + random.uniform(-2.5, 2.5), 1)
        
        try:
            address = self.addresses['TEMP']
            response = self._send_command(address, ATLAS_COMMANDS['READ'])
            
            if response:
                return float(response)
            return None
        except Exception as e:
            logger.error(f"Error reading temperature: {e}")
            return None
    
    def _update_temperature_compensation(self):
        """Update temperature compensation for pH and EC sensors"""
        temp = self.get_temperature()
        if temp is not None and 0 < temp < 50:
            self.temp_compensation = temp
            self._set_temperature_compensation('pH', temp)
            self._set_temperature_compensation('EC', temp)
    
    def get_ph(self) -> float:
        """Get pH value, reading from sensor if cache has expired
        
        Returns:
            float: pH value
        """
        with self.lock:
            current_time = time.time()
            if current_time - self.last_readings['pH']['timestamp'] > self.cache_time:
                # Update temperature compensation first
                self._update_temperature_compensation()
                
                # Read new value
                ph = self._read_ph()
                if ph is not None:
                    self.last_readings['pH'] = {
                        'value': ph,
                        'timestamp': current_time
                    }
            
            return self.last_readings['pH']['value']
    
    def get_ec(self) -> float:
        """Get EC value, reading from sensor if cache has expired
        
        Returns:
            float: EC value in mS/cm
        """
        with self.lock:
            current_time = time.time()
            if current_time - self.last_readings['EC']['timestamp'] > self.cache_time:
                # Update temperature compensation first
                self._update_temperature_compensation()
                
                # Read new value
                ec = self._read_ec()
                if ec is not None:
                    self.last_readings['EC'] = {
                        'value': ec,
                        'timestamp': current_time
                    }
            
            return self.last_readings['EC']['value']
    
    def get_tds(self) -> int:
        """Get TDS value, reading from sensor if cache has expired
        
        Returns:
            int: TDS value in ppm
        """
        with self.lock:
            current_time = time.time()
            if current_time - self.last_readings['TDS']['timestamp'] > self.cache_time:
                # If EC has been recently updated, calculate from EC
                if current_time - self.last_readings['EC']['timestamp'] <= self.cache_time:
                    ec = self.last_readings['EC']['value']
                    tds = int(ec * 500)  # Approximate conversion
                    self.last_readings['TDS'] = {
                        'value': tds,
                        'timestamp': current_time
                    }
                else:
                    # Update temperature compensation first
                    self._update_temperature_compensation()
                    
                    # Read new value
                    tds = self._read_tds()
                    if tds is not None:
                        self.last_readings['TDS'] = {
                            'value': tds,
                            'timestamp': current_time
                        }
            
            return self.last_readings['TDS']['value']
    
    def get_temperature(self) -> float:
        """Get temperature value, reading from sensor if cache has expired
        
        Returns:
            float: Temperature in Celsius
        """
        with self.lock:
            current_time = time.time()
            if current_time - self.last_readings['TEMP']['timestamp'] > self.cache_time:
                # Read new value
                temp = self._read_temperature()
                if temp is not None:
                    self.last_readings['TEMP'] = {
                        'value': temp,
                        'timestamp': current_time
                    }
            
            return self.last_readings['TEMP']['value']
    
    def get_ph_calibration_status(self) -> Dict[str, Any]:
        """Get pH sensor calibration status
        
        Returns:
            Dict with calibration status information
        """
        if self.simulation_mode:
            return {
                'calibrated': True,
                'mid': True,
                'low': True,
                'high': True
            }
        
        try:
            address = self.addresses['pH']
            response = self._send_command(address, ATLAS_COMMANDS['STATUS'])
            
            if response:
                # Parse calibration status response
                # Format is typically: "?STATUS,X,Y,Z" where X,Y,Z are pH values or 0
                parts = response.strip('?STATUS,').split(',')
                
                # Convert to meaningful status
                status = {
                    'calibrated': any(float(p) > 0 for p in parts),
                }
                
                # Add calibration points if available
                if len(parts) >= 3:
                    if float(parts[0]) > 0:
                        status['mid'] = parts[0]
                    if float(parts[1]) > 0:
                        status['low'] = parts[1]
                    if float(parts[2]) > 0:
                        status['high'] = parts[2]
                
                return status
            else:
                return {'calibrated': False, 'error': 'No response from sensor'}
                
        except Exception as e:
            logger.error(f"Error getting pH calibration status: {e}")
            return {'calibrated': False, 'error': str(e)}
    
    def get_ec_calibration_status(self) -> Dict[str, Any]:
        """Get EC sensor calibration status
        
        Returns:
            Dict with calibration status information
        """
        if self.simulation_mode:
            return {
                'calibrated': True,
                'dry': True,
                'single': "1.413"
            }
        
        try:
            address = self.addresses['EC']
            response = self._send_command(address, ATLAS_COMMANDS['STATUS'])
            
            if response:
                # Parse calibration status response
                # Format is typically: "?STATUS,DRY,X,Y,Z" where X,Y,Z are EC values or 0
                parts = response.strip('?STATUS,').split(',')
                
                # Convert to meaningful status
                status = {
                    'calibrated': any(p != '0' for p in parts[1:]) or parts[0] == '1',
                }
                
                # Add calibration points if available
                if parts[0] == '1':
                    status['dry'] = True
                
                # Add any non-zero calibration points
                for point in parts[1:]:
                    if point != '0':
                        if float(point) < 1.0:
                            status['low'] = point
                        elif float(point) < 5.0:
                            status['single'] = point
                        else:
                            status['high'] = point
                
                return status
            else:
                return {'calibrated': False, 'error': 'No response from sensor'}
                
        except Exception as e:
            logger.error(f"Error getting EC calibration status: {e}")
            return {'calibrated': False, 'error': str(e)}
    
    def get_temperature_calibration_status(self) -> Dict[str, Any]:
        """Get temperature sensor calibration status
        
        Returns:
            Dict with calibration status information
        """
        if self.simulation_mode:
            return {
                'calibrated': True,
                'value': "25.0"
            }
        
        try:
            # Temperature sensors don't typically report calibration status
            # We'll check if the sensor is working properly
            temp = self._read_temperature()
            
            if temp is not None:
                return {
                    'calibrated': True,
                    'value': f"{temp:.1f}"
                }
            else:
                return {'calibrated': False, 'error': 'No response from sensor'}
                
        except Exception as e:
            logger.error(f"Error checking temperature sensor: {e}")
            return {'calibrated': False, 'error': str(e)}
    
    def calibrate_ph(self, point: str, value: float) -> bool:
        """Calibrate pH sensor
        
        Args:
            point: Calibration point ('low', 'mid', or 'high')
            value: Calibration value
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.simulation_mode:
            logger.info(f"Simulation: Calibrated pH sensor at {point} point with value {value}")
            return True
        
        try:
            address = self.addresses['pH']
            
            # Update temperature compensation first
            self._update_temperature_compensation()
            
            # Determine calibration command
            command = f"{ATLAS_COMMANDS['CALIBRATE']},"
            
            if point == 'mid':
                command += "mid," + str(value)
            elif point == 'low':
                command += "low," + str(value)
            elif point == 'high':
                command += "high," + str(value)
            else:
                logger.error(f"Invalid pH calibration point: {point}")
                return False
            
            # Send calibration command
            response = self._send_command(address, command)
            
            if response:
                logger.info(f"Calibrated pH sensor at {point} point with value {value}")
                # Invalidate cache
                self.last_readings['pH']['timestamp'] = 0
                return True
            else:
                logger.error(f"pH calibration failed at {point} point")
                return False
                
        except Exception as e:
            logger.error(f"Error calibrating pH sensor: {e}")
            return False
    
    def calibrate_ec(self, point: str, value: float = 0) -> bool:
        """Calibrate EC sensor
        
        Args:
            point: Calibration point ('dry', 'low', 'single', or 'high')
            value: Calibration value (not needed for 'dry')
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.simulation_mode:
            logger.info(f"Simulation: Calibrated EC sensor at {point} point with value {value}")
            return True
        
        try:
            address = self.addresses['EC']
            
            # Update temperature compensation first
            self._update_temperature_compensation()
            
            # Determine calibration command
            command = f"{ATLAS_COMMANDS['CALIBRATE']},"
            
            if point == 'dry':
                command += "dry"
            elif point == 'low':
                command += "low," + str(value)
            elif point == 'single' or point == 'one':
                command += str(value)
            elif point == 'high':
                command += "high," + str(value)
            else:
                logger.error(f"Invalid EC calibration point: {point}")
                return False
            
            # Send calibration command
            response = self._send_command(address, command)
            
            if response:
                logger.info(f"Calibrated EC sensor at {point} point with value {value}")
                # Invalidate cache
                self.last_readings['EC']['timestamp'] = 0
                self.last_readings['TDS']['timestamp'] = 0
                return True
            else:
                logger.error(f"EC calibration failed at {point} point")
                return False
                
        except Exception as e:
            logger.error(f"Error calibrating EC sensor: {e}")
            return False
    
    def calibrate_temperature(self, value: float) -> bool:
        """Calibrate temperature sensor
        
        Args:
            value: Temperature calibration value
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.simulation_mode:
            logger.info(f"Simulation: Calibrated temperature sensor with value {value}")
            return True
        
        try:
            address = self.addresses['TEMP']
            
            # Temperature sensor calibration (single point)
            command = f"{ATLAS_COMMANDS['CALIBRATE']},{value:.2f}"
            
            # Send calibration command
            response = self._send_command(address, command)
            
            if response:
                logger.info(f"Calibrated temperature sensor with value {value}")
                # Invalidate cache
                self.last_readings['TEMP']['timestamp'] = 0
                # Update compensation
                self.temp_compensation = value
                self._set_temperature_compensation('pH', value)
                self._set_temperature_compensation('EC', value)
                return True
            else:
                logger.error(f"Temperature calibration failed")
                return False
                
        except Exception as e:
            logger.error(f"Error calibrating temperature sensor: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up Atlas interface")
        
        if self.simulation_mode:
            return
        
        try:
            # No specific cleanup needed for I2C other than closing the bus
            if self.i2c:
                # Put sensors to sleep to save power
                for device_type in ['pH', 'EC', 'TEMP']:
                    try:
                        address = self.addresses[device_type]
                        self._send_command(address, ATLAS_COMMANDS['SLEEP'])
                        logger.info(f"Put {device_type} sensor to sleep")
                    except:
                        pass
                
                # Close I2C bus (will be closed automatically when object is destroyed)
                # self.i2c.close()  # This method is not available in smbus2
                self.i2c = None
                
        except Exception as e:
            logger.error(f"Error cleaning up Atlas interface: {e}") 