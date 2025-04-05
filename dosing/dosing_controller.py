#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Dosing Controller
Handles automated pH and nutrient dosing based on sensor readings
"""
import time
import logging
import threading
import datetime
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("NuTetra.Dosing")

class DosingController:
    """Controls automated dosing of pH and nutrients based on sensor readings"""
    
    def __init__(self, config, atlas, pumps):
        """Initialize the dosing controller
        
        Args:
            config: Configuration manager instance
            atlas: Atlas sensor interface
            pumps: Pump manager instance
        """
        self.config = config
        self.atlas = atlas
        self.pumps = pumps
        
        # Get dosing settings from config
        self.settings = self.config.get_setting('dosing', {})
        
        # Set default settings if not in config
        self._set_default_settings()
        
        # Setup state variables
        self.running = False
        self.active_pump = None
        self.last_run = 0
        self.next_run = 0
        self.dosing_thread = None
        self.dosing_history = {
            'ph_up': {'daily_total': 0, 'last_reset': time.time()},
            'ph_down': {'daily_total': 0, 'last_reset': time.time()},
            'nutrient_a': {'daily_total': 0, 'last_reset': time.time()},
            'nutrient_b': {'daily_total': 0, 'last_reset': time.time()}
        }
        
        logger.info("Dosing controller initialized")
    
    def _set_default_settings(self):
        """Set default dosing settings if not in config"""
        defaults = {
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
        }
        
        # Update settings with defaults for any missing values
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
        
        # Save settings to config
        self.config.set_setting('dosing', self.settings)
        self.config.save_config()
    
    def start(self):
        """Start the dosing controller thread"""
        if self.running:
            logger.warning("Dosing controller already running")
            return
        
        logger.info("Starting dosing controller")
        self.running = True
        self.dosing_thread = threading.Thread(target=self._dosing_loop, daemon=True)
        self.dosing_thread.start()
    
    def stop(self):
        """Stop the dosing controller thread"""
        if not self.running:
            logger.warning("Dosing controller already stopped")
            return
        
        logger.info("Stopping dosing controller")
        self.running = False
        if self.dosing_thread:
            self.dosing_thread.join(timeout=10)
        
        # Ensure all pumps are off
        self.pumps.all_pumps_off()
    
    def _dosing_loop(self):
        """Main dosing control loop"""
        logger.info("Dosing loop started")
        
        while self.running:
            try:
                # Reset daily totals if day changed
                self._check_daily_reset()
                
                # Check if it's time to run a dosing cycle
                current_time = time.time()
                
                if current_time >= self.next_run:
                    # Check if night mode is enabled and we're in night hours
                    if not self._is_night_mode_active():
                        # Run the dosing cycle
                        logger.info("Starting automatic dosing cycle")
                        self.run_cycle()
                    else:
                        logger.info("Skipping dosing cycle due to night mode")
                        self._schedule_next_run()
                
                # Sleep for a bit to avoid high CPU usage
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in dosing loop: {e}")
                time.sleep(60)  # Longer sleep on error
    
    def _check_daily_reset(self):
        """Reset daily dosing totals if the day has changed"""
        current_time = time.time()
        
        for pump_id, history in self.dosing_history.items():
            # Reset if more than 24 hours have passed
            if current_time - history['last_reset'] > 86400:  # 24 hours in seconds
                logger.info(f"Resetting daily total for {pump_id}")
                history['daily_total'] = 0
                history['last_reset'] = current_time
    
    def _is_night_mode_active(self) -> bool:
        """Check if night mode is active"""
        if not self.settings.get('enable_night_mode', False):
            return False
        
        # Parse night time settings
        try:
            night_start = self.settings.get('night_start', '22:00')
            night_end = self.settings.get('night_end', '06:00')
            
            # Get current time
            now = datetime.datetime.now().time()
            
            # Parse night start and end times
            start_time = datetime.datetime.strptime(night_start, '%H:%M').time()
            end_time = datetime.datetime.strptime(night_end, '%H:%M').time()
            
            # Check if current time is in night period
            if start_time < end_time:  # Normal time range (e.g., 22:00 to 06:00)
                return start_time <= now <= end_time
            else:  # Time range spans midnight (e.g., 22:00 to 06:00)
                return now >= start_time or now <= end_time
                
        except Exception as e:
            logger.error(f"Error checking night mode: {e}")
            return False
    
    def _schedule_next_run(self):
        """Schedule the next dosing cycle"""
        frequency_minutes = self.settings.get('dosing_frequency', 60)
        self.last_run = time.time()
        self.next_run = self.last_run + (frequency_minutes * 60)
        
        logger.info(f"Next dosing cycle scheduled in {frequency_minutes} minutes")
    
    def _calculate_ph_dose(self, current_ph: float) -> Tuple[str, float]:
        """Calculate required pH adjustment dose
        
        Args:
            current_ph: Current pH reading
            
        Returns:
            Tuple of (pump_id, dose_ml) for pH adjustment
        """
        target_ph = self.settings.get('target_ph', 6.0)
        ph_tolerance = self.settings.get('ph_tolerance', 0.3)
        
        # Check if pH is within tolerance
        upper_bound = target_ph + ph_tolerance
        lower_bound = target_ph - ph_tolerance
        
        if lower_bound <= current_ph <= upper_bound:
            # pH is within acceptable range
            return None, 0
        
        # Determine which direction to adjust
        if current_ph > upper_bound:
            # pH is too high, need to decrease
            pump_id = 'ph_down'
            rate = self.settings.get('ph_down_rate', 1.0)  # ml/s
            max_dose = self.settings.get('max_ph_adjustment', 20)  # ml
            max_daily = self.settings.get('max_daily_ph_down', 100)  # ml
            
            # Calculate dose based on how far from target
            ph_diff = current_ph - target_ph
            # Non-linear scaling based on pH difference
            # This is a simple approximation - may need calibration for specific systems
            dose_ml = min(ph_diff * 5, max_dose)
            
        else:
            # pH is too low, need to increase
            pump_id = 'ph_up'
            rate = self.settings.get('ph_up_rate', 1.0)  # ml/s
            max_dose = self.settings.get('max_ph_adjustment', 20)  # ml
            max_daily = self.settings.get('max_daily_ph_up', 100)  # ml
            
            # Calculate dose based on how far from target
            ph_diff = target_ph - current_ph
            # Non-linear scaling based on pH difference
            dose_ml = min(ph_diff * 5, max_dose)
        
        # Check daily limits
        daily_used = self.dosing_history[pump_id]['daily_total']
        if daily_used + dose_ml > max_daily:
            logger.warning(f"Daily limit reached for {pump_id}. Limiting dose.")
            dose_ml = max(0, max_daily - daily_used)
        
        return pump_id, dose_ml
    
    def _calculate_nutrient_dose(self, current_ec: float) -> Tuple[str, float]:
        """Calculate required nutrient dose
        
        Args:
            current_ec: Current EC reading
            
        Returns:
            Tuple of (nutrient_type, dose_ml) for nutrient adjustment
        """
        target_ec = self.settings.get('target_ec', 1.8)
        ec_tolerance = self.settings.get('ec_tolerance', 0.2)
        
        # Check if EC is within tolerance or too high
        if current_ec >= target_ec - ec_tolerance:
            # EC is at target or too high, don't add nutrients
            return None, 0
        
        # EC is too low, calculate nutrient dose
        max_dose = self.settings.get('max_nutrient_dose', 20)  # ml
        max_daily = self.settings.get('max_daily_nutrient', 200)  # ml
        
        # Calculate how much EC needs to increase
        ec_diff = target_ec - current_ec
        
        # Calculate dose - simplified formula
        # This should be calibrated for specific nutrients and reservoir size
        dose_ml = min(ec_diff * 10, max_dose)  # Simplified formula
        
        # Adjust based on reservoir volume
        # In a real implementation, this should be based on actual reservoir size
        # and nutrient concentration
        
        # Check daily limits for both nutrient types
        a_used = self.dosing_history['nutrient_a']['daily_total']
        b_used = self.dosing_history['nutrient_b']['daily_total']
        
        # Distribute dose evenly between A and B
        a_dose = dose_ml / 2
        b_dose = dose_ml / 2
        
        # Adjust if daily limits are approached
        if a_used + a_dose > max_daily:
            a_dose = max(0, max_daily - a_used)
        if b_used + b_dose > max_daily:
            b_dose = max(0, max_daily - b_used)
        
        # Return result as (type, dose)
        return "nutrients", (a_dose, b_dose)
    
    def run_cycle(self):
        """Run a complete dosing cycle"""
        logger.info("Running dosing cycle")
        
        try:
            # Collect current sensor data
            ph = self.atlas.get_ph()
            ec = self.atlas.get_ec()
            
            logger.info(f"Current pH: {ph}, EC: {ec}")
            
            # Check if sensor readings are valid
            if not (4.0 <= ph <= 9.0) or not (0.0 <= ec <= 5.0):
                logger.error(f"Invalid sensor readings: pH={ph}, EC={ec}")
                self._schedule_next_run()
                return
            
            # Calculate pH adjustment needed
            ph_pump, ph_dose = self._calculate_ph_dose(ph)
            
            # Calculate nutrient adjustment needed
            nutrient_type, nutrient_dose = self._calculate_nutrient_dose(ec)
            
            # Perform pH adjustment first if needed
            if ph_pump and ph_dose > 0:
                logger.info(f"Adjusting pH with {ph_pump}: {ph_dose:.1f}ml")
                self._dose_ph(ph_pump, ph_dose)
                
                # Wait for mixing after pH adjustment
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"Mixing for {mixing_time} seconds after pH adjustment")
                time.sleep(mixing_time)
            else:
                logger.info("No pH adjustment needed")
            
            # Perform nutrient adjustment if needed
            if nutrient_type and sum(nutrient_dose) > 0:
                a_dose, b_dose = nutrient_dose
                logger.info(f"Adding nutrients: A={a_dose:.1f}ml, B={b_dose:.1f}ml")
                self._dose_nutrients(a_dose, b_dose)
                
                # Wait for mixing after nutrient adjustment
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"Mixing for {mixing_time} seconds after nutrient adjustment")
                time.sleep(mixing_time)
            else:
                logger.info("No nutrient adjustment needed")
            
            # Schedule next run
            self._schedule_next_run()
            
        except Exception as e:
            logger.error(f"Error in dosing cycle: {e}")
            # In case of error, schedule next run anyway
            self._schedule_next_run()
    
    def _dose_ph(self, pump_id: str, dose_ml: float):
        """Dose pH adjustment
        
        Args:
            pump_id: The pump to use ('ph_up' or 'ph_down')
            dose_ml: The amount to dose in ml
        """
        if dose_ml <= 0:
            return
        
        # Get flow rate for this pump
        rate_key = f"{pump_id}_rate"
        flow_rate = self.settings.get(rate_key, 1.0)  # ml/sec
        
        # Calculate run time
        run_time = dose_ml / flow_rate
        
        # Run the pump
        success = self.pumps.run_pump_for_seconds(pump_id, run_time)
        
        if success:
            # Update dosing history
            self.dosing_history[pump_id]['daily_total'] += dose_ml
            logger.info(f"Dosed {dose_ml:.1f}ml using {pump_id} pump")
        else:
            logger.error(f"Failed to dose with {pump_id} pump")
    
    def _dose_nutrients(self, a_dose: float, b_dose: float):
        """Dose nutrients
        
        Args:
            a_dose: Nutrient A dose in ml
            b_dose: Nutrient B dose in ml
        """
        # Dose nutrient A
        if a_dose > 0:
            flow_rate = self.settings.get('nutrient_a_rate', 1.0)  # ml/sec
            run_time = a_dose / flow_rate
            
            success = self.pumps.run_pump_for_seconds('nutrient_a', run_time)
            
            if success:
                self.dosing_history['nutrient_a']['daily_total'] += a_dose
                logger.info(f"Dosed {a_dose:.1f}ml of nutrient A")
            else:
                logger.error("Failed to dose nutrient A")
        
        # Wait a moment between nutrient doses
        time.sleep(2)
        
        # Dose nutrient B
        if b_dose > 0:
            flow_rate = self.settings.get('nutrient_b_rate', 1.0)  # ml/sec
            run_time = b_dose / flow_rate
            
            success = self.pumps.run_pump_for_seconds('nutrient_b', run_time)
            
            if success:
                self.dosing_history['nutrient_b']['daily_total'] += b_dose
                logger.info(f"Dosed {b_dose:.1f}ml of nutrient B")
            else:
                logger.error("Failed to dose nutrient B")
    
    def manual_dose(self, pump_id: str, volume_ml: float) -> bool:
        """Manually run a pump to dose a specific amount
        
        Args:
            pump_id: The pump to run ('ph_up', 'ph_down', 'nutrient_a', 'nutrient_b')
            volume_ml: The amount to dose in ml
            
        Returns:
            bool: True if successful, False otherwise
        """
        if pump_id not in ['ph_up', 'ph_down', 'nutrient_a', 'nutrient_b']:
            logger.error(f"Invalid pump ID: {pump_id}")
            return False
        
        logger.info(f"Manual dosing {volume_ml:.1f}ml with {pump_id}")
        
        # Get flow rate for this pump
        rate_key = f"{pump_id}_rate"
        flow_rate = self.settings.get(rate_key, 1.0)  # ml/sec
        
        # Calculate run time
        run_time = volume_ml / flow_rate
        
        # Check daily limits
        max_daily = self.settings.get(f"max_daily_{pump_id.replace('nutrient_', '')}", 100)
        current_total = self.dosing_history[pump_id]['daily_total']
        
        if current_total + volume_ml > max_daily:
            logger.warning(f"Daily limit for {pump_id} would be exceeded")
            return False
        
        # Run the pump
        success = self.pumps.run_pump_for_seconds(pump_id, run_time)
        
        if success:
            # Update dosing history
            self.dosing_history[pump_id]['daily_total'] += volume_ml
            logger.info(f"Manual dose complete: {volume_ml:.1f}ml using {pump_id}")
            return True
        else:
            logger.error(f"Failed to run pump {pump_id}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the dosing controller
        
        Returns:
            Dict with dosing controller status information
        """
        # Get latest sensor readings
        try:
            ph = self.atlas.get_ph()
            ec = self.atlas.get_ec()
            
            # Calculate adjustment needs
            ph_pump, ph_dose = self._calculate_ph_dose(ph)
            nutrient_type, nutrient_dose = self._calculate_nutrient_dose(ec)
            
            # Determine if adjustments are needed
            ph_adjustment_needed = ph_pump is not None and ph_dose > 0
            ec_adjustment_needed = nutrient_type is not None and sum(nutrient_dose) > 0 if isinstance(nutrient_dose, tuple) else nutrient_dose > 0
            
            # Format time until next run
            time_to_next = max(0, self.next_run - time.time())
            minutes = int(time_to_next // 60)
            seconds = int(time_to_next % 60)
            
            # Return status information
            return {
                'running': self.running,
                'last_run': self.last_run,
                'next_run': self.next_run,
                'time_to_next': f"{minutes}m {seconds}s",
                'current_ph': ph,
                'target_ph': self.settings.get('target_ph'),
                'ph_adjustment_needed': ph_adjustment_needed,
                'current_ec': ec,
                'target_ec': self.settings.get('target_ec'),
                'ec_adjustment_needed': ec_adjustment_needed,
                'night_mode_active': self._is_night_mode_active(),
                'dosing_history': self.dosing_history
            }
        except Exception as e:
            logger.error(f"Error getting dosing status: {e}")
            return {
                'running': self.running,
                'error': str(e)
            }
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current dosing settings
        
        Returns:
            Dict with dosing settings
        """
        return self.settings
    
    def update_target_settings(self, settings: Dict[str, Any]) -> bool:
        """Update target dosing settings
        
        Args:
            settings: Dict containing settings to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate settings
            if 'target_ph' in settings:
                ph = float(settings['target_ph'])
                if not (4.0 <= ph <= 9.0):
                    logger.error(f"Invalid target pH: {ph}")
                    return False
                self.settings['target_ph'] = ph
            
            if 'ph_tolerance' in settings:
                tol = float(settings['ph_tolerance'])
                if not (0.1 <= tol <= 1.0):
                    logger.error(f"Invalid pH tolerance: {tol}")
                    return False
                self.settings['ph_tolerance'] = tol
            
            if 'target_ec' in settings:
                ec = float(settings['target_ec'])
                if not (0.1 <= ec <= 5.0):
                    logger.error(f"Invalid target EC: {ec}")
                    return False
                self.settings['target_ec'] = ec
            
            if 'ec_tolerance' in settings:
                tol = float(settings['ec_tolerance'])
                if not (0.1 <= tol <= 1.0):
                    logger.error(f"Invalid EC tolerance: {tol}")
                    return False
                self.settings['ec_tolerance'] = tol
            
            # Save settings to config
            self.config.set_setting('dosing', self.settings)
            self.config.save_config()
            
            logger.info(f"Updated target settings: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating target settings: {e}")
            return False
    
    def update_nutrient_settings(self, settings: Dict[str, Any]) -> bool:
        """Update nutrient dosing settings
        
        Args:
            settings: Dict containing settings to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Handle flow rates
            for key in ['ph_up_rate', 'ph_down_rate', 'nutrient_a_rate', 'nutrient_b_rate']:
                if key in settings:
                    rate = float(settings[key])
                    if not (0.1 <= rate <= 10.0):
                        logger.error(f"Invalid flow rate for {key}: {rate}")
                        return False
                    self.settings[key] = rate
            
            # Handle max doses
            for key in ['max_ph_adjustment', 'max_nutrient_dose']:
                if key in settings:
                    max_dose = float(settings[key])
                    if not (1.0 <= max_dose <= 100.0):
                        logger.error(f"Invalid max dose for {key}: {max_dose}")
                        return False
                    self.settings[key] = max_dose
            
            # Save settings to config
            self.config.set_setting('dosing', self.settings)
            self.config.save_config()
            
            logger.info(f"Updated nutrient settings: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating nutrient settings: {e}")
            return False
    
    def update_safety_settings(self, settings: Dict[str, Any]) -> bool:
        """Update safety settings
        
        Args:
            settings: Dict containing settings to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Handle daily limits
            for key in ['max_daily_ph_up', 'max_daily_ph_down', 'max_daily_nutrient']:
                if key in settings:
                    max_daily = float(settings[key])
                    if not (10.0 <= max_daily <= 1000.0):
                        logger.error(f"Invalid daily limit for {key}: {max_daily}")
                        return False
                    self.settings[key] = max_daily
            
            # Handle timing settings
            if 'dosing_frequency' in settings:
                freq = int(settings['dosing_frequency'])
                if not (5 <= freq <= 1440):  # 5 min to 24 hours
                    logger.error(f"Invalid dosing frequency: {freq}")
                    return False
                self.settings['dosing_frequency'] = freq
            
            if 'dosing_cooldown' in settings:
                cooldown = int(settings['dosing_cooldown'])
                if not (1 <= cooldown <= 120):  # 1 min to 2 hours
                    logger.error(f"Invalid dosing cooldown: {cooldown}")
                    return False
                self.settings['dosing_cooldown'] = cooldown
            
            if 'mixing_time' in settings:
                mixing = int(settings['mixing_time'])
                if not (5 <= mixing <= 300):  # 5 sec to 5 min
                    logger.error(f"Invalid mixing time: {mixing}")
                    return False
                self.settings['mixing_time'] = mixing
            
            # Handle night mode settings
            if 'enable_night_mode' in settings:
                self.settings['enable_night_mode'] = bool(settings['enable_night_mode'])
            
            if 'night_start' in settings:
                # Validate time format HH:MM
                time_str = settings['night_start']
                try:
                    datetime.datetime.strptime(time_str, '%H:%M')
                    self.settings['night_start'] = time_str
                except ValueError:
                    logger.error(f"Invalid night start time: {time_str}")
                    return False
            
            if 'night_end' in settings:
                # Validate time format HH:MM
                time_str = settings['night_end']
                try:
                    datetime.datetime.strptime(time_str, '%H:%M')
                    self.settings['night_end'] = time_str
                except ValueError:
                    logger.error(f"Invalid night end time: {time_str}")
                    return False
            
            # Save settings to config
            self.config.set_setting('dosing', self.settings)
            self.config.save_config()
            
            logger.info(f"Updated safety settings: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating safety settings: {e}")
            return False 