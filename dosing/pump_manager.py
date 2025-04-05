#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Pump Manager
Controls peristaltic pumps for dosing nutrients and pH adjusters
"""
import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("NuTetra.Pumps")

class PumpManager:
    """Manages peristaltic pumps for dosing"""
    
    def __init__(self, config):
        """Initialize the pump manager
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        
        # Get pump settings from config
        self.pump_config = self.config.get_setting('pumps', {})
        self.gpio_config = self.config.get_setting('gpio', {})
        
        # Default GPIO settings if not in config
        self.chip_num = self.gpio_config.get('chip', 4)  # Default to GPIO chip 4 on Raspberry Pi 4
        self.gpio_library = self.gpio_config.get('library', 'rpi-lgpio')  # Default to rpi-lgpio
        
        # Track active pumps and status
        self.active_pumps = {}
        self.pump_states = {}
        self.lock = threading.RLock()
        
        # Initialize GPIO interface
        self.gpio = None
        self.h = None  # GPIO chip handle for lgpio
        self.simulation_mode = False
        
        # Try to initialize GPIO
        success = self._init_gpio()
        if not success:
            logger.warning("Failed to initialize GPIO. Running in simulation mode.")
            self.simulation_mode = True
        
        # Initialize pumps
        self._init_pumps()
        
        logger.info("Pump manager initialized")
    
    def _init_gpio(self) -> bool:
        """Initialize the GPIO interface
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Default pin configuration for pumps
        default_pins = {
            'ph_up': {'pin': 17},
            'ph_down': {'pin': 18},
            'nutrient_a': {'pin': 22},
            'nutrient_b': {'pin': 23},
            'main': {'pin': 27}
        }
        
        # Update default pins with configuration
        for pump_id, config in default_pins.items():
            if pump_id not in self.pump_config:
                self.pump_config[pump_id] = config
        
        # Ensure the config is saved
        self.config.set_setting('pumps', self.pump_config)
        
        # Try to import the appropriate GPIO library
        try:
            if self.gpio_library == 'rpi-lgpio':
                try:
                    import rpi_lgpio as lgpio
                    self.gpio = lgpio
                    # Open the GPIO chip
                    self.h = self.gpio.gpiochip_open(self.chip_num)
                    logger.info(f"Using rpi-lgpio with gpiochip{self.chip_num}")
                    return True
                except ImportError:
                    logger.warning("rpi-lgpio not available, falling back to standard lgpio")
                except Exception as e:
                    logger.error(f"Error initializing rpi-lgpio: {e}")
                    return False
            
            # Try standard lgpio if rpi-lgpio failed or not selected
            if self.gpio_library == 'lgpio' or (self.gpio_library == 'rpi-lgpio' and self.gpio is None):
                try:
                    import lgpio
                    self.gpio = lgpio
                    # Open the GPIO chip
                    self.h = self.gpio.gpiochip_open(self.chip_num)
                    logger.info(f"Using standard lgpio with gpiochip{self.chip_num}")
                    return True
                except ImportError:
                    logger.warning("lgpio not available")
                except Exception as e:
                    logger.error(f"Error initializing lgpio: {e}")
                    return False
            
            # If simulation mode is explicitly selected
            if self.gpio_library == 'simulation':
                logger.info("Using simulation mode for GPIO")
                self.simulation_mode = True
                return True
            
            # If we get here, no GPIO library was successfully loaded
            logger.error("No GPIO library available, running in simulation mode")
            self.simulation_mode = True
            return False
            
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            self.simulation_mode = True
            return False
    
    def _init_pumps(self):
        """Initialize all pumps"""
        for pump_id, config in self.pump_config.items():
            pin = config.get('pin')
            if pin is None:
                logger.error(f"No pin defined for pump {pump_id}")
                continue
            
            if not self.simulation_mode:
                try:
                    # Configure the pin as an output
                    self.gpio.gpio_claim_output(self.h, pin, 0)  # Start with pump off (0)
                    logger.info(f"Initialized {pump_id} pump on pin {pin}")
                except Exception as e:
                    logger.error(f"Error initializing {pump_id} on pin {pin}: {e}")
            
            # Initialize state
            self.pump_states[pump_id] = {
                'state': 'idle',
                'pin': pin,
                'start_time': 0,
                'run_duration': 0,
                'flow_rate': config.get('flow_rate', 1.0)  # ml/sec
            }
    
    def _set_pump(self, pump_id: str, state: int):
        """Set the pump pin state
        
        Args:
            pump_id: The pump to control
            state: 1 for on, 0 for off
        """
        if pump_id not in self.pump_states:
            logger.error(f"Unknown pump: {pump_id}")
            return False
        
        pin = self.pump_states[pump_id]['pin']
        
        if self.simulation_mode:
            logger.info(f"Simulation: {pump_id} on pin {pin} set to {state}")
            return True
        
        try:
            self.gpio.gpio_write(self.h, pin, state)
            return True
        except Exception as e:
            logger.error(f"Error setting {pump_id} on pin {pin} to {state}: {e}")
            return False
    
    def run_pump(self, pump_id: str, state: bool) -> bool:
        """Run or stop a pump
        
        Args:
            pump_id: The pump to control
            state: True to turn on, False to turn off
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            if pump_id not in self.pump_states:
                logger.error(f"Unknown pump: {pump_id}")
                return False
            
            # Convert bool to GPIO value (1 or 0)
            gpio_state = 1 if state else 0
            
            if state:
                # Turn on pump
                success = self._set_pump(pump_id, gpio_state)
                if success:
                    self.pump_states[pump_id]['state'] = 'running'
                    self.pump_states[pump_id]['start_time'] = time.time()
                    logger.info(f"{pump_id} pump started")
                return success
            else:
                # Turn off pump
                success = self._set_pump(pump_id, gpio_state)
                if success:
                    self.pump_states[pump_id]['state'] = 'idle'
                    self.pump_states[pump_id]['run_duration'] = 0
                    logger.info(f"{pump_id} pump stopped")
                return success
    
    def run_pump_for_seconds(self, pump_id: str, duration: float) -> bool:
        """Run a pump for a specific duration
        
        Args:
            pump_id: The pump to run
            duration: How long to run the pump in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if duration <= 0:
            logger.warning(f"Invalid duration: {duration}")
            return False
        
        if pump_id not in self.pump_states:
            logger.error(f"Unknown pump: {pump_id}")
            return False
        
        # Check if pump is already running
        if pump_id in self.active_pumps:
            logger.warning(f"{pump_id} pump is already running")
            return False
        
        logger.info(f"Running {pump_id} pump for {duration:.1f} seconds")
        
        # Start the pump
        success = self.run_pump(pump_id, True)
        if not success:
            return False
        
        # Create a thread to stop the pump after the duration
        def stop_after_duration():
            try:
                self.active_pumps[pump_id] = True
                time.sleep(duration)
                
                # If we still own this pump (it hasn't been stopped elsewhere)
                with self.lock:
                    if pump_id in self.active_pumps:
                        logger.info(f"Auto-stopping {pump_id} pump after {duration:.1f}s")
                        self.run_pump(pump_id, False)
                        del self.active_pumps[pump_id]
            except Exception as e:
                logger.error(f"Error in timer thread for {pump_id}: {e}")
                # Try to ensure pump is stopped on error
                try:
                    self.run_pump(pump_id, False)
                    if pump_id in self.active_pumps:
                        del self.active_pumps[pump_id]
                except:
                    pass
        
        # Start the timer thread
        timer_thread = threading.Thread(target=stop_after_duration, daemon=True)
        timer_thread.start()
        
        return True
    
    def all_pumps_off(self) -> bool:
        """Emergency stop all pumps
        
        Returns:
            bool: True if all pumps stopped successfully, False otherwise
        """
        logger.info("Stopping all pumps")
        success = True
        
        with self.lock:
            # Clear active pumps list
            self.active_pumps.clear()
            
            # Stop each pump
            for pump_id in self.pump_states:
                pump_success = self.run_pump(pump_id, False)
                if not pump_success:
                    success = False
        
        return success
    
    def get_pump_state(self, pump_id: str) -> Dict[str, Any]:
        """Get the current state of a pump
        
        Args:
            pump_id: The pump to check
            
        Returns:
            Dict with pump state information
        """
        if pump_id not in self.pump_states:
            return {'state': 'unknown'}
        
        state = self.pump_states[pump_id].copy()
        
        # Calculate runtime for active pumps
        if state['state'] == 'running':
            elapsed = time.time() - state['start_time']
            state['elapsed'] = elapsed
        
        return state
    
    def calibrate_pump_automated(self, pump_id: str, volume_ml: float, run_time: float) -> float:
        """Calibrate a pump by measuring actual volume pumped
        
        Args:
            pump_id: The pump to calibrate
            volume_ml: The volume actually pumped in ml
            run_time: How long the pump ran in seconds
            
        Returns:
            float: The new flow rate in ml/sec
        """
        if pump_id not in self.pump_states:
            logger.error(f"Unknown pump: {pump_id}")
            return 0.0
        
        if volume_ml <= 0 or run_time <= 0:
            logger.error(f"Invalid calibration values: volume={volume_ml}, run_time={run_time}")
            return 0.0
        
        # Calculate new flow rate
        new_rate = volume_ml / run_time
        
        # Update pump configuration
        with self.lock:
            self.pump_states[pump_id]['flow_rate'] = new_rate
            
            # Update the config
            if pump_id in self.pump_config:
                self.pump_config[pump_id]['flow_rate'] = new_rate
            else:
                self.pump_config[pump_id] = {'pin': self.pump_states[pump_id]['pin'], 'flow_rate': new_rate}
            
            self.config.set_setting('pumps', self.pump_config)
            self.config.save_config()
        
        logger.info(f"Calibrated {pump_id} pump: {new_rate:.2f} ml/sec")
        return new_rate
    
    def cleanup(self):
        """Clean up resources on shutdown"""
        logger.info("Cleaning up pump manager")
        
        # Stop all pumps
        self.all_pumps_off()
        
        # Close GPIO if using hardware
        if not self.simulation_mode and self.h is not None:
            try:
                for pump_id, state in self.pump_states.items():
                    pin = state['pin']
                    # Release GPIO pins
                    self.gpio.gpio_free(self.h, pin)
                
                # Close GPIO chip
                self.gpio.gpiochip_close(self.h)
                logger.info("GPIO resources cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}") 