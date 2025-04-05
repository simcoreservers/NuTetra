#!/usr/bin/env python3
# NuTetra Configuration Manager
# Handles system settings and configuration

import os
import json
import logging
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path="/NuTetra/data/config.json"):
        self.logger = logging.getLogger("NuTetra.Config")
        self.logger.info("Initializing Configuration Manager")
        
        self.config_path = config_path
        
        # Default configuration values
        self.defaults = {
            "system": {
                "name": "NuTetra Hydroponic System",
                "version": "1.0.0"
            },
            "sensors": {
                "ph": {
                    "target_min": 5.8,
                    "target_max": 6.2,
                    "alert_min": 5.5,
                    "alert_max": 6.5,
                    "calibration": {
                        "offset": 0.0,
                        "scale": 1.0
                    }
                },
                "ec": {
                    "target_min": 1.0,  # mS/cm
                    "target_max": 1.6,  # mS/cm
                    "alert_min": 0.8,   # mS/cm
                    "alert_max": 1.8,   # mS/cm
                    "calibration": {
                        "offset": 0.0,
                        "scale": 1.0
                    }
                },
                "temperature": {
                    "target_min": 18.0,  # Celsius
                    "target_max": 22.0,  # Celsius
                    "alert_min": 15.0,   # Celsius
                    "alert_max": 25.0,   # Celsius
                    "calibration": {
                        "offset": 0.0,
                        "scale": 1.0
                    }
                },
                "reading_interval": 2.0  # seconds
            },
            "dosing": {
                "pumps": {
                    "ph_up": {
                        "pin": 5,
                        "name": "pH Up",
                        "flow_rate": 1.0,  # mL per second
                        "enabled": True
                    },
                    "ph_down": {
                        "pin": 6,
                        "name": "pH Down",
                        "flow_rate": 1.0,  # mL per second
                        "enabled": True
                    },
                    "nutrient_a": {
                        "pin": 13,
                        "name": "Nutrient A",
                        "flow_rate": 1.2,  # mL per second
                        "enabled": True
                    },
                    "nutrient_b": {
                        "pin": 19,
                        "name": "Nutrient B",
                        "flow_rate": 1.2,  # mL per second
                        "enabled": True
                    }
                },
                "settings": {
                    "min_dose_interval": 300,  # Minimum seconds between doses
                    "max_daily_volume": {
                        "ph_up": 50.0,        # Maximum daily volume in mL
                        "ph_down": 50.0,
                        "nutrient_a": 100.0,
                        "nutrient_b": 100.0
                    },
                    "dose_amounts": {
                        "ph_up": 0.5,         # Default dose amount in mL
                        "ph_down": 0.5,
                        "nutrient_a": 1.0,
                        "nutrient_b": 1.0
                    },
                    "auto_dosing_enabled": True
                }
            },
            "alerts": {
                "email": {
                    "enabled": False,
                    "recipient": "",
                    "smtp_server": "",
                    "smtp_port": 587,
                    "smtp_user": "",
                    "smtp_password": ""
                },
                "sms": {
                    "enabled": False,
                    "phone_number": "",
                    "provider": ""
                },
                "notification_interval": 3600  # seconds
            },
            "ui": {
                "theme": "dark",
                "display_units": {
                    "temperature": "celsius",  # or fahrenheit
                    "volume": "ml"
                },
                "screensaver_timeout": 300,  # seconds
                "brightness": 80  # percentage
            },
            "logging": {
                "level": "INFO",
                "max_log_size_mb": 10,
                "max_log_files": 5,
                "data_log_interval": 300  # seconds
            },
            "network": {
                "hostname": "nutetra",
                "wifi": {
                    "ssid": "",
                    "psk": "",
                    "enable_ap": True,
                    "ap_ssid": "NuTetra",
                    "ap_psk": "hydroponics"
                }
            }
        }
        
        # Load or create configuration
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create defaults"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.logger.info("Configuration loaded from file")
                    
                    # Merge with defaults to ensure all settings exist
                    merged_config = self._deep_merge(self.defaults.copy(), config)
                    return merged_config
            else:
                self.logger.info("Configuration file not found, using defaults")
                # Ensure directory exists
                Path(os.path.dirname(self.config_path)).mkdir(parents=True, exist_ok=True)
                # Save defaults
                self.save_config(self.defaults)
                return self.defaults.copy()
                
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return self.defaults.copy()
    
    def save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
            
        try:
            # Ensure directory exists
            Path(os.path.dirname(self.config_path)).mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.logger.info("Configuration saved to file")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, section, key=None, default=None):
        """
        Get a configuration value
        section: Top-level section (e.g., 'sensors', 'dosing')
        key: Optional sub-key (e.g., 'ph', 'target_min')
        default: Value to return if key doesn't exist
        """
        try:
            if section not in self.config:
                return default
                
            if key is None:
                return self.config[section]
                
            # Handle nested keys (e.g., 'sensors.ph.target_min')
            if '.' in key:
                parts = key.split('.')
                value = self.config[section]
                
                for part in parts:
                    if part in value:
                        value = value[part]
                    else:
                        return default
                        
                return value
            else:
                return self.config[section].get(key, default)
                
        except Exception as e:
            self.logger.error(f"Error getting config value [{section}.{key}]: {e}")
            return default
    
    def set(self, section, key, value):
        """
        Set a configuration value
        section: Top-level section (e.g., 'sensors', 'dosing')
        key: Key to set (can be nested using dots, e.g., 'ph.target_min')
        value: Value to set
        """
        try:
            if section not in self.config:
                self.config[section] = {}
                
            # Handle nested keys (e.g., 'ph.target_min')
            if '.' in key:
                parts = key.split('.')
                config_section = self.config[section]
                
                # Navigate to the deepest level
                for part in parts[:-1]:
                    if part not in config_section:
                        config_section[part] = {}
                    config_section = config_section[part]
                    
                # Set the value
                config_section[parts[-1]] = value
            else:
                self.config[section][key] = value
                
            # Save the updated configuration
            self.save_config()
            self.logger.debug(f"Set config value [{section}.{key}] = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting config value [{section}.{key}]: {e}")
            return False
    
    def _deep_merge(self, dest, src):
        """
        Deep merge two dictionaries
        Values from src override those in dest
        """
        for key, value in src.items():
            if key in dest and isinstance(dest[key], dict) and isinstance(value, dict):
                self._deep_merge(dest[key], value)
            else:
                dest[key] = value
        return dest
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.defaults.copy()
        self.save_config()
        self.logger.info("Configuration reset to defaults")
        return True
    
    def export_config(self, export_path):
        """Export configuration to a file"""
        try:
            with open(export_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, import_path):
        """Import configuration from a file"""
        try:
            with open(import_path, 'r') as f:
                imported = json.load(f)
            
            # Merge with defaults to ensure all required settings exist
            self.config = self._deep_merge(self.defaults.copy(), imported)
            self.save_config()
            return True
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False 