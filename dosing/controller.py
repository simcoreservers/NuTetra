#!/usr/bin/env python3
# NuTetra Dosing Controller
# Implements smart dosing algorithms for pH and EC/PPM adjustment

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable

class DosingController:
    """
    Sophisticated dosing controller for hydroponic systems.
    
    Features:
    - Smart pH adjustment with gradual dosing
    - EC/PPM management with nutrient ratio maintenance
    - Safety protocols to prevent overdosing
    - Temperature-based adjustments
    - Dilution compensation
    """
    
    # Dosing states
    IDLE = 'idle'               # No active dosing
    DOSING_PH_UP = 'ph_up'      # Adding pH up solution
    DOSING_PH_DOWN = 'ph_down'  # Adding pH down solution
    DOSING_NUTRIENT_A = 'nut_a' # Adding nutrient A
    DOSING_NUTRIENT_B = 'nut_b' # Adding nutrient B
    MEASURING = 'measuring'     # Waiting for measurements to stabilize
    ERROR = 'error'             # Error state
    
    def __init__(self, 
                 sensor_manager,
                 pump_manager, 
                 config_manager,
                 reservoir_volume_liters: float = 100.0):
        """
        Initialize the dosing controller.
        
        Args:
            sensor_manager: Interface to Atlas Scientific sensors
            pump_manager: Interface to pumps for dosing
            config_manager: System configuration manager
            reservoir_volume_liters: Volume of nutrient reservoir in liters
        """
        self.logger = logging.getLogger("NuTetra.Dosing")
        self.sensor_manager = sensor_manager
        self.pump_manager = pump_manager
        self.config = config_manager
        
        # System parameters
        self.reservoir_volume = reservoir_volume_liters
        self.system_state = self.IDLE
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Safety parameters (to be loaded from config)
        self.max_daily_dosage_ml = {
            'ph_up': 100.0,
            'ph_down': 100.0,
            'nutrient_a': 200.0,
            'nutrient_b': 200.0
        }
        
        # Dosing history for safety limits
        self.dosing_history = {
            'ph_up': [],
            'ph_down': [],
            'nutrient_a': [],
            'nutrient_b': []
        }
        
        # Target parameters (to be loaded from config)
        self.target_ph = 6.0
        self.target_ec = 1800.0  # μS/cm
        self.ph_tolerance = 0.2   # ±0.2 pH
        self.ec_tolerance = 100.0  # ±100 μS/cm
        
        # pH control parameters
        self.ph_band_narrow = 0.1   # Use small doses when within this band
        self.ph_band_medium = 0.3   # Use medium doses when within this band
        self.ph_band_wide = 0.6     # Use large doses when outside this band
        
        # EC control parameters
        self.ec_band_narrow = 50.0   # μS/cm - Use small doses when within this band
        self.ec_band_medium = 150.0  # μS/cm - Use medium doses when within this band
        self.ec_band_wide = 300.0    # μS/cm - Use large doses when outside this band
        
        # Nutrient ratios (to be loaded from config)
        self.nutrient_ratio_a_to_b = 1.0  # 1:1 ratio by default
        
        # Dosing ml per unit change (to be calibrated or loaded from config)
        # Example: ml of pH up needed to raise 1L of water by 1.0 pH unit
        self.dose_efficiency = {
            'ph_up': 0.5,      # ml per 0.1 pH decrease per 100L
            'ph_down': 0.5,    # ml per 0.1 pH increase per 100L
            'nutrient_a': 5.0, # ml per 100 μS/cm increase per 100L
            'nutrient_b': 5.0  # ml per 100 μS/cm increase per 100L
        }
        
        # Stabilization times after dosing (seconds)
        self.stabilization_time = {
            'ph_up': 300,      # 5 minutes for pH to stabilize after dosing
            'ph_down': 300,    # 5 minutes for pH to stabilize after dosing
            'nutrient_a': 600, # 10 minutes for EC to stabilize after dosing
            'nutrient_b': 600  # 10 minutes for EC to stabilize after dosing
        }
        
        # Time between dosing cycles (seconds)
        self.dosing_interval = 3600  # 1 hour between full dosing cycles by default
        
        # Last successful dosing timestamp
        self.last_dosing_time = {
            'ph_up': 0,
            'ph_down': 0,
            'nutrient_a': 0,
            'nutrient_b': 0,
            'any': 0  # Any type of dosing
        }
        
        # Initialize from config
        self._load_config()
        
    def _load_config(self):
        """Load dosing configuration from config manager."""
        try:
            dosing_config = self.config.get_setting('dosing', {})
            
            # Target values
            self.target_ph = float(dosing_config.get('target_ph', self.target_ph))
            self.target_ec = float(dosing_config.get('target_ec', self.target_ec))
            self.ph_tolerance = float(dosing_config.get('ph_tolerance', self.ph_tolerance))
            self.ec_tolerance = float(dosing_config.get('ec_tolerance', self.ec_tolerance))
            
            # Safety limits
            self.max_daily_dosage_ml = dosing_config.get('max_daily_dosage_ml', self.max_daily_dosage_ml)
            
            # Nutrient ratios
            self.nutrient_ratio_a_to_b = float(dosing_config.get('nutrient_ratio_a_to_b', self.nutrient_ratio_a_to_b))
            
            # Dosing efficiency
            if 'dose_efficiency' in dosing_config:
                self.dose_efficiency.update(dosing_config['dose_efficiency'])
                
            # Stabilization times
            if 'stabilization_time' in dosing_config:
                self.stabilization_time.update(dosing_config['stabilization_time'])
                
            # Dosing interval
            self.dosing_interval = int(dosing_config.get('dosing_interval', self.dosing_interval))
            
            # Reservoir volume
            self.reservoir_volume = float(dosing_config.get('reservoir_volume_liters', self.reservoir_volume))
            
            self.logger.info(f"Loaded dosing configuration: pH target {self.target_ph}±{self.ph_tolerance}, EC target {self.target_ec}±{self.ec_tolerance}")
            
        except Exception as e:
            self.logger.error(f"Error loading dosing configuration: {e}")
    
    def save_config(self):
        """Save current dosing configuration to config manager."""
        try:
            dosing_config = {
                'target_ph': self.target_ph,
                'target_ec': self.target_ec,
                'ph_tolerance': self.ph_tolerance,
                'ec_tolerance': self.ec_tolerance,
                'max_daily_dosage_ml': self.max_daily_dosage_ml,
                'nutrient_ratio_a_to_b': self.nutrient_ratio_a_to_b,
                'dose_efficiency': self.dose_efficiency,
                'stabilization_time': self.stabilization_time,
                'dosing_interval': self.dosing_interval,
                'reservoir_volume_liters': self.reservoir_volume
            }
            
            self.config.set_setting('dosing', dosing_config)
            self.config.save_config()
            self.logger.info("Saved dosing configuration")
            return True
        except Exception as e:
            self.logger.error(f"Error saving dosing configuration: {e}")
            return False
    
    def set_target_ph(self, ph: float) -> bool:
        """Set the target pH value."""
        with self.lock:
            if 3.0 <= ph <= 10.0:  # Reasonable pH range
                self.target_ph = ph
                self.logger.info(f"Target pH set to {ph}")
                return self.save_config()
            else:
                self.logger.error(f"Invalid pH target: {ph}")
                return False
    
    def set_target_ec(self, ec: float) -> bool:
        """Set the target EC value in μS/cm."""
        with self.lock:
            if 0.0 <= ec <= 5000.0:  # Reasonable EC range
                self.target_ec = ec
                self.logger.info(f"Target EC set to {ec}")
                return self.save_config()
            else:
                self.logger.error(f"Invalid EC target: {ec}")
                return False
    
    def set_ph_tolerance(self, tolerance: float) -> bool:
        """Set the pH tolerance range."""
        with self.lock:
            if 0.05 <= tolerance <= 1.0:
                self.ph_tolerance = tolerance
                self.logger.info(f"pH tolerance set to ±{tolerance}")
                return self.save_config()
            else:
                self.logger.error(f"Invalid pH tolerance: {tolerance}")
                return False
    
    def set_ec_tolerance(self, tolerance: float) -> bool:
        """Set the EC tolerance range in μS/cm."""
        with self.lock:
            if 10.0 <= tolerance <= 500.0:
                self.ec_tolerance = tolerance
                self.logger.info(f"EC tolerance set to ±{tolerance}")
                return self.save_config()
            else:
                self.logger.error(f"Invalid EC tolerance: {tolerance}")
                return False
    
    def set_reservoir_volume(self, volume_liters: float) -> bool:
        """Set the reservoir volume in liters."""
        with self.lock:
            if volume_liters > 0:
                self.reservoir_volume = volume_liters
                self.logger.info(f"Reservoir volume set to {volume_liters} liters")
                return self.save_config()
            else:
                self.logger.error(f"Invalid reservoir volume: {volume_liters}")
                return False
    
    def set_nutrient_ratio(self, ratio: float) -> bool:
        """Set the nutrient A to B ratio."""
        with self.lock:
            if 0.1 <= ratio <= 10.0:
                self.nutrient_ratio_a_to_b = ratio
                self.logger.info(f"Nutrient A:B ratio set to {ratio}")
                return self.save_config()
            else:
                self.logger.error(f"Invalid nutrient ratio: {ratio}")
                return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get the current dosing controller state."""
        with self.lock:
            return {
                'state': self.system_state,
                'target_ph': self.target_ph,
                'target_ec': self.target_ec,
                'ph_tolerance': self.ph_tolerance,
                'ec_tolerance': self.ec_tolerance,
                'reservoir_volume': self.reservoir_volume,
                'nutrient_ratio': self.nutrient_ratio_a_to_b,
                'last_dosing': self.last_dosing_time['any'],
                'dosing_interval': self.dosing_interval,
                'next_dosing': self.last_dosing_time['any'] + self.dosing_interval,
                'dosing_history': self._get_summary_history()
            }
    
    def _get_summary_history(self) -> Dict[str, Any]:
        """Get a summary of recent dosing history."""
        now = time.time()
        last_24h = now - 86400  # 24 hours
        
        summary = {}
        for pump_type, history in self.dosing_history.items():
            # Filter to last 24 hours
            recent = [entry for entry in history if entry['timestamp'] >= last_24h]
            
            # Calculate total volume used in last 24 hours
            total_volume = sum(entry['volume_ml'] for entry in recent)
            
            # Get most recent dosing event
            most_recent = max([0] + [entry['timestamp'] for entry in recent]) if recent else 0
            
            summary[pump_type] = {
                'total_24h_ml': total_volume,
                'count_24h': len(recent),
                'last_dosing': most_recent,
                'last_amount_ml': recent[-1]['volume_ml'] if recent else 0
            }
        
        return summary
    
    def _clean_old_history(self, days: int = 7):
        """Remove dosing history older than specified days."""
        cutoff = time.time() - days * 86400
        
        with self.lock:
            for pump_type in self.dosing_history:
                self.dosing_history[pump_type] = [
                    entry for entry in self.dosing_history[pump_type]
                    if entry['timestamp'] >= cutoff
                ]
    
    def is_dosing_allowed(self) -> bool:
        """Check if dosing is allowed based on time and other constraints."""
        with self.lock:
            # Prevent dosing if in an active state
            if self.system_state != self.IDLE:
                self.logger.debug(f"Dosing not allowed: system in {self.system_state} state")
                return False
            
            # Check if the minimum interval has passed since last dosing
            now = time.time()
            if now - self.last_dosing_time['any'] < self.dosing_interval:
                self.logger.debug("Dosing not allowed: minimum interval not elapsed")
                return False
            
            return True
    
    def is_pump_within_safety_limits(self, pump_type: str, volume_ml: float) -> bool:
        """Check if the requested dosing amount is within safety limits."""
        with self.lock:
            # Check daily limit
            if pump_type not in self.max_daily_dosage_ml:
                self.logger.error(f"Unknown pump type: {pump_type}")
                return False
            
            # Calculate amount used in last 24 hours
            now = time.time()
            last_24h = now - 86400  # 24 hours
            
            history = self.dosing_history.get(pump_type, [])
            daily_usage = sum(
                entry['volume_ml'] for entry in history
                if entry['timestamp'] >= last_24h
            )
            
            # Check if new dosing would exceed limit
            if daily_usage + volume_ml > self.max_daily_dosage_ml[pump_type]:
                self.logger.warning(
                    f"Safety limit exceeded for {pump_type}: " +
                    f"Used {daily_usage:.2f}ml, requested {volume_ml:.2f}ml, " +
                    f"limit {self.max_daily_dosage_ml[pump_type]:.2f}ml in 24h"
                )
                return False
            
            return True
    
    def _log_dosing_event(self, pump_type: str, volume_ml: float, reason: str):
        """Log a dosing event to history."""
        with self.lock:
            now = time.time()
            
            # Add to dosing history
            if pump_type in self.dosing_history:
                self.dosing_history[pump_type].append({
                    'timestamp': now,
                    'volume_ml': volume_ml,
                    'reason': reason,
                    'readings_before': self.sensor_manager.readings.copy()
                })
            
            # Update last dosing time
            self.last_dosing_time[pump_type] = now
            self.last_dosing_time['any'] = now
            
            # Log the event
            self.logger.info(f"Dosed {volume_ml:.2f}ml of {pump_type}: {reason}")
            
            # Clean old history periodically
            if len(self.dosing_history[pump_type]) % 10 == 0:
                self._clean_old_history()
    
    async def dose_ph_adjustment(self) -> Dict[str, Any]:
        """
        Perform pH adjustment dosing if needed.
        
        Returns:
            Dictionary with results of the operation
        """
        with self.lock:
            # Check if we can dose
            if not self.is_dosing_allowed():
                return {'success': False, 'message': 'Dosing not allowed at this time'}
            
            # Get current pH reading
            current_ph = self.sensor_manager.readings.get('pH')
            if current_ph is None:
                return {'success': False, 'message': 'No pH reading available'}
            
            # Calculate pH deviation
            ph_deviation = current_ph - self.target_ph
            
            # Check if pH is within tolerance
            if abs(ph_deviation) <= self.ph_tolerance:
                self.logger.debug(f"pH {current_ph} is within tolerance of target {self.target_ph}±{self.ph_tolerance}")
                return {'success': True, 'message': 'pH within tolerance, no dosing needed'}
            
            # Determine which pump to use
            if ph_deviation > 0:  # pH too high, need pH down
                pump_type = 'ph_down'
                self.system_state = self.DOSING_PH_DOWN
            else:  # pH too low, need pH up
                pump_type = 'ph_up'
                self.system_state = self.DOSING_PH_UP
            
            try:
                # Calculate dosing amount based on deviation
                abs_deviation = abs(ph_deviation)
                
                if abs_deviation <= self.ph_band_narrow:
                    # Small adjustment
                    adjustment_factor = 0.2
                elif abs_deviation <= self.ph_band_medium:
                    # Medium adjustment
                    adjustment_factor = 0.5
                else:
                    # Large adjustment
                    adjustment_factor = 1.0
                
                # Calculate volume in mL
                # Formula: deviation * efficiency * adjustment_factor * volume_ratio
                volume_ml = abs_deviation * 10 * self.dose_efficiency[pump_type] * adjustment_factor * (self.reservoir_volume / 100.0)
                
                # Apply maximum single dose limit
                max_single_dose = self.max_daily_dosage_ml[pump_type] * 0.3  # Max 30% of daily limit in one dose
                volume_ml = min(volume_ml, max_single_dose)
                
                # Round to 2 decimal places for precision
                volume_ml = round(volume_ml, 2)
                
                # Check safety limits
                if not self.is_pump_within_safety_limits(pump_type, volume_ml):
                    self.system_state = self.IDLE
                    return {
                        'success': False, 
                        'message': f'Safety limits would be exceeded for {pump_type}'
                    }
                
                # Perform the actual dosing
                self.logger.info(f"Dosing {volume_ml}ml of {pump_type} for pH adjustment: current {current_ph}, target {self.target_ph}")
                
                # Activate the appropriate pump
                if pump_type == 'ph_up':
                    success = await self.pump_manager.dose_ph_up(volume_ml)
                else:  # ph_down
                    success = await self.pump_manager.dose_ph_down(volume_ml)
                
                if success:
                    # Log the dosing event
                    reason = f"pH adjustment: {current_ph} → {self.target_ph}"
                    self._log_dosing_event(pump_type, volume_ml, reason)
                    
                    # Set stabilization waiting period
                    self.system_state = self.MEASURING
                    
                    # Wait for stabilization (non-blocking, just return)
                    result = {
                        'success': True,
                        'message': f'Dosed {volume_ml}ml of {pump_type} for pH adjustment',
                        'volume_ml': volume_ml,
                        'pump_type': pump_type,
                        'current_ph': current_ph,
                        'target_ph': self.target_ph,
                        'stabilization_time': self.stabilization_time[pump_type]
                    }
                else:
                    result = {
                        'success': False,
                        'message': f'Pump activation failed for {pump_type}'
                    }
                
                # Reset state after dosing
                self.system_state = self.IDLE
                return result
                
            except Exception as e:
                self.logger.error(f"Error during pH dosing: {e}")
                self.system_state = self.ERROR
                return {'success': False, 'message': f'Error during pH dosing: {str(e)}'}
            finally:
                # Ensure we reset state if there was an exception
                if self.system_state in [self.DOSING_PH_UP, self.DOSING_PH_DOWN]:
                    self.system_state = self.IDLE
    
    async def dose_nutrients(self) -> Dict[str, Any]:
        """
        Perform EC/nutrient adjustment dosing if needed.
        
        Returns:
            Dictionary with results of the operation
        """
        with self.lock:
            # Check if we can dose
            if not self.is_dosing_allowed():
                return {'success': False, 'message': 'Dosing not allowed at this time'}
            
            # Get current EC reading
            current_ec = self.sensor_manager.readings.get('EC')
            if current_ec is None:
                return {'success': False, 'message': 'No EC reading available'}
            
            # Calculate EC deviation
            ec_deviation = self.target_ec - current_ec  # Positive means we need to add nutrients
            
            # Check if EC is within tolerance
            if abs(ec_deviation) <= self.ec_tolerance:
                self.logger.debug(f"EC {current_ec} is within tolerance of target {self.target_ec}±{self.ec_tolerance}")
                return {'success': True, 'message': 'EC within tolerance, no dosing needed'}
            
            # Only add nutrients, never remove (dilution must be manual or via auto top-off system)
            if ec_deviation < 0:
                self.logger.warning(f"EC {current_ec} is higher than target {self.target_ec}, dilution required")
                return {'success': False, 'message': 'EC too high, manual dilution required'}
            
            try:
                # Calculate dosing amount based on deviation
                if ec_deviation <= self.ec_band_narrow:
                    # Small adjustment
                    adjustment_factor = 0.2
                elif ec_deviation <= self.ec_band_medium:
                    # Medium adjustment
                    adjustment_factor = 0.5
                else:
                    # Large adjustment
                    adjustment_factor = 1.0
                
                # Volume calculation for each nutrient
                # Formula: deviation * efficiency * adjustment_factor * volume_ratio
                base_volume_ml = ec_deviation / 100.0 * self.dose_efficiency['nutrient_a'] * adjustment_factor * (self.reservoir_volume / 100.0)
                
                # A/B ratio distribution
                ratio_sum = 1.0 + self.nutrient_ratio_a_to_b
                volume_a_ml = base_volume_ml * (self.nutrient_ratio_a_to_b / ratio_sum)
                volume_b_ml = base_volume_ml * (1.0 / ratio_sum)
                
                # Round to 2 decimal places for precision
                volume_a_ml = round(volume_a_ml, 2)
                volume_b_ml = round(volume_b_ml, 2)
                
                # Apply maximum single dose limit for each nutrient
                max_single_dose_a = self.max_daily_dosage_ml['nutrient_a'] * 0.3
                max_single_dose_b = self.max_daily_dosage_ml['nutrient_b'] * 0.3
                volume_a_ml = min(volume_a_ml, max_single_dose_a)
                volume_b_ml = min(volume_b_ml, max_single_dose_b)
                
                # Check safety limits
                if not self.is_pump_within_safety_limits('nutrient_a', volume_a_ml):
                    return {
                        'success': False, 
                        'message': 'Safety limits would be exceeded for nutrient A'
                    }
                
                if not self.is_pump_within_safety_limits('nutrient_b', volume_b_ml):
                    return {
                        'success': False, 
                        'message': 'Safety limits would be exceeded for nutrient B'
                    }
                
                # Perform the actual dosing - Nutrient A first
                self.logger.info(f"Dosing {volume_a_ml}ml of nutrient A for EC adjustment: current {current_ec}, target {self.target_ec}")
                self.system_state = self.DOSING_NUTRIENT_A
                
                success_a = await self.pump_manager.dose_nutrient_a(volume_a_ml)
                
                if success_a:
                    # Log the dosing event for nutrient A
                    reason = f"EC adjustment: {current_ec} → {self.target_ec}"
                    self._log_dosing_event('nutrient_a', volume_a_ml, reason)
                    
                    # Now dose nutrient B
                    self.logger.info(f"Dosing {volume_b_ml}ml of nutrient B for EC adjustment")
                    self.system_state = self.DOSING_NUTRIENT_B
                    
                    success_b = await self.pump_manager.dose_nutrient_b(volume_b_ml)
                    
                    if success_b:
                        # Log the dosing event for nutrient B
                        self._log_dosing_event('nutrient_b', volume_b_ml, reason)
                        
                        # Set measuring state
                        self.system_state = self.MEASURING
                        
                        result = {
                            'success': True,
                            'message': f'Dosed nutrients for EC adjustment',
                            'volume_a_ml': volume_a_ml,
                            'volume_b_ml': volume_b_ml,
                            'current_ec': current_ec,
                            'target_ec': self.target_ec,
                            'stabilization_time': self.stabilization_time['nutrient_a']  # Use longer of the two
                        }
                    else:
                        result = {
                            'success': False,
                            'message': 'Pump activation failed for nutrient B'
                        }
                else:
                    result = {
                        'success': False,
                        'message': 'Pump activation failed for nutrient A'
                    }
                
                # Reset state after dosing
                self.system_state = self.IDLE
                return result
                
            except Exception as e:
                self.logger.error(f"Error during nutrient dosing: {e}")
                self.system_state = self.ERROR
                return {'success': False, 'message': f'Error during nutrient dosing: {str(e)}'}
            finally:
                # Ensure we reset state if there was an exception
                if self.system_state in [self.DOSING_NUTRIENT_A, self.DOSING_NUTRIENT_B]:
                    self.system_state = self.IDLE
    
    async def run_dosing_cycle(self) -> Dict[str, Any]:
        """
        Run a complete dosing cycle (pH and nutrients).
        
        Returns:
            Dictionary with results of the operation
        """
        results = {
            'timestamp': time.time(),
            'ph_dosing': None,
            'nutrient_dosing': None,
            'overall_success': False
        }
        
        # First, check if dosing is allowed
        if not self.is_dosing_allowed():
            results['message'] = 'Dosing not allowed at this time'
            return results
        
        # Get fresh sensor readings
        self.sensor_manager.read_all()
        
        # Step 1: Do pH adjustment first
        ph_result = await self.dose_ph_adjustment()
        results['ph_dosing'] = ph_result
        
        # If pH dosing was done, wait for stabilization before proceeding to nutrients
        if ph_result.get('success', False) and 'stabilization_time' in ph_result:
            # In a real implementation, you might want to make this a background task
            # that waits for stabilization and then proceeds
            self.logger.info(f"Waiting for pH stabilization: {ph_result['stabilization_time']} seconds")
            
            # In a real async implementation, you might use:
            # await asyncio.sleep(ph_result['stabilization_time'])
            
            # Get fresh readings after stabilization
            self.sensor_manager.read_all()
        
        # Step 2: Do nutrient/EC adjustment
        nutrient_result = await self.dose_nutrients()
        results['nutrient_dosing'] = nutrient_result
        
        # Determine overall success
        results['overall_success'] = (
            ph_result.get('success', False) or 
            nutrient_result.get('success', False)
        )
        
        if results['overall_success']:
            results['message'] = 'Dosing cycle completed successfully'
        else:
            results['message'] = 'Dosing cycle completed with errors'
        
        return results
    
    def calculate_dilution_compensation(self, added_water_liters: float) -> Dict[str, float]:
        """
        Calculate nutrient amounts needed to compensate for dilution when adding water.
        
        Args:
            added_water_liters: Amount of fresh water added in liters
            
        Returns:
            Dictionary with recommended nutrient amounts
        """
        # Get current EC
        current_ec = self.sensor_manager.readings.get('EC')
        if current_ec is None:
            return {'error': 'No EC reading available'}
        
        # Calculate new reservoir volume
        new_volume = self.reservoir_volume + added_water_liters
        
        # Calculate EC after dilution (before compensation)
        diluted_ec = current_ec * (self.reservoir_volume / new_volume)
        
        # Calculate EC drop due to dilution
        ec_drop = current_ec - diluted_ec
        
        # Calculate compensation amounts using the same formula from dose_nutrients
        # but based on the EC drop instead of deviation
        base_volume_ml = ec_drop / 100.0 * self.dose_efficiency['nutrient_a'] * (new_volume / 100.0)
        
        # A/B ratio distribution
        ratio_sum = 1.0 + self.nutrient_ratio_a_to_b
        volume_a_ml = base_volume_ml * (self.nutrient_ratio_a_to_b / ratio_sum)
        volume_b_ml = base_volume_ml * (1.0 / ratio_sum)
        
        return {
            'nutrient_a_ml': round(volume_a_ml, 2),
            'nutrient_b_ml': round(volume_b_ml, 2),
            'current_ec': current_ec,
            'diluted_ec': round(diluted_ec, 2),
            'target_ec': self.target_ec,
            'added_water_liters': added_water_liters
        }
    
    async def compensate_for_dilution(self, added_water_liters: float) -> Dict[str, Any]:
        """
        Add nutrients to compensate for dilution after adding water.
        
        Args:
            added_water_liters: Amount of fresh water added in liters
            
        Returns:
            Dictionary with results of the operation
        """
        with self.lock:
            # Check if we can dose
            if not self.is_dosing_allowed():
                return {'success': False, 'message': 'Dosing not allowed at this time'}
            
            # Calculate required nutrients
            compensation = self.calculate_dilution_compensation(added_water_liters)
            
            if 'error' in compensation:
                return {'success': False, 'message': compensation['error']}
            
            volume_a_ml = compensation['nutrient_a_ml']
            volume_b_ml = compensation['nutrient_b_ml']
            
            # Check safety limits
            if not self.is_pump_within_safety_limits('nutrient_a', volume_a_ml):
                return {
                    'success': False, 
                    'message': 'Safety limits would be exceeded for nutrient A'
                }
            
            if not self.is_pump_within_safety_limits('nutrient_b', volume_b_ml):
                return {
                    'success': False, 
                    'message': 'Safety limits would be exceeded for nutrient B'
                }
            
            try:
                # Update reservoir volume first
                old_volume = self.reservoir_volume
                self.reservoir_volume = old_volume + added_water_liters
                self.save_config()
                
                # Perform the dosing - Nutrient A first
                self.logger.info(
                    f"Dosing {volume_a_ml}ml of nutrient A for dilution compensation: " +
                    f"Added {added_water_liters}L water, EC impact {compensation['current_ec']} → {compensation['diluted_ec']}"
                )
                self.system_state = self.DOSING_NUTRIENT_A
                
                success_a = await self.pump_manager.dose_nutrient_a(volume_a_ml)
                
                if success_a:
                    # Log the dosing event for nutrient A
                    reason = f"Dilution compensation: Added {added_water_liters}L water"
                    self._log_dosing_event('nutrient_a', volume_a_ml, reason)
                    
                    # Now dose nutrient B
                    self.logger.info(f"Dosing {volume_b_ml}ml of nutrient B for dilution compensation")
                    self.system_state = self.DOSING_NUTRIENT_B
                    
                    success_b = await self.pump_manager.dose_nutrient_b(volume_b_ml)
                    
                    if success_b:
                        # Log the dosing event for nutrient B
                        self._log_dosing_event('nutrient_b', volume_b_ml, reason)
                        
                        # Set measuring state
                        self.system_state = self.MEASURING
                        
                        result = {
                            'success': True,
                            'message': f'Dosed nutrients for dilution compensation',
                            'volume_a_ml': volume_a_ml,
                            'volume_b_ml': volume_b_ml,
                            'added_water_liters': added_water_liters,
                            'new_reservoir_volume': self.reservoir_volume,
                            'current_ec': compensation['current_ec'],
                            'diluted_ec': compensation['diluted_ec'],
                            'target_ec': self.target_ec,
                            'stabilization_time': self.stabilization_time['nutrient_a']
                        }
                    else:
                        result = {
                            'success': False,
                            'message': 'Pump activation failed for nutrient B'
                        }
                else:
                    result = {
                        'success': False,
                        'message': 'Pump activation failed for nutrient A'
                    }
                
                # Reset state after dosing
                self.system_state = self.IDLE
                return result
                
            except Exception as e:
                self.logger.error(f"Error during dilution compensation: {e}")
                self.system_state = self.ERROR
                return {'success': False, 'message': f'Error during dilution compensation: {str(e)}'}
            finally:
                # Ensure we reset state if there was an exception
                if self.system_state in [self.DOSING_NUTRIENT_A, self.DOSING_NUTRIENT_B]:
                    self.system_state = self.IDLE
                    
# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("DosingController module - import to use") 