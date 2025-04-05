#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Dosing Controller
Handles automated pH and nutrient dosing based on sensor readings
"""
import time
import logging
import threading
import datetime
import random
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("NuTetra.Dosing")

class DosingController:
    """Controls automated dosing of pH and nutrients based on sensor readings"""
    
    def __init__(self, config_manager, atlas=None, pumps=None):
        """Initialize the dosing controller
        
        Args:
            config_manager: Configuration manager instance
            atlas: Atlas sensor interface (optional)
            pumps: Pump manager instance (optional)
        """
        self.config_manager = config_manager
        self.atlas = atlas
        self.pumps = pumps
        
        # Determine if we're in simulation mode
        self.simulation_mode = (atlas is None or pumps is None)
        if self.simulation_mode:
            logger.warning("Dosing controller running in simulation mode")
        
        # Get dosing settings from config
        self.settings = self.config_manager.get_setting('dosing', {})
        
        # Set default settings if not in config
        self._set_default_settings()
        
        # Setup state variables
        self.running = False
        self.active_pump = None
        self.last_run = 0
        self.next_run = 0
        self.dosing_thread = None
        self.daily_totals = {
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
        self.config_manager.set_setting('dosing', self.settings)
        self.config_manager.save_config()
    
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
        
        for pump_id, history in self.daily_totals.items():
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
        daily_used = self.daily_totals[pump_id]['daily_total']
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
        a_used = self.daily_totals['nutrient_a']['daily_total']
        b_used = self.daily_totals['nutrient_b']['daily_total']
        
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
    
    def _get_sensor_readings(self):
        """Get current sensor readings with simulation support
        
        Returns:
            Dictionary with ph, ec, tds, and temperature readings
        """
        if self.simulation_mode or self.atlas is None:
            # Return "sensor not detected" instead of simulated readings
            logger.info("Atlas sensor interface not available, reporting sensors as not detected")
            return {
                'ph': "sensor not detected",
                'ec': "sensor not detected",
                'tds': "sensor not detected",
                'temperature': "sensor not detected"
            }
        else:
            # Get readings from Atlas interface
            return {
                'ph': self.atlas.read_ph(),
                'ec': self.atlas.read_ec(),
                'tds': self.atlas.read_tds(),
                'temperature': self.atlas.read_temperature()
            }

    def run_cycle(self):
        """Run a complete dosing cycle"""
        try:
            # Mark start time
            cycle_start = time.time()
            
            # Get current readings
            readings = self._get_sensor_readings()
            current_ph = readings['ph']
            current_ec = readings['ec']
            
            # Check if sensors are detected
            if current_ph == "sensor not detected" or current_ec == "sensor not detected":
                logger.warning("Sensors not detected, skipping dosing cycle")
                self._schedule_next_run()
                return {
                    'ph_adjustment_needed': False,
                    'ec_adjustment_needed': False,
                    'error': "Sensors not detected",
                    'cycle_time': time.time() - cycle_start
                }
            
            if current_ph is None or current_ec is None:
                logger.error("Failed to get sensor readings, skipping dosing cycle")
                self._schedule_next_run()
                return {
                    'ph_adjustment_needed': False,
                    'ec_adjustment_needed': False,
                    'error': "Failed to get sensor readings",
                    'cycle_time': time.time() - cycle_start
                }
            
            logger.info(f"Current readings - pH: {current_ph}, EC: {current_ec}")
            
            # Check pH and calculate dose
            ph_adjustment_needed = False
            ph_pump, ph_dose = self._calculate_ph_dose(current_ph)
            
            if ph_pump and ph_dose > 0:
                ph_adjustment_needed = True
                logger.info(f"pH adjustment needed: {ph_pump} {ph_dose}ml")
                
                # Dose pH adjuster
                success = self._dose_ph(ph_pump, ph_dose)
                
                if not success:
                    logger.error(f"Failed to dose {ph_pump}")
            else:
                logger.info("No pH adjustment needed")
            
            # Check EC and calculate nutrient dose
            ec_adjustment_needed = False
            nutrient_pump, nutrient_dose = self._calculate_nutrient_dose(current_ec)
            
            if nutrient_pump and nutrient_dose > 0:
                ec_adjustment_needed = True
                logger.info(f"Nutrient adjustment needed: {nutrient_dose}ml")
                
                # Split into A/B doses
                a_dose = nutrient_dose[0]
                b_dose = nutrient_dose[1]
                
                # Dose nutrients
                success = self._dose_nutrients(a_dose, b_dose)
                
                if not success:
                    logger.error("Failed to dose nutrients")
            else:
                logger.info("No nutrient adjustment needed")
            
            # Schedule next run
            self._schedule_next_run()
            
            # Log completion
            cycle_time = time.time() - cycle_start
            logger.info(f"Dosing cycle completed in {cycle_time:.1f} seconds")
            
            # Return status
            return {
                'ph_adjustment_needed': ph_adjustment_needed,
                'ec_adjustment_needed': ec_adjustment_needed,
                'cycle_time': cycle_time
            }
            
        except Exception as e:
            logger.error(f"Error running dosing cycle: {e}")
            self._schedule_next_run()
            return {
                'error': str(e),
                'ph_adjustment_needed': False,
                'ec_adjustment_needed': False,
                'cycle_time': time.time() - cycle_start if 'cycle_start' in locals() else 0
            }
    
    def _dose_ph(self, pump_id: str, dose_ml: float) -> bool:
        """Dose pH adjuster
        
        Args:
            pump_id: The pump to use ('ph_up' or 'ph_down')
            dose_ml: Amount to dose in ml
            
        Returns:
            True if successful
        """
        try:
            if self.simulation_mode or self.pumps is None:
                # Simulate dosing in simulation mode
                logger.info(f"[SIMULATION] Dosing {dose_ml:.1f}ml of {pump_id}")
                # Add to history
                self._add_to_history(pump_id, dose_ml)
                # Simulate mixing time
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"[SIMULATION] Mixing for {mixing_time} seconds")
                time.sleep(1)  # Just a short delay in simulation
                return True
            
            # Check if we've exceeded daily maximum
            daily_max = self.settings.get(f'max_daily_{pump_id}', 100)
            current_total = self.daily_totals[pump_id]['daily_total']
            
            if current_total + dose_ml > daily_max:
                logger.warning(f"Daily maximum for {pump_id} exceeded, limiting dose")
                dose_ml = max(0, daily_max - current_total)
            
            if dose_ml <= 0:
                logger.warning(f"Zero or negative dose calculated for {pump_id}, skipping")
                return False
            
            # Get flow rate from settings
            flow_rate = self.settings.get(f'{pump_id}_rate', 1.0)  # ml/sec
            
            # Calculate run time
            run_time = dose_ml / flow_rate if flow_rate > 0 else 0
            
            # Run the pump
            logger.info(f"Dosing {dose_ml:.1f}ml of {pump_id} for {run_time:.1f} seconds")
            success = self.pumps.run_pump_for_seconds(pump_id, run_time)
            
            if success:
                # Add to history
                self._add_to_history(pump_id, dose_ml)
                
                # Wait for mixing
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"Mixing for {mixing_time} seconds")
                time.sleep(mixing_time)
                
                return True
            else:
                logger.error(f"Failed to run pump {pump_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error dosing {pump_id}: {e}")
            return False

    def _dose_nutrients(self, a_dose: float, b_dose: float) -> bool:
        """Dose nutrients
        
        Args:
            a_dose: Amount of nutrient A to dose in ml
            b_dose: Amount of nutrient B to dose in ml
            
        Returns:
            True if successful
        """
        try:
            if self.simulation_mode or self.pumps is None:
                # Simulate dosing in simulation mode
                logger.info(f"[SIMULATION] Dosing nutrients - A: {a_dose:.1f}ml, B: {b_dose:.1f}ml")
                # Add to history
                self._add_to_history('nutrient_a', a_dose)
                self._add_to_history('nutrient_b', b_dose)
                # Simulate mixing time
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"[SIMULATION] Mixing for {mixing_time} seconds")
                time.sleep(1)  # Just a short delay in simulation
                return True
            
            # Check if we've exceeded daily maximum for nutrients
            daily_max_a = self.settings.get('max_daily_nutrient_a', 100)
            daily_max_b = self.settings.get('max_daily_nutrient_b', 100)
            
            current_total_a = self.daily_totals['nutrient_a']['daily_total']
            current_total_b = self.daily_totals['nutrient_b']['daily_total']
            
            if current_total_a + a_dose > daily_max_a:
                logger.warning("Daily maximum for nutrient A exceeded, limiting dose")
                a_dose = max(0, daily_max_a - current_total_a)
            
            if current_total_b + b_dose > daily_max_b:
                logger.warning("Daily maximum for nutrient B exceeded, limiting dose")
                b_dose = max(0, daily_max_b - current_total_b)
            
            if a_dose <= 0 and b_dose <= 0:
                logger.warning("Zero or negative dose calculated for nutrients, skipping")
                return False
            
            # Get flow rates
            a_flow_rate = self.settings.get('nutrient_a_rate', 1.0)  # ml/sec
            b_flow_rate = self.settings.get('nutrient_b_rate', 1.0)  # ml/sec
            
            # Calculate run times
            a_run_time = a_dose / a_flow_rate if a_flow_rate > 0 and a_dose > 0 else 0
            b_run_time = b_dose / b_flow_rate if b_flow_rate > 0 and b_dose > 0 else 0
            
            # Dose nutrient A
            if a_dose > 0:
                logger.info(f"Dosing {a_dose:.1f}ml of nutrient A for {a_run_time:.1f} seconds")
                success_a = self.pumps.run_pump_for_seconds('nutrient_a', a_run_time)
                
                if success_a:
                    self._add_to_history('nutrient_a', a_dose)
                else:
                    logger.error("Failed to run nutrient A pump")
                    return False
            
            # Wait briefly between nutrient doses
            if a_dose > 0 and b_dose > 0:
                time.sleep(2)
            
            # Dose nutrient B
            if b_dose > 0:
                logger.info(f"Dosing {b_dose:.1f}ml of nutrient B for {b_run_time:.1f} seconds")
                success_b = self.pumps.run_pump_for_seconds('nutrient_b', b_run_time)
                
                if success_b:
                    self._add_to_history('nutrient_b', b_dose)
                else:
                    logger.error("Failed to run nutrient B pump")
                    return False
            
            # Wait for mixing
            if a_dose > 0 or b_dose > 0:
                mixing_time = self.settings.get('mixing_time', 30)
                logger.info(f"Mixing for {mixing_time} seconds")
                time.sleep(mixing_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Error dosing nutrients: {e}")
            return False

    def _add_to_history(self, pump_id: str, volume: float):
        """Add a dosing event to history
        
        Args:
            pump_id: The pump used
            volume: Volume dosed in ml
        """
        timestamp = time.time()
        
        # Add to daily total
        if pump_id in self.daily_totals:
            self.daily_totals[pump_id]['daily_total'] += volume
        
        # Add to history
        entry = {
            'pump': pump_id,
            'volume': volume,
            'timestamp': timestamp,
            'time': datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.dosing_history.append(entry)
        
        # Limit history to last 100 entries
        if len(self.dosing_history) > 100:
            self.dosing_history = self.dosing_history[-100:]
    
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
        current_total = self.daily_totals[pump_id]['daily_total']
        
        if current_total + volume_ml > max_daily:
            logger.warning(f"Daily limit for {pump_id} would be exceeded")
            return False
        
        # Run the pump
        success = self.pumps.run_pump_for_seconds(pump_id, run_time)
        
        if success:
            # Update dosing history
            self.daily_totals[pump_id]['daily_total'] += volume_ml
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
            if self.atlas is None:
                # Handle case where sensors are not detected
                ph = "sensor not detected"
                ec = "sensor not detected"
                
                # When sensors are not detected, we can't determine if adjustments are needed
                ph_adjustment_needed = False
                ec_adjustment_needed = False
                ph_pump = None
                ph_dose = 0
                nutrient_type = None
                nutrient_dose = 0
            else:
                # Get readings from Atlas
                ph = self.atlas.read_ph()
                ec = self.atlas.read_ec()
                
                # Calculate adjustment needs if we have numeric readings
                if isinstance(ph, (int, float)) and isinstance(ec, (int, float)):
                    ph_pump, ph_dose = self._calculate_ph_dose(ph)
                    nutrient_type, nutrient_dose = self._calculate_nutrient_dose(ec)
                    
                    # Determine if adjustments are needed
                    ph_adjustment_needed = ph_pump is not None and ph_dose > 0
                    ec_adjustment_needed = nutrient_type is not None and sum(nutrient_dose) > 0 if isinstance(nutrient_dose, tuple) else nutrient_dose > 0
                else:
                    # If readings are not numeric, we can't determine if adjustments are needed
                    ph_adjustment_needed = False
                    ec_adjustment_needed = False
                    ph_pump = None
                    ph_dose = 0
                    nutrient_type = None
                    nutrient_dose = 0
            
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
                'sensors_detected': self.atlas is not None
            }
        except Exception as e:
            logger.error(f"Error getting dosing status: {e}")
            return {
                'running': self.running,
                'error': str(e),
                'sensors_detected': self.atlas is not None
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
            self.config_manager.set_setting('dosing', self.settings)
            self.config_manager.save_config()
            
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
            self.config_manager.set_setting('dosing', self.settings)
            self.config_manager.save_config()
            
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
            self.config_manager.set_setting('dosing', self.settings)
            self.config_manager.save_config()
            
            logger.info(f"Updated safety settings: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating safety settings: {e}")
            return False 