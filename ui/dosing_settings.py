#!/usr/bin/env python3
# NuTetra Dosing Settings Screen
# Configure pH and EC target ranges and dosing parameters

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QGridLayout, QGroupBox,
                           QDoubleSpinBox, QCheckBox, QMessageBox,
                           QTabWidget, QSlider, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class DosingSettingsScreen(QWidget):
    def __init__(self, system):
        super().__init__()
        self.logger = logging.getLogger("NuTetra.UI.DosingSettings")
        self.logger.info("Initializing Dosing Settings Screen")
        
        self.system = system
        
        # Initialize UI components
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Dosing Settings")
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Tabs for different settings
        tabs = QTabWidget()
        
        # Target Ranges Tab
        target_tab = QWidget()
        target_layout = QVBoxLayout()
        
        # pH Target Range
        ph_group = QGroupBox("pH Target Range")
        ph_layout = QGridLayout()
        
        ph_layout.addWidget(QLabel("Target Minimum:"), 0, 0)
        self.ph_min_spin = QDoubleSpinBox()
        self.ph_min_spin.setRange(0.0, 14.0)
        self.ph_min_spin.setDecimals(1)
        self.ph_min_spin.setSingleStep(0.1)
        self.ph_min_spin.setValue(5.8)
        ph_layout.addWidget(self.ph_min_spin, 0, 1)
        
        ph_layout.addWidget(QLabel("Target Maximum:"), 1, 0)
        self.ph_max_spin = QDoubleSpinBox()
        self.ph_max_spin.setRange(0.0, 14.0)
        self.ph_max_spin.setDecimals(1)
        self.ph_max_spin.setSingleStep(0.1)
        self.ph_max_spin.setValue(6.2)
        ph_layout.addWidget(self.ph_max_spin, 1, 1)
        
        ph_layout.addWidget(QLabel("Alert Minimum:"), 2, 0)
        self.ph_alert_min_spin = QDoubleSpinBox()
        self.ph_alert_min_spin.setRange(0.0, 14.0)
        self.ph_alert_min_spin.setDecimals(1)
        self.ph_alert_min_spin.setSingleStep(0.1)
        self.ph_alert_min_spin.setValue(5.5)
        ph_layout.addWidget(self.ph_alert_min_spin, 2, 1)
        
        ph_layout.addWidget(QLabel("Alert Maximum:"), 3, 0)
        self.ph_alert_max_spin = QDoubleSpinBox()
        self.ph_alert_max_spin.setRange(0.0, 14.0)
        self.ph_alert_max_spin.setDecimals(1)
        self.ph_alert_max_spin.setSingleStep(0.1)
        self.ph_alert_max_spin.setValue(6.5)
        ph_layout.addWidget(self.ph_alert_max_spin, 3, 1)
        
        ph_group.setLayout(ph_layout)
        target_layout.addWidget(ph_group)
        
        # EC Target Range
        ec_group = QGroupBox("EC Target Range (mS/cm)")
        ec_layout = QGridLayout()
        
        ec_layout.addWidget(QLabel("Target Minimum:"), 0, 0)
        self.ec_min_spin = QDoubleSpinBox()
        self.ec_min_spin.setRange(0.0, 5.0)
        self.ec_min_spin.setDecimals(2)
        self.ec_min_spin.setSingleStep(0.1)
        self.ec_min_spin.setValue(1.0)
        ec_layout.addWidget(self.ec_min_spin, 0, 1)
        
        ec_layout.addWidget(QLabel("Target Maximum:"), 1, 0)
        self.ec_max_spin = QDoubleSpinBox()
        self.ec_max_spin.setRange(0.0, 5.0)
        self.ec_max_spin.setDecimals(2)
        self.ec_max_spin.setSingleStep(0.1)
        self.ec_max_spin.setValue(1.6)
        ec_layout.addWidget(self.ec_max_spin, 1, 1)
        
        ec_layout.addWidget(QLabel("Alert Minimum:"), 2, 0)
        self.ec_alert_min_spin = QDoubleSpinBox()
        self.ec_alert_min_spin.setRange(0.0, 5.0)
        self.ec_alert_min_spin.setDecimals(2)
        self.ec_alert_min_spin.setSingleStep(0.1)
        self.ec_alert_min_spin.setValue(0.8)
        ec_layout.addWidget(self.ec_alert_min_spin, 2, 1)
        
        ec_layout.addWidget(QLabel("Alert Maximum:"), 3, 0)
        self.ec_alert_max_spin = QDoubleSpinBox()
        self.ec_alert_max_spin.setRange(0.0, 5.0)
        self.ec_alert_max_spin.setDecimals(2)
        self.ec_alert_max_spin.setSingleStep(0.1)
        self.ec_alert_max_spin.setValue(1.8)
        ec_layout.addWidget(self.ec_alert_max_spin, 3, 1)
        
        ec_group.setLayout(ec_layout)
        target_layout.addWidget(ec_group)
        
        target_tab.setLayout(target_layout)
        
        # Dosing Configuration Tab
        dosing_tab = QWidget()
        dosing_layout = QVBoxLayout()
        
        # Auto Dosing Checkbox
        auto_dosing_box = QHBoxLayout()
        self.auto_dosing_check = QCheckBox("Enable Automatic Dosing")
        self.auto_dosing_check.setChecked(True)
        auto_dosing_box.addWidget(self.auto_dosing_check)
        dosing_layout.addLayout(auto_dosing_box)
        
        # Dosing Limits
        limits_group = QGroupBox("Dosing Limits")
        limits_layout = QGridLayout()
        
        limits_layout.addWidget(QLabel("Minimum Interval Between Doses (seconds):"), 0, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(60, 3600)
        self.interval_spin.setSingleStep(60)
        self.interval_spin.setValue(300)
        limits_layout.addWidget(self.interval_spin, 0, 1)
        
        limits_group.setLayout(limits_layout)
        dosing_layout.addWidget(limits_group)
        
        # Dose Amounts
        amounts_group = QGroupBox("Dose Amounts (mL)")
        amounts_layout = QGridLayout()
        
        amounts_layout.addWidget(QLabel("pH Up Dose:"), 0, 0)
        self.ph_up_dose_spin = QDoubleSpinBox()
        self.ph_up_dose_spin.setRange(0.1, 10.0)
        self.ph_up_dose_spin.setDecimals(1)
        self.ph_up_dose_spin.setSingleStep(0.1)
        self.ph_up_dose_spin.setValue(0.5)
        amounts_layout.addWidget(self.ph_up_dose_spin, 0, 1)
        
        amounts_layout.addWidget(QLabel("pH Down Dose:"), 1, 0)
        self.ph_down_dose_spin = QDoubleSpinBox()
        self.ph_down_dose_spin.setRange(0.1, 10.0)
        self.ph_down_dose_spin.setDecimals(1)
        self.ph_down_dose_spin.setSingleStep(0.1)
        self.ph_down_dose_spin.setValue(0.5)
        amounts_layout.addWidget(self.ph_down_dose_spin, 1, 1)
        
        amounts_layout.addWidget(QLabel("Nutrient A Dose:"), 2, 0)
        self.nutrient_a_dose_spin = QDoubleSpinBox()
        self.nutrient_a_dose_spin.setRange(0.1, 20.0)
        self.nutrient_a_dose_spin.setDecimals(1)
        self.nutrient_a_dose_spin.setSingleStep(0.5)
        self.nutrient_a_dose_spin.setValue(1.0)
        amounts_layout.addWidget(self.nutrient_a_dose_spin, 2, 1)
        
        amounts_layout.addWidget(QLabel("Nutrient B Dose:"), 3, 0)
        self.nutrient_b_dose_spin = QDoubleSpinBox()
        self.nutrient_b_dose_spin.setRange(0.1, 20.0)
        self.nutrient_b_dose_spin.setDecimals(1)
        self.nutrient_b_dose_spin.setSingleStep(0.5)
        self.nutrient_b_dose_spin.setValue(1.0)
        amounts_layout.addWidget(self.nutrient_b_dose_spin, 3, 1)
        
        amounts_group.setLayout(amounts_layout)
        dosing_layout.addWidget(amounts_group)
        
        # Daily Volume Limits
        volume_group = QGroupBox("Maximum Daily Volume (mL)")
        volume_layout = QGridLayout()
        
        volume_layout.addWidget(QLabel("pH Up Daily Limit:"), 0, 0)
        self.ph_up_limit_spin = QDoubleSpinBox()
        self.ph_up_limit_spin.setRange(10.0, 500.0)
        self.ph_up_limit_spin.setDecimals(1)
        self.ph_up_limit_spin.setSingleStep(5.0)
        self.ph_up_limit_spin.setValue(50.0)
        volume_layout.addWidget(self.ph_up_limit_spin, 0, 1)
        
        volume_layout.addWidget(QLabel("pH Down Daily Limit:"), 1, 0)
        self.ph_down_limit_spin = QDoubleSpinBox()
        self.ph_down_limit_spin.setRange(10.0, 500.0)
        self.ph_down_limit_spin.setDecimals(1)
        self.ph_down_limit_spin.setSingleStep(5.0)
        self.ph_down_limit_spin.setValue(50.0)
        volume_layout.addWidget(self.ph_down_limit_spin, 1, 1)
        
        volume_layout.addWidget(QLabel("Nutrient A Daily Limit:"), 2, 0)
        self.nutrient_a_limit_spin = QDoubleSpinBox()
        self.nutrient_a_limit_spin.setRange(10.0, 1000.0)
        self.nutrient_a_limit_spin.setDecimals(1)
        self.nutrient_a_limit_spin.setSingleStep(10.0)
        self.nutrient_a_limit_spin.setValue(100.0)
        volume_layout.addWidget(self.nutrient_a_limit_spin, 2, 1)
        
        volume_layout.addWidget(QLabel("Nutrient B Daily Limit:"), 3, 0)
        self.nutrient_b_limit_spin = QDoubleSpinBox()
        self.nutrient_b_limit_spin.setRange(10.0, 1000.0)
        self.nutrient_b_limit_spin.setDecimals(1)
        self.nutrient_b_limit_spin.setSingleStep(10.0)
        self.nutrient_b_limit_spin.setValue(100.0)
        volume_layout.addWidget(self.nutrient_b_limit_spin, 3, 1)
        
        volume_group.setLayout(volume_layout)
        dosing_layout.addWidget(volume_group)
        
        dosing_tab.setLayout(dosing_layout)
        
        # Add tabs to tab widget
        tabs.addTab(target_tab, "Target Ranges")
        tabs.addTab(dosing_tab, "Dosing Configuration")
        
        main_layout.addWidget(tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        
        main_layout.addLayout(button_layout)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Load current values
        self.load_settings()
    
    def load_settings(self):
        """Load settings from configuration"""
        try:
            # pH Target Ranges
            self.ph_min_spin.setValue(self.system.config.get('sensors', 'ph.target_min', 5.8))
            self.ph_max_spin.setValue(self.system.config.get('sensors', 'ph.target_max', 6.2))
            self.ph_alert_min_spin.setValue(self.system.config.get('sensors', 'ph.alert_min', 5.5))
            self.ph_alert_max_spin.setValue(self.system.config.get('sensors', 'ph.alert_max', 6.5))
            
            # EC Target Ranges
            self.ec_min_spin.setValue(self.system.config.get('sensors', 'ec.target_min', 1.0))
            self.ec_max_spin.setValue(self.system.config.get('sensors', 'ec.target_max', 1.6))
            self.ec_alert_min_spin.setValue(self.system.config.get('sensors', 'ec.alert_min', 0.8))
            self.ec_alert_max_spin.setValue(self.system.config.get('sensors', 'ec.alert_max', 1.8))
            
            # Auto Dosing
            self.auto_dosing_check.setChecked(self.system.config.get('dosing', 'settings.auto_dosing_enabled', True))
            
            # Dosing Interval
            self.interval_spin.setValue(self.system.config.get('dosing', 'settings.min_dose_interval', 300))
            
            # Dose Amounts
            self.ph_up_dose_spin.setValue(self.system.config.get('dosing', 'settings.dose_amounts.ph_up', 0.5))
            self.ph_down_dose_spin.setValue(self.system.config.get('dosing', 'settings.dose_amounts.ph_down', 0.5))
            self.nutrient_a_dose_spin.setValue(self.system.config.get('dosing', 'settings.dose_amounts.nutrient_a', 1.0))
            self.nutrient_b_dose_spin.setValue(self.system.config.get('dosing', 'settings.dose_amounts.nutrient_b', 1.0))
            
            # Daily Volume Limits
            self.ph_up_limit_spin.setValue(self.system.config.get('dosing', 'settings.max_daily_volume.ph_up', 50.0))
            self.ph_down_limit_spin.setValue(self.system.config.get('dosing', 'settings.max_daily_volume.ph_down', 50.0))
            self.nutrient_a_limit_spin.setValue(self.system.config.get('dosing', 'settings.max_daily_volume.nutrient_a', 100.0))
            self.nutrient_b_limit_spin.setValue(self.system.config.get('dosing', 'settings.max_daily_volume.nutrient_b', 100.0))
            
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self.show_message("Error", f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to configuration"""
        try:
            # pH Target Ranges
            self.system.config.set('sensors', 'ph.target_min', self.ph_min_spin.value())
            self.system.config.set('sensors', 'ph.target_max', self.ph_max_spin.value())
            self.system.config.set('sensors', 'ph.alert_min', self.ph_alert_min_spin.value())
            self.system.config.set('sensors', 'ph.alert_max', self.ph_alert_max_spin.value())
            
            # EC Target Ranges
            self.system.config.set('sensors', 'ec.target_min', self.ec_min_spin.value())
            self.system.config.set('sensors', 'ec.target_max', self.ec_max_spin.value())
            self.system.config.set('sensors', 'ec.alert_min', self.ec_alert_min_spin.value())
            self.system.config.set('sensors', 'ec.alert_max', self.ec_alert_max_spin.value())
            
            # Auto Dosing
            self.system.config.set('dosing', 'settings.auto_dosing_enabled', self.auto_dosing_check.isChecked())
            
            # Dosing Interval
            self.system.config.set('dosing', 'settings.min_dose_interval', self.interval_spin.value())
            
            # Dose Amounts
            self.system.config.set('dosing', 'settings.dose_amounts.ph_up', self.ph_up_dose_spin.value())
            self.system.config.set('dosing', 'settings.dose_amounts.ph_down', self.ph_down_dose_spin.value())
            self.system.config.set('dosing', 'settings.dose_amounts.nutrient_a', self.nutrient_a_dose_spin.value())
            self.system.config.set('dosing', 'settings.dose_amounts.nutrient_b', self.nutrient_b_dose_spin.value())
            
            # Daily Volume Limits
            self.system.config.set('dosing', 'settings.max_daily_volume.ph_up', self.ph_up_limit_spin.value())
            self.system.config.set('dosing', 'settings.max_daily_volume.ph_down', self.ph_down_limit_spin.value())
            self.system.config.set('dosing', 'settings.max_daily_volume.nutrient_a', self.nutrient_a_limit_spin.value())
            self.system.config.set('dosing', 'settings.max_daily_volume.nutrient_b', self.nutrient_b_limit_spin.value())
            
            self.show_message("Success", "Settings saved successfully!")
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            self.show_message("Error", f"Failed to save settings: {e}")
    
    def reset_to_defaults(self):
        """Reset settings to default values"""
        try:
            # pH Target Ranges
            self.ph_min_spin.setValue(5.8)
            self.ph_max_spin.setValue(6.2)
            self.ph_alert_min_spin.setValue(5.5)
            self.ph_alert_max_spin.setValue(6.5)
            
            # EC Target Ranges
            self.ec_min_spin.setValue(1.0)
            self.ec_max_spin.setValue(1.6)
            self.ec_alert_min_spin.setValue(0.8)
            self.ec_alert_max_spin.setValue(1.8)
            
            # Auto Dosing
            self.auto_dosing_check.setChecked(True)
            
            # Dosing Interval
            self.interval_spin.setValue(300)
            
            # Dose Amounts
            self.ph_up_dose_spin.setValue(0.5)
            self.ph_down_dose_spin.setValue(0.5)
            self.nutrient_a_dose_spin.setValue(1.0)
            self.nutrient_b_dose_spin.setValue(1.0)
            
            # Daily Volume Limits
            self.ph_up_limit_spin.setValue(50.0)
            self.ph_down_limit_spin.setValue(50.0)
            self.nutrient_a_limit_spin.setValue(100.0)
            self.nutrient_b_limit_spin.setValue(100.0)
            
        except Exception as e:
            self.logger.error(f"Error resetting settings: {e}")
            self.show_message("Error", f"Failed to reset settings: {e}")
    
    def update_ui(self):
        """Update UI with latest data"""
        # No live updates needed for this screen
        pass
    
    def show_message(self, title, message):
        """Show a message box to the user"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_() 