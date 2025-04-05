#!/usr/bin/env python3
# NuTetra Pump Controller
# Manages dosing pumps for pH up/down and nutrients

import time
import logging
import threading
from datetime import datetime, timedelta

class PumpController:
    def __init__(self, gpio_manager):
        self.logger = logging.getLogger("NuTetra.Pumps")
        self.logger.info("Initializing Pump Controller")
        
        self.gpio = gpio_manager
        
        # Pump configurations (can be configured in config.json)
        self.pumps = {
            'ph_up': {
                'pin': 5,
                'name': 'pH Up',
                'flow_rate': 1.0,  # mL per second
                'last_dose': None,
                'total_volume': 0.0,  # total volume dispensed in mL
                'enabled': True
            },
            'ph_down': {
                'pin': 6,
                'name': 'pH Down',
                'flow_rate': 1.0,  # mL per second
                'last_dose': None,
                'total_volume': 0.0,  # total volume dispensed in mL
                'enabled': True
            },
            'nutrient_a': {
                'pin': 13,
                'name': 'Nutrient A',
                'flow_rate': 1.2,  # mL per second
                'last_dose': None,
                'total_volume': 0.0,  # total volume dispensed in mL
                'enabled': True
            },
            'nutrient_b': {
                'pin': 19,
                'name': 'Nutrient B',
                'flow_rate': 1.2,  # mL per second
                'last_dose': None,
                'total_volume': 0.0,  # total volume dispensed in mL
                'enabled': True
            }
        }
        
        # Dosing settings
        self.dosing_settings = {
            'min_dose_interval': 300,  # Minimum seconds between doses
            'max_daily_volume': {
                'ph_up': 50.0,        # Maximum daily volume in mL
                'ph_down': 50.0,
                'nutrient_a': 100.0,
                'nutrient_b': 100.0
            },
            'dose_amounts': {
                'ph_up': 0.5,         # Default dose amount in mL
                'ph_down': 0.5,
                'nutrient_a': 1.0,
                'nutrient_b': 1.0
            }
        }
        
        # Initialize GPIO pins for pumps
        self._setup_pump_pins()
        
    def _setup_pump_pins(self):
        """Configure GPIO pins for all pumps"""
        for pump_id, pump in self.pumps.items():
            # Configure pin as output with initial state LOW (pump off)
            self.gpio.setup_pin(pump['pin'], 1, 0)
            self.logger.debug(f"Configured pump {pump['name']} on pin {pump['pin']}")
            
    def dose(self, pump_id, volume_ml=None):
        """
        Dose a specific volume using the specified pump
        Returns: (success, message)
        """
        if pump_id not in self.pumps:
            return False, f"Unknown pump ID: {pump_id}"
            
        pump = self.pumps[pump_id]
        
        if not pump['enabled']:
            return False, f"Pump {pump['name']} is disabled"
            
        # Use default dose amount if volume not specified
        if volume_ml is None:
            volume_ml = self.dosing_settings['dose_amounts'][pump_id]
            
        # Check if minimum interval has elapsed since last dose
        now = datetime.now()
        if pump['last_dose'] is not None:
            seconds_since_last = (now - pump['last_dose']).total_seconds()
            if seconds_since_last < self.dosing_settings['min_dose_interval']:
                return False, f"Minimum interval not elapsed for {pump['name']}"
                
        # Check daily volume limit
        daily_volume = self._get_daily_volume(pump_id)
        if (daily_volume + volume_ml) > self.dosing_settings['max_daily_volume'][pump_id]:
            return False, f"Daily volume limit exceeded for {pump['name']}"
            
        # Calculate pump duration based on flow rate
        duration_sec = volume_ml / pump['flow_rate']
        
        try:
            # Turn on the pump
            self.gpio.write_pin(pump['pin'], 1)
            
            # Wait for the calculated duration
            self.logger.info(f"Dosing {volume_ml} mL using {pump['name']} for {duration_sec:.2f} seconds")
            time.sleep(duration_sec)
            
            # Turn off the pump
            self.gpio.write_pin(pump['pin'], 0)
            
            # Update pump statistics
            pump['last_dose'] = now
            pump['total_volume'] += volume_ml
            
            return True, f"Successfully dosed {volume_ml} mL using {pump['name']}"
            
        except Exception as e:
            # Ensure pump is turned off in case of error
            try:
                self.gpio.write_pin(pump['pin'], 0)
            except:
                pass
                
            self.logger.error(f"Error dosing with {pump['name']}: {e}")
            return False, f"Dosing error: {str(e)}"
    
    def dose_ph_up(self, volume_ml=None):
        """Convenience method to dose pH up solution"""
        return self.dose('ph_up', volume_ml)
        
    def dose_ph_down(self, volume_ml=None):
        """Convenience method to dose pH down solution"""
        return self.dose('ph_down', volume_ml)
        
    def dose_nutrient_a(self, volume_ml=None):
        """Convenience method to dose nutrient A"""
        return self.dose('nutrient_a', volume_ml)
        
    def dose_nutrient_b(self, volume_ml=None):
        """Convenience method to dose nutrient B"""
        return self.dose('nutrient_b', volume_ml)
    
    def _get_daily_volume(self, pump_id):
        """
        Calculate total volume dispensed by a pump in the last 24 hours
        """
        # In a production system, this would query a database of dose events
        # For now, we'll just use the total volume as an approximation
        return self.pumps[pump_id]['total_volume'] * 0.5  # Simplified for demo
    
    def calibrate_pump(self, pump_id, actual_volume_ml, expected_volume_ml):
        """
        Calibrate a pump's flow rate based on the actual volume dispensed
        """
        if pump_id not in self.pumps:
            return False, f"Unknown pump ID: {pump_id}"
            
        pump = self.pumps[pump_id]
        
        # Calculate new flow rate
        if expected_volume_ml > 0:
            new_flow_rate = pump['flow_rate'] * (expected_volume_ml / actual_volume_ml)
            pump['flow_rate'] = new_flow_rate
            
            self.logger.info(f"Calibrated {pump['name']} flow rate: {new_flow_rate:.2f} mL/sec")
            return True, f"Calibrated {pump['name']} to {new_flow_rate:.2f} mL/sec"
        else:
            return False, "Expected volume must be greater than zero"
    
    def set_pump_enabled(self, pump_id, enabled):
        """Enable or disable a pump"""
        if pump_id not in self.pumps:
            return False, f"Unknown pump ID: {pump_id}"
            
        self.pumps[pump_id]['enabled'] = bool(enabled)
        status = "enabled" if enabled else "disabled"
        self.logger.info(f"Pump {self.pumps[pump_id]['name']} {status}")
        return True, f"Pump {self.pumps[pump_id]['name']} {status}"
    
    def rename_pump(self, pump_id, new_name):
        """Rename a pump"""
        if pump_id not in self.pumps:
            return False, f"Unknown pump ID: {pump_id}"
            
        old_name = self.pumps[pump_id]['name']
        self.pumps[pump_id]['name'] = new_name
        self.logger.info(f"Renamed pump from '{old_name}' to '{new_name}'")
        return True, f"Renamed pump from '{old_name}' to '{new_name}'"
    
    def get_pump_status(self):
        """Get status of all pumps"""
        status = {}
        for pump_id, pump in self.pumps.items():
            status[pump_id] = {
                'name': pump['name'],
                'enabled': pump['enabled'],
                'flow_rate': pump['flow_rate'],
                'total_volume': pump['total_volume'],
                'last_dose': pump['last_dose'].isoformat() if pump['last_dose'] else None
            }
        return status 