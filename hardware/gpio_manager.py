#!/usr/bin/env python3
# NuTetra GPIO Manager for Raspberry Pi 5
# Handles all GPIO operations using the rpi-lgpio library

import logging
import os

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

class GPIOManager:
    def __init__(self, simulation_mode=not GPIO_AVAILABLE):
        self.logger = logging.getLogger("NuTetra.GPIO")
        self.logger.info("Initializing GPIO Manager for Raspberry Pi 5")
        
        self.simulation_mode = simulation_mode
        self.handle = None
        
        # Detect the appropriate GPIO chip number
        self.chip_num = self._detect_gpio_chip()
        
        # Store pin configurations
        self.pin_modes = {}  # Tracks pin modes (INPUT/OUTPUT)
        self.pin_states = {} # Tracks current pin states
        
        if not self.simulation_mode:
            try:
                # Initialize lgpio with the detected chip
                self.handle = lgpio.gpiochip_open(self.chip_num)
                self.logger.info(f"Successfully opened GPIO chip{self.chip_num}")
            except Exception as e:
                self.logger.error(f"Failed to initialize GPIO: {e}")
                self.simulation_mode = True
                self.logger.warning("Falling back to simulation mode")
    
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
                self.logger.info("Using gpiochip4 for GPIO control")
                return 4  # Pi 5 uses gpiochip4
            else:
                self.logger.info("Using gpiochip0 for GPIO control")
                return 0  # Older Pi models use gpiochip0
                
        except Exception as e:
            self.logger.warning(f"Error detecting GPIO chip: {e}, defaulting to gpiochip4")
            return 4  # Default to Pi 5 setting
    
    def setup_pin(self, pin, mode, initial_state=0):
        """
        Configure a GPIO pin
        mode: 0 for INPUT, 1 for OUTPUT
        """
        if self.simulation_mode:
            self.logger.debug(f"SIMULATION: Pin {pin} configured as {'OUTPUT' if mode == 1 else 'INPUT'}")
            self.pin_modes[pin] = mode
            if mode == 1:
                self.pin_states[pin] = initial_state
            return True
            
        try:
            if mode == 1:  # OUTPUT
                lgpio.gpio_claim_output(self.handle, pin, initial_state)
                self.pin_states[pin] = initial_state
            else:  # INPUT
                lgpio.gpio_claim_input(self.handle, pin)
            
            self.pin_modes[pin] = mode
            self.logger.debug(f"Pin {pin} configured as {'OUTPUT' if mode == 1 else 'INPUT'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup pin {pin}: {e}")
            return False
    
    def write_pin(self, pin, state):
        """Set the state of an output pin (0 or 1)"""
        if self.simulation_mode:
            if pin not in self.pin_modes or self.pin_modes[pin] != 1:
                self.logger.error(f"SIMULATION: Pin {pin} is not configured as an output")
                return False
            self.pin_states[pin] = state
            self.logger.debug(f"SIMULATION: Pin {pin} set to {state}")
            return True
            
        try:
            if pin not in self.pin_modes or self.pin_modes[pin] != 1:
                self.logger.error(f"Pin {pin} is not configured as an output")
                return False
                
            lgpio.gpio_write(self.handle, pin, state)
            self.pin_states[pin] = state
            self.logger.debug(f"Pin {pin} set to {state}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write to pin {pin}: {e}")
            return False
    
    def read_pin(self, pin):
        """Read the state of an input pin"""
        if self.simulation_mode:
            if pin not in self.pin_modes:
                self.logger.error(f"SIMULATION: Pin {pin} is not configured")
                return None
            # Return the stored state for outputs or 0 for inputs in simulation
            return self.pin_states.get(pin, 0)
            
        try:
            if pin not in self.pin_modes:
                self.logger.error(f"Pin {pin} is not configured")
                return None
                
            state = lgpio.gpio_read(self.handle, pin)
            self.logger.debug(f"Pin {pin} read as {state}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to read pin {pin}: {e}")
            return None
    
    def toggle_pin(self, pin):
        """Toggle the state of an output pin"""
        if pin in self.pin_states:
            current_state = self.pin_states[pin]
            return self.write_pin(pin, 1 - current_state)
        return False
    
    def set_pwm(self, pin, frequency, duty_cycle):
        """
        Configure a pin for PWM output
        frequency: Hz
        duty_cycle: 0-100 (percentage)
        """
        if self.simulation_mode:
            self.logger.debug(f"SIMULATION: PWM on pin {pin} set to {frequency}Hz at {duty_cycle}%")
            return True
            
        try:
            # Convert duty cycle percentage (0-100) to lgpio range (0-1000000)
            dc_scaled = int(duty_cycle * 10000)
            lgpio.tx_pwm(self.handle, pin, frequency, dc_scaled)
            self.logger.debug(f"PWM on pin {pin} set to {frequency}Hz at {duty_cycle}%")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set PWM on pin {pin}: {e}")
            return False
    
    def cleanup(self):
        """Release all GPIO resources"""
        if self.simulation_mode or self.handle is None:
            self.logger.info("Simulation mode - no GPIO resources to clean up")
            return
            
        try:
            lgpio.gpiochip_close(self.handle)
            self.handle = None
            self.logger.info("GPIO resources released")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup: {e}") 