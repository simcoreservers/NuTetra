#!/usr/bin/env python3
# NuTetra Pump Manager
# Controls dosing pumps via GPIO or motor controller

import time
import logging
import asyncio
import threading
import os
import platform
from typing import Dict, Any, Optional, List, Tuple

try:
    import rpi_lgpio as lgpio  # Import rpi-lgpio for Raspberry Pi 5
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import lgpio  # Fallback to standard lgpio
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False
        print("WARNING: lgpio not available, running in simulation mode")

class PumpManager:
    """
    Manages the dosing pumps for the NuTetra system.
    
    Features:
    - Controls peristaltic pumps for pH up, pH down, nutrient A, and nutrient B
    - Calibration and flow rate management
    - Safety limits and timeout protection
    """
    
    # Pump states
    IDLE = 'idle'
    RUNNING = 'running'
    ERROR = 'error'
    
    def __init__(self, config_manager, simulation_mode: bool = not GPIO_AVAILABLE):
        """
        Initialize the pump manager.
        
        Args:
            config_manager: System configuration manager
            simulation_mode: If True, simulate pump actions instead of using GPIO
        """
        self.logger = logging.getLogger("NuTetra.Pumps")
        self.config = config_manager
        self.simulation_mode = simulation_mode
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # For lgpio: handle to GPIO chip
        self.chip = None
        self.chip_num = 4  # Default to gpiochip4 for Raspberry Pi 5
        
        # Try to detect Raspberry Pi version
        if not simulation_mode:
            self._detect_gpio_chip()
        
        # Default pump configuration
        self.pumps = {
            'ph_up': {
                'pin': 17,           # GPIO pin number
                'flow_rate': 1.0,    # ml per second
                'calibration': 1.0,  # Calibration factor
                'state': self.IDLE,
                'max_run_time': 60,  # Maximum continuous run time in seconds
                'reverse_logic': False  # True if pump activates on LOW
            },
            'ph_down': {
                'pin': 27,
                'flow_rate': 1.0,
                'calibration': 1.0,
                'state': self.IDLE,
                'max_run_time': 60,
                'reverse_logic': False
            },
            'nutrient_a': {
                'pin': 22,
                'flow_rate': 1.0,
                'calibration': 1.0,
                'state': self.IDLE,
                'max_run_time': 60,
                'reverse_logic': False
            },
            'nutrient_b': {
                'pin': 23,
                'flow_rate': 1.0,
                'calibration': 1.0,
                'state': self.IDLE,
                'max_run_time': 60,
                'reverse_logic': False
            },
            'main': {  # Main circulation pump
                'pin': 24,
                'state': self.IDLE,
                'max_run_time': 3600,  # 1 hour
                'reverse_logic': False
            }
        }
        
        # Running status
        self.active_pumps = {}  # Track which pumps are currently running
        
        # Load configuration
        self._load_config()
        
        # Initialize GPIO if not in simulation mode
        if not self.simulation_mode:
            self._setup_gpio()
    
    def _detect_gpio_chip(self):
        """Detect the appropriate GPIO chip number based on Raspberry Pi version."""
        try:
            # Try to determine if this is a Raspberry Pi 5
            is_pi5 = False
            
            # Check if /proc/device-tree/model exists (common on Raspberry Pi)
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read()
                    if 'Raspberry Pi 5' in model:
                        is_pi5 = True
                        self.logger.info("Detected Raspberry Pi 5")
            
            # Check if gpiochip4 exists (Pi 5) or gpiochip0 (older Pi models)
            if is_pi5 or os.path.exists('/dev/gpiochip4'):
                self.chip_num = 4  # Pi 5 uses gpiochip4
                self.logger.info("Using gpiochip4 for GPIO control")
            else:
                self.chip_num = 0  # Older Pi models use gpiochip0
                self.logger.info("Using gpiochip0 for GPIO control")
                
        except Exception as e:
            self.logger.warning(f"Error detecting GPIO chip: {e}, defaulting to gpiochip4")
            self.chip_num = 4  # Default to Pi 5 setting
    
    def _load_config(self):
        """Load pump configuration from config manager."""
        try:
            pump_config = self.config.get_setting('pumps', {})
            
            # Update configuration for each pump
            for pump_name, pump_data in pump_config.items():
                if pump_name in self.pumps:
                    self.pumps[pump_name].update(pump_data)
            
            self.logger.info(f"Loaded pump configuration for {len(pump_config)} pumps")
            
        except Exception as e:
            self.logger.error(f"Error loading pump configuration: {e}")
    
    def save_config(self):
        """Save current pump configuration to config manager."""
        try:
            # Create a clean copy without transient state
            pump_config = {}
            for pump_name, pump_data in self.pumps.items():
                pump_config[pump_name] = {k: v for k, v in pump_data.items() if k != 'state'}
            
            self.config.set_setting('pumps', pump_config)
            self.config.save_config()
            self.logger.info("Saved pump configuration")
            return True
        except Exception as e:
            self.logger.error(f"Error saving pump configuration: {e}")
            return False
    
    def _setup_gpio(self):
        """Set up GPIO pins for the pumps using lgpio."""
        try:
            # Open GPIO chip (gpiochip4 on Raspberry Pi 5, gpiochip0 on older models)
            self.chip = lgpio.gpiochip_open(self.chip_num)
            
            # Set up each pump pin as output
            for pump_name, pump_data in self.pumps.items():
                pin = pump_data['pin']
                # Set as output
                lgpio.gpio_claim_output(self.chip, pin)
                
                # Initialize to OFF state
                initial_state = 0 if not pump_data['reverse_logic'] else 1
                lgpio.gpio_write(self.chip, pin, initial_state)
                
            self.logger.info(f"GPIO initialized successfully using lgpio on gpiochip{self.chip_num}")
        except Exception as e:
            self.logger.error(f"Error setting up GPIO with lgpio: {e}")
            self.simulation_mode = True
            self.logger.warning("Falling back to simulation mode")
    
    def cleanup(self):
        """Clean up GPIO resources when shutting down."""
        if not self.simulation_mode and self.chip is not None:
            try:
                # Ensure all pumps are off
                self.all_pumps_off()
                # Release all pins and close the chip
                lgpio.gpiochip_close(self.chip)
                self.chip = None
                self.logger.info("GPIO cleaned up")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")
    
    def all_pumps_off(self):
        """Turn off all pumps immediately."""
        with self.lock:
            for pump_name in self.pumps:
                self._set_pump_state(pump_name, False)
            self.active_pumps = {}
            self.logger.info("All pumps turned off")
    
    def _set_pump_state(self, pump_name: str, state: bool):
        """
        Set the physical state of a pump.
        
        Args:
            pump_name: Name of the pump to control
            state: True to turn on, False to turn off
        """
        if pump_name not in self.pumps:
            self.logger.error(f"Unknown pump: {pump_name}")
            return False
        
        pump = self.pumps[pump_name]
        pin = pump['pin']
        
        # Update pump state
        if state:
            pump['state'] = self.RUNNING
        else:
            pump['state'] = self.IDLE
        
        if self.simulation_mode:
            self.logger.debug(f"SIMULATION: Pump {pump_name} {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Set GPIO state, accounting for reverse logic
            gpio_state = 1 if state != pump['reverse_logic'] else 0
            lgpio.gpio_write(self.chip, pin, gpio_state)
            self.logger.debug(f"Pump {pump_name} set to {'ON' if state else 'OFF'}")
            return True
        except Exception as e:
            self.logger.error(f"Error controlling pump {pump_name}: {e}")
            pump['state'] = self.ERROR
            return False
    
    def get_pump_state(self, pump_name: str) -> Dict[str, Any]:
        """Get the current state of a pump."""
        if pump_name not in self.pumps:
            return {'error': f"Unknown pump: {pump_name}"}
        
        with self.lock:
            pump = self.pumps[pump_name]
            return {
                'name': pump_name,
                'state': pump['state'],
                'pin': pump['pin'],
                'flow_rate': pump.get('flow_rate', None),
                'calibration': pump.get('calibration', None)
            }
    
    def get_all_pump_states(self) -> Dict[str, Dict[str, Any]]:
        """Get the current state of all pumps."""
        states = {}
        with self.lock:
            for pump_name in self.pumps:
                states[pump_name] = self.get_pump_state(pump_name)
        return states
    
    def set_pump_calibration(self, pump_name: str, flow_rate: float) -> bool:
        """
        Set the calibration flow rate for a pump.
        
        Args:
            pump_name: Name of the pump to calibrate
            flow_rate: Flow rate in ml per second
        """
        if pump_name not in self.pumps:
            self.logger.error(f"Unknown pump: {pump_name}")
            return False
        
        if pump_name in ['main']:
            self.logger.error(f"Cannot set flow rate for {pump_name} pump")
            return False
        
        if flow_rate <= 0:
            self.logger.error(f"Invalid flow rate: {flow_rate}")
            return False
        
        with self.lock:
            self.pumps[pump_name]['flow_rate'] = flow_rate
            self.logger.info(f"Calibrated {pump_name} pump to {flow_rate} ml/s")
            return self.save_config()
    
    async def run_pump_for_duration(self, pump_name: str, duration_seconds: float) -> bool:
        """
        Run a pump for a specific duration.
        
        Args:
            pump_name: Name of the pump to run
            duration_seconds: How long to run the pump
            
        Returns:
            Success status
        """
        if pump_name not in self.pumps:
            self.logger.error(f"Unknown pump: {pump_name}")
            return False
        
        pump = self.pumps[pump_name]
        
        # Check maximum run time for safety
        if duration_seconds > pump['max_run_time']:
            self.logger.error(f"Requested duration {duration_seconds}s exceeds maximum allowed {pump['max_run_time']}s")
            return False
        
        # Check if pump is already running
        if pump_name in self.active_pumps:
            self.logger.error(f"Pump {pump_name} is already running")
            return False
        
        with self.lock:
            try:
                # Track this pump as active
                self.active_pumps[pump_name] = time.time() + duration_seconds
                
                # Turn on the pump
                self._set_pump_state(pump_name, True)
                self.logger.info(f"Started {pump_name} pump for {duration_seconds} seconds")
                
                # Wait for the duration
                await asyncio.sleep(duration_seconds)
                
                # Turn off the pump
                self._set_pump_state(pump_name, False)
                self.logger.info(f"Stopped {pump_name} pump after {duration_seconds} seconds")
                
                # Remove from active pumps
                if pump_name in self.active_pumps:
                    del self.active_pumps[pump_name]
                
                return True
            except Exception as e:
                self.logger.error(f"Error running {pump_name} pump: {e}")
                # Ensure pump is off in case of exception
                self._set_pump_state(pump_name, False)
                if pump_name in self.active_pumps:
                    del self.active_pumps[pump_name]
                return False
    
    async def run_pump_for_volume(self, pump_name: str, volume_ml: float) -> bool:
        """
        Run a dosing pump to dispense a specific volume.
        
        Args:
            pump_name: Name of the pump to run
            volume_ml: Volume to dispense in milliliters
            
        Returns:
            Success status
        """
        if pump_name not in self.pumps or pump_name == 'main':
            self.logger.error(f"Invalid dosing pump: {pump_name}")
            return False
        
        if volume_ml <= 0:
            self.logger.error(f"Invalid volume: {volume_ml}ml")
            return False
        
        pump = self.pumps[pump_name]
        flow_rate = pump['flow_rate']
        
        if flow_rate <= 0:
            self.logger.error(f"Invalid flow rate for {pump_name}: {flow_rate}ml/s")
            return False
        
        # Calculate duration
        duration_seconds = volume_ml / flow_rate
        
        # Minimum run time to prevent very short bursts
        if duration_seconds < 0.5:
            self.logger.warning(f"Adjusted duration to minimum 0.5s for {volume_ml}ml")
            duration_seconds = 0.5
        
        return await self.run_pump_for_duration(pump_name, duration_seconds)
    
    async def dose_ph_up(self, volume_ml: float) -> bool:
        """Dose pH up solution."""
        return await self.run_pump_for_volume('ph_up', volume_ml)
    
    async def dose_ph_down(self, volume_ml: float) -> bool:
        """Dose pH down solution."""
        return await self.run_pump_for_volume('ph_down', volume_ml)
    
    async def dose_nutrient_a(self, volume_ml: float) -> bool:
        """Dose nutrient A solution."""
        return await self.run_pump_for_volume('nutrient_a', volume_ml)
    
    async def dose_nutrient_b(self, volume_ml: float) -> bool:
        """Dose nutrient B solution."""
        return await self.run_pump_for_volume('nutrient_b', volume_ml)
    
    async def run_main_pump(self, duration_seconds: float = 60.0) -> bool:
        """Run the main circulation pump."""
        return await self.run_pump_for_duration('main', duration_seconds)
    
    async def calibrate_pump_automated(self, pump_name: str, expected_volume_ml: float, run_time_seconds: float) -> float:
        """
        Perform automated pump calibration.
        
        Args:
            pump_name: Name of the pump to calibrate
            expected_volume_ml: The volume expected to be dispensed (measured by user)
            run_time_seconds: How long the pump ran
            
        Returns:
            New calculated flow rate
        """
        if pump_name not in self.pumps or pump_name == 'main':
            self.logger.error(f"Invalid dosing pump for calibration: {pump_name}")
            return 0.0
        
        if expected_volume_ml <= 0 or run_time_seconds <= 0:
            self.logger.error(f"Invalid calibration parameters: {expected_volume_ml}ml in {run_time_seconds}s")
            return 0.0
        
        # Calculate new flow rate
        new_flow_rate = expected_volume_ml / run_time_seconds
        
        # Update pump calibration
        with self.lock:
            old_flow_rate = self.pumps[pump_name]['flow_rate']
            self.pumps[pump_name]['flow_rate'] = new_flow_rate
            self.save_config()
            
            self.logger.info(
                f"Calibrated {pump_name} pump: " +
                f"Old rate = {old_flow_rate:.2f} ml/s, New rate = {new_flow_rate:.2f} ml/s"
            )
            
            return new_flow_rate
    
    async def run_calibration_cycle(self, pump_name: str, run_time_seconds: float = 10.0) -> Dict[str, Any]:
        """
        Run a calibration cycle for a pump.
        
        Args:
            pump_name: Name of the pump to calibrate
            run_time_seconds: How long to run the pump
            
        Returns:
            Dictionary with calibration details
        """
        if pump_name not in self.pumps or pump_name == 'main':
            return {'success': False, 'message': f"Invalid dosing pump for calibration: {pump_name}"}
        
        with self.lock:
            # Get current flow rate for reference
            current_flow_rate = self.pumps[pump_name]['flow_rate']
            expected_volume = current_flow_rate * run_time_seconds
            
            self.logger.info(
                f"Starting calibration cycle for {pump_name}: " +
                f"Current rate = {current_flow_rate:.2f} ml/s, " +
                f"Expected volume = {expected_volume:.2f} ml in {run_time_seconds:.1f}s"
            )
            
            # Run the pump
            success = await self.run_pump_for_duration(pump_name, run_time_seconds)
            
            if success:
                return {
                    'success': True,
                    'message': f"Calibration cycle completed for {pump_name}",
                    'pump': pump_name,
                    'run_time': run_time_seconds,
                    'current_flow_rate': current_flow_rate,
                    'expected_volume': expected_volume,
                    'instructions': "Measure the actual volume dispensed and enter it to complete calibration"
                }
            else:
                return {
                    'success': False,
                    'message': f"Calibration cycle failed for {pump_name}"
                }

# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("PumpManager module - import to use") 