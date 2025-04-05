#!/usr/bin/env python3
# NuTetra GPIO Manager for Raspberry Pi 5
# Handles all GPIO operations using the lgpio library

import logging
import lgpio

class GPIOManager:
    def __init__(self):
        self.logger = logging.getLogger("NuTetra.GPIO")
        self.logger.info("Initializing GPIO Manager for Raspberry Pi 5")
        
        try:
            # Initialize lgpio (specific to Raspberry Pi 5)
            self.handle = lgpio.gpiochip_open(0)
            self.logger.info("Successfully opened GPIO chip")
            
            # Store pin configurations
            self.pin_modes = {}  # Tracks pin modes (INPUT/OUTPUT)
            self.pin_states = {} # Tracks current pin states
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            raise
    
    def setup_pin(self, pin, mode, initial_state=0):
        """
        Configure a GPIO pin
        mode: 0 for INPUT, 1 for OUTPUT
        """
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
        try:
            lgpio.gpiochip_close(self.handle)
            self.logger.info("GPIO resources released")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup: {e}") 