#!/usr/bin/env python3
# NuTetra Atlas Scientific Interface
# Interfaces with Atlas Scientific EZO circuits via the i3 InterLink Raspberry Pi Shield

import time
import logging
import smbus2
import threading
from typing import Dict, Any, Optional, List, Tuple

class AtlasI2C:
    """Atlas Scientific sensor interface using I2C"""
    
    # I2C default addresses for Atlas Scientific EZO circuits
    DEFAULT_ADDRESSES = {
        'pH': 0x63,       # 99 decimal
        'EC': 0x64,       # 100 decimal
        'RTD': 0x66,      # 102 decimal
        'DO': 0x61,       # 97 decimal (Dissolved Oxygen - not used but included)
        'ORP': 0x62,      # 98 decimal (Oxidation Reduction Potential - not used but included)
    }
    
    # Status codes
    SUCCESS = 1
    ERROR = 2
    NO_DATA = 3
    PENDING = 254
    
    def __init__(self, address: int, bus: int = 1):
        """Initialize the I2C device at the specified address."""
        self.address = address
        self.bus = smbus2.SMBus(bus)
        self.logger = logging.getLogger("NuTetra.Atlas")
        
    def write(self, cmd: str) -> None:
        """Send a command to the device."""
        try:
            self.bus.write_i2c_block_data(self.address, 0, [ord(c) for c in cmd])
            self.logger.debug(f"I2C write to {hex(self.address)}: {cmd}")
        except Exception as e:
            self.logger.error(f"I2C write error to {hex(self.address)}: {e}")
            raise
    
    def read(self, num_bytes: int = 31) -> str:
        """Read a response from the device."""
        try:
            response = self.bus.read_i2c_block_data(self.address, 0, num_bytes)
            response = [chr(x) for x in response if x != 0]
            response_str = "".join(response)
            self.logger.debug(f"I2C read from {hex(self.address)}: {response_str}")
            return response_str
        except Exception as e:
            self.logger.error(f"I2C read error from {hex(self.address)}: {e}")
            raise
    
    def query(self, cmd: str, delay_ms: int = 1000) -> str:
        """Write a command and read the response after the specified delay."""
        self.write(cmd)
        time.sleep(delay_ms / 1000)
        return self.read()
        
class AtlasSensorManager:
    """Manager class for Atlas Scientific sensors"""
    
    def __init__(self, bus: int = 1):
        """Initialize the sensor manager."""
        self.bus = bus
        self.sensors: Dict[str, AtlasI2C] = {}
        self.readings: Dict[str, Any] = {
            'pH': None,
            'EC': None,
            'temperature': None,
            'TDS': None,  # Calculated from EC
            'timestamp': None,
            'pH_mv': None,  # Raw millivolt reading from pH sensor
            'EC_ms': None,  # Raw millisiemens reading
        }
        self.calibration_status: Dict[str, Dict[str, bool]] = {
            'pH': {'low': False, 'mid': False, 'high': False},
            'EC': {'dry': False, 'low': False, 'high': False},
            'RTD': {'confirmed': False}
        }
        self.temperature_compensation = 25.0  # Default temperature compensation (°C)
        self.logger = logging.getLogger("NuTetra.Atlas")
        self.lock = threading.RLock()  # For thread safety
        self._setup_sensors()
    
    def _setup_sensors(self) -> None:
        """Initialize all sensors."""
        with self.lock:
            try:
                # Initialize the standard sensors
                self.sensors['pH'] = AtlasI2C(AtlasI2C.DEFAULT_ADDRESSES['pH'], self.bus)
                self.sensors['EC'] = AtlasI2C(AtlasI2C.DEFAULT_ADDRESSES['EC'], self.bus)
                self.sensors['RTD'] = AtlasI2C(AtlasI2C.DEFAULT_ADDRESSES['RTD'], self.bus)
                
                # Set up sensors with initial commands
                self._setup_sensor('RTD', ["i"])  # Identify the RTD sensor
                self._setup_sensor('pH', ["i", "L,0"])  # Identify pH and turn off LED
                self._setup_sensor('EC', ["i", "L,0", "O,EC,1", "O,TDS,1", "O,S,0"])  # Enable EC & TDS, disable salinity
                
                # Check if all sensors responded
                self.check_sensors_status()
                
                # Apply temperature compensation
                self.update_temp_compensation(self.temperature_compensation)
                
                self.logger.info("Atlas Scientific sensors initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing Atlas Scientific sensors: {e}")
                raise
    
    def _setup_sensor(self, sensor_type: str, commands: List[str]) -> None:
        """Send a series of setup commands to a specific sensor."""
        if sensor_type not in self.sensors:
            self.logger.error(f"Sensor {sensor_type} not found")
            return
            
        for cmd in commands:
            try:
                response = self.sensors[sensor_type].query(cmd)
                self.logger.debug(f"{sensor_type} setup command '{cmd}' response: {response}")
                time.sleep(0.3)  # Short delay between commands
            except Exception as e:
                self.logger.error(f"Error setting up {sensor_type} with command '{cmd}': {e}")
    
    def check_sensors_status(self) -> Dict[str, bool]:
        """Check if all sensors are responsive."""
        status = {}
        
        with self.lock:
            for name, sensor in self.sensors.items():
                try:
                    # Sends an identify command and checks response
                    response = sensor.query("i")
                    status[name] = response.startswith("?I")
                    self.logger.debug(f"Sensor {name} status: {'OK' if status[name] else 'FAIL'}")
                except Exception as e:
                    self.logger.error(f"Error checking {name} sensor status: {e}")
                    status[name] = False
        
        return status
    
    def update_temp_compensation(self, temp: float) -> None:
        """Update temperature compensation for pH and EC sensors."""
        with self.lock:
            temp_str = f"{temp:.2f}"
            try:
                # Send temperature compensation to pH sensor
                response = self.sensors['pH'].query(f"T,{temp_str}")
                self.logger.debug(f"pH temperature compensation set to {temp_str}°C: {response}")
                
                # Send temperature compensation to EC sensor
                response = self.sensors['EC'].query(f"T,{temp_str}")
                self.logger.debug(f"EC temperature compensation set to {temp_str}°C: {response}")
                
                self.temperature_compensation = temp
            except Exception as e:
                self.logger.error(f"Failed to update temperature compensation: {e}")
    
    def read_temperature(self) -> Optional[float]:
        """Read the current temperature from the RTD sensor."""
        with self.lock:
            try:
                response = self.sensors['RTD'].query("R")
                if response:
                    temp = float(response)
                    self.readings['temperature'] = temp
                    self.readings['timestamp'] = time.time()
                    self.update_temp_compensation(temp)
                    self.logger.debug(f"Temperature reading: {temp}°C")
                    return temp
                return None
            except Exception as e:
                self.logger.error(f"Failed to read temperature: {e}")
                return None
    
    def read_ph(self) -> Optional[float]:
        """Read the current pH value."""
        with self.lock:
            try:
                response = self.sensors['pH'].query("R")
                if response:
                    ph = float(response)
                    self.readings['pH'] = ph
                    self.readings['timestamp'] = time.time()
                    self.logger.debug(f"pH reading: {ph}")
                    return ph
                return None
            except Exception as e:
                self.logger.error(f"Failed to read pH: {e}")
                return None
    
    def read_ph_mv(self) -> Optional[float]:
        """Read the raw millivolt reading from the pH sensor."""
        with self.lock:
            try:
                response = self.sensors['pH'].query("MV")
                if response:
                    mv = float(response)
                    self.readings['pH_mv'] = mv
                    self.logger.debug(f"pH millivolt reading: {mv}mV")
                    return mv
                return None
            except Exception as e:
                self.logger.error(f"Failed to read pH millivolts: {e}")
                return None
                
    def read_ec(self) -> Tuple[Optional[float], Optional[float]]:
        """Read the current EC and TDS values."""
        with self.lock:
            try:
                response = self.sensors['EC'].query("R")
                if response:
                    values = response.split(",")
                    if len(values) >= 2:
                        ec = float(values[0])
                        tds = float(values[1])
                        self.readings['EC'] = ec
                        self.readings['TDS'] = tds
                        self.readings['EC_ms'] = ec / 1000.0  # Convert to millisiemens
                        self.readings['timestamp'] = time.time()
                        self.logger.debug(f"EC reading: {ec}µS/cm, TDS: {tds}ppm")
                        return ec, tds
                return None, None
            except Exception as e:
                self.logger.error(f"Failed to read EC: {e}")
                return None, None
    
    def read_all(self) -> Dict[str, Any]:
        """Read all sensor values and return current readings."""
        # Temperature should be read first to update compensation
        self.read_temperature()
        self.read_ph()
        self.read_ec()
        self.read_ph_mv()
        
        return self.readings
    
    def calibrate_ph(self, point: str, value: float) -> bool:
        """
        Calibrate the pH sensor.
        point: 'low', 'mid', or 'high'
        value: the calibration value (e.g., 4.01, 7.00, 10.00)
        """
        with self.lock:
            point_map = {'low': 'L', 'mid': 'M', 'high': 'H'}
            if point not in point_map:
                self.logger.error(f"Invalid pH calibration point: {point}")
                return False
            
            try:
                cmd = f"Cal,{point_map[point]},{value:.2f}"
                response = self.sensors['pH'].query(cmd, delay_ms=1600)  # Extended delay for calibration
                
                success = 'OK' in response
                if success:
                    self.calibration_status['pH'][point] = True
                    self.logger.info(f"pH calibration at {point} point ({value}) successful")
                else:
                    self.logger.error(f"pH calibration failed: {response}")
                
                return success
            except Exception as e:
                self.logger.error(f"Error during pH calibration: {e}")
                return False
    
    def calibrate_ec(self, point: str, value: Optional[float] = None) -> bool:
        """
        Calibrate the EC sensor.
        point: 'dry', 'low', or 'high'
        value: the calibration value (e.g., 12880, 1413). Not needed for 'dry'.
        """
        with self.lock:
            try:
                if point == 'dry':
                    cmd = "Cal,dry"
                elif point in ['low', 'high']:
                    if value is None:
                        self.logger.error(f"Calibration value required for {point} point")
                        return False
                    cmd = f"Cal,{value}"
                else:
                    self.logger.error(f"Invalid EC calibration point: {point}")
                    return False
                
                response = self.sensors['EC'].query(cmd, delay_ms=1600)  # Extended delay for calibration
                
                success = 'OK' in response
                if success:
                    self.calibration_status['EC'][point] = True
                    self.logger.info(f"EC calibration at {point} point successful")
                else:
                    self.logger.error(f"EC calibration failed: {response}")
                
                return success
            except Exception as e:
                self.logger.error(f"Error during EC calibration: {e}")
                return False
    
    def calibrate_rtd(self, value: float) -> bool:
        """Calibrate the RTD temperature sensor to a known value."""
        with self.lock:
            try:
                cmd = f"Cal,{value:.2f}"
                response = self.sensors['RTD'].query(cmd, delay_ms=1600)  # Extended delay for calibration
                
                success = 'OK' in response
                if success:
                    self.calibration_status['RTD']['confirmed'] = True
                    self.logger.info(f"RTD calibration to {value}°C successful")
                else:
                    self.logger.error(f"RTD calibration failed: {response}")
                
                return success
            except Exception as e:
                self.logger.error(f"Error during RTD calibration: {e}")
                return False
    
    def get_calibration_status(self) -> Dict[str, Dict[str, bool]]:
        """Get the calibration status of all sensors."""
        return self.calibration_status
    
    def factory_reset(self, sensor_type: str) -> bool:
        """Factory reset a sensor."""
        if sensor_type not in self.sensors:
            self.logger.error(f"Sensor {sensor_type} not found")
            return False
            
        with self.lock:
            try:
                response = self.sensors[sensor_type].query("Factory")
                success = 'OK' in response
                
                if success:
                    self.logger.info(f"{sensor_type} factory reset successful")
                    # Reset calibration status for this sensor
                    if sensor_type == 'RTD':
                        self.calibration_status[sensor_type] = {'confirmed': False}
                    else:
                        for key in self.calibration_status[sensor_type]:
                            self.calibration_status[sensor_type][key] = False
                else:
                    self.logger.error(f"{sensor_type} factory reset failed: {response}")
                
                return success
            except Exception as e:
                self.logger.error(f"Error during {sensor_type} factory reset: {e}")
                return False
    
    def get_device_info(self, sensor_type: str) -> Dict[str, str]:
        """Get detailed device information for a sensor."""
        if sensor_type not in self.sensors:
            self.logger.error(f"Sensor {sensor_type} not found")
            return {'error': 'Sensor not found'}
            
        info = {
            'type': sensor_type,
            'address': hex(self.sensors[sensor_type].address),
            'status': 'unknown',
            'version': 'unknown',
            'voltage': 'unknown'
        }
            
        with self.lock:
            try:
                # Get device info
                response = self.sensors[sensor_type].query("i")
                info['status'] = 'online' if response.startswith("?I") else 'offline'
                info['version'] = response.replace("?I,", "")
                
                # Get voltage
                response = self.sensors[sensor_type].query("Status")
                if "," in response:
                    info['voltage'] = response.split(",")[1] + "V"
                
                return info
            except Exception as e:
                self.logger.error(f"Error getting {sensor_type} device info: {e}")
                info['status'] = f'error: {str(e)}'
                return info

# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        manager = AtlasSensorManager()
        
        # Check if sensors are connected
        status = manager.check_sensors_status()
        print("Sensor Status:", status)
        
        # Example: Read all sensors
        if all(status.values()):
            readings = manager.read_all()
            print(f"Temperature: {readings.get('temperature')}°C")
            print(f"pH: {readings.get('pH')}")
            print(f"EC: {readings.get('EC')}µS/cm")
            print(f"TDS: {readings.get('TDS')}ppm")
    except Exception as e:
        print(f"Error: {e}") 