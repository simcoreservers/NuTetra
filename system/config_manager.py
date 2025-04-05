#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Configuration Manager
Manages system configuration storage and retrieval
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("NuTetra.Config")

class ConfigManager:
    """Manages system configuration storage and retrieval"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager
        
        Args:
            config_path: Path to the configuration file (optional)
        """
        # Set default path if none provided
        if config_path is None:
            self.config_path = "/NuTetra/config/config.json"
        else:
            self.config_path = config_path
            
        self.config = {}
        
        # Ensure config directory exists
        self._ensure_config_dir()
        
        # Load configuration
        self.load_config()
        
        # Set default configuration if needed
        self._set_defaults()
        
        logger.info("Configuration manager initialized")
    
    def _ensure_config_dir(self):
        """Ensure the configuration directory exists"""
        config_dir = os.path.dirname(self.config_path)
        try:
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured config directory exists: {config_dir}")
        except Exception as e:
            logger.error(f"Error creating config directory: {e}")
            # Use a fallback path in the current directory
            self.config_path = "config.json"
            logger.warning(f"Using fallback config path: {self.config_path}")
    
    def _set_defaults(self):
        """Set default configuration values"""
        defaults = {
            # System configuration
            'system': {
                'name': 'NuTetra',
                'version': '1.0.0',
                'log_level': 'INFO',
                'data_dir': '/NuTetra/data'
            },
            
            # GPIO configuration
            'gpio': {
                'chip': 4,  # Default to chip 4 for RPi 5
                'library': 'rpi-lgpio',  # Options: rpi-lgpio, lgpio, simulation
                'simulation_mode': False
            },
            
            # I2C configuration
            'i2c': {
                'bus': 1,
                'enabled': True,
                'ph_address': 0x63,
                'ec_address': 0x64,
                'temp_address': 0x66,
                'cache_time': 2.0  # seconds
            },
            
            # Pump configuration
            'pumps': {
                'ph_up': {
                    'pin': 17,
                    'flow_rate': 1.0  # ml/sec
                },
                'ph_down': {
                    'pin': 18,
                    'flow_rate': 1.0
                },
                'nutrient_a': {
                    'pin': 22,
                    'flow_rate': 1.0
                },
                'nutrient_b': {
                    'pin': 23,
                    'flow_rate': 1.0
                },
                'main': {
                    'pin': 27
                }
            },
            
            # Dosing configuration
            'dosing': {
                'target_ph': 6.0,
                'ph_tolerance': 0.3,
                'target_ec': 1.8,
                'ec_tolerance': 0.2,
                'dosing_frequency': 60,  # minutes
                'dosing_cooldown': 15,   # minutes
                'mixing_time': 30,       # seconds
                'enable_night_mode': False,
                'night_start': '22:00',
                'night_end': '06:00',
                'ph_up_rate': 1.0,       # ml/sec
                'ph_down_rate': 1.0,     # ml/sec
                'nutrient_a_rate': 1.0,  # ml/sec
                'nutrient_b_rate': 1.0,  # ml/sec
                'max_ph_adjustment': 20, # ml
                'max_nutrient_dose': 20, # ml
                'max_daily_ph_up': 100,  # ml
                'max_daily_ph_down': 100,# ml
                'max_daily_nutrient': 200 # ml
            },
            
            # Alerting configuration
            'alerts': {
                'enabled': True,
                'ph_min': 5.0,
                'ph_max': 7.0,
                'ec_min': 1.0,
                'ec_max': 3.0,
                'temp_min': 15.0,
                'temp_max': 30.0
            }
        }
        
        # Update config with defaults for missing sections
        for section, settings in defaults.items():
            if section not in self.config:
                self.config[section] = settings
            else:
                # Update existing section with any missing default values
                for key, value in settings.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value
        
        # Save the updated configuration
        self.save_config()
    
    def load_config(self) -> bool:
        """Load configuration from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                return True
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save configuration to file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Saved configuration to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_setting(self, section: str, default: Any = None) -> Any:
        """Get a configuration section
        
        Args:
            section: Configuration section name
            default: Default value if section doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self.config.get(section, default)
    
    def set_setting(self, section: str, value: Any) -> bool:
        """Set a configuration section
        
        Args:
            section: Configuration section name
            value: Value to set
            
        Returns:
            bool: True if successful
        """
        self.config[section] = value
        return True
    
    def get_subsetting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific setting within a section
        
        Args:
            section: Configuration section name
            key: Setting key within the section
            default: Default value if key doesn't exist
            
        Returns:
            Setting value or default
        """
        if section in self.config:
            return self.config[section].get(key, default)
        return default
    
    def set_subsetting(self, section: str, key: str, value: Any) -> bool:
        """Set a specific setting within a section
        
        Args:
            section: Configuration section name
            key: Setting key within the section
            value: Value to set
            
        Returns:
            bool: True if successful
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        return True
    
    def reset_to_defaults(self) -> bool:
        """Reset all configuration to defaults
        
        Returns:
            bool: True if successful
        """
        self.config = {}
        self._set_defaults()
        logger.info("Reset configuration to defaults")
        return True
    
    def reset_section(self, section: str) -> bool:
        """Reset a specific configuration section to defaults
        
        Args:
            section: Configuration section to reset
            
        Returns:
            bool: True if successful
        """
        if section in self.config:
            del self.config[section]
            self._set_defaults()
            logger.info(f"Reset {section} configuration to defaults")
            return True
        return False
    
    def export_config(self, export_path: str) -> bool:
        """Export configuration to a different file
        
        Args:
            export_path: Path to export the configuration to
            
        Returns:
            bool: True if successful
        """
        try:
            with open(export_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Exported configuration to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """Import configuration from a different file
        
        Args:
            import_path: Path to import the configuration from
            
        Returns:
            bool: True if successful
        """
        try:
            if os.path.exists(import_path):
                with open(import_path, 'r') as f:
                    new_config = json.load(f)
                
                # Update configuration
                self.config.update(new_config)
                
                # Save the updated configuration
                self.save_config()
                
                logger.info(f"Imported configuration from {import_path}")
                return True
            else:
                logger.error(f"Import file not found: {import_path}")
                return False
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False 