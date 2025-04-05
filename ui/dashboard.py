# Dashboard screen UI logic
#!/usr/bin/env python3
# NuTetra Dashboard Screen
# Displays real-time sensor readings and system status

import logging
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

class DashboardScreen(QWidget):
    def __init__(self, system):
        super().__init__()
        self.logger = logging.getLogger("NuTetra.UI.Dashboard")
        self.logger.info("Initializing Dashboard Screen")
        
        self.system = system
        
        # Set up the UI components
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section with system name and time
        header_layout = QHBoxLayout()
        
        self.system_name_label = QLabel("NuTetra Hydroponic System")
        self.system_name_label.setFont(QFont('Arial', 20, QFont.Bold))
        
        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time_label.setFont(QFont('Arial', 16))
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(self.system_name_label)
        header_layout.addWidget(self.time_label)
        
        # Sensor readings section
        sensor_frame = QFrame()
        sensor_frame.setFrameShape(QFrame.StyledPanel)
        sensor_frame.setStyleSheet("background-color: #252525; border-radius: 5px;")
        
        sensor_layout = QGridLayout()
        sensor_layout.setContentsMargins(20, 20, 20, 20)
        sensor_layout.setSpacing(15)
        
        # pH Section
        ph_label = QLabel("pH")
        ph_label.setFont(QFont('Arial', 16, QFont.Bold))
        
        self.ph_value_label = QLabel("7.0")
        self.ph_value_label.setFont(QFont('Arial', 30, QFont.Bold))
        self.ph_value_label.setStyleSheet("color: #2a82da;")
        
        self.ph_status_label = QLabel("NORMAL")
        self.ph_status_label.setFont(QFont('Arial', 12))
        self.ph_status_label.setStyleSheet("color: #22bb33;")
        
        # EC Section
        ec_label = QLabel("EC (mS/cm)")
        ec_label.setFont(QFont('Arial', 16, QFont.Bold))
        
        self.ec_value_label = QLabel("1.2")
        self.ec_value_label.setFont(QFont('Arial', 30, QFont.Bold))
        self.ec_value_label.setStyleSheet("color: #2a82da;")
        
        self.ec_status_label = QLabel("NORMAL")
        self.ec_status_label.setFont(QFont('Arial', 12))
        self.ec_status_label.setStyleSheet("color: #22bb33;")
        
        # Temperature Section
        temp_label = QLabel("Temperature (°C)")
        temp_label.setFont(QFont('Arial', 16, QFont.Bold))
        
        self.temp_value_label = QLabel("21.5")
        self.temp_value_label.setFont(QFont('Arial', 30, QFont.Bold))
        self.temp_value_label.setStyleSheet("color: #2a82da;")
        
        self.temp_status_label = QLabel("NORMAL")
        self.temp_status_label.setFont(QFont('Arial', 12))
        self.temp_status_label.setStyleSheet("color: #22bb33;")
        
        # Add elements to sensor grid
        sensor_layout.addWidget(ph_label, 0, 0)
        sensor_layout.addWidget(self.ph_value_label, 1, 0)
        sensor_layout.addWidget(self.ph_status_label, 2, 0)
        
        sensor_layout.addWidget(ec_label, 0, 1)
        sensor_layout.addWidget(self.ec_value_label, 1, 1)
        sensor_layout.addWidget(self.ec_status_label, 2, 1)
        
        sensor_layout.addWidget(temp_label, 0, 2)
        sensor_layout.addWidget(self.temp_value_label, 1, 2)
        sensor_layout.addWidget(self.temp_status_label, 2, 2)
        
        sensor_frame.setLayout(sensor_layout)
        
        # Dosing status section
        dosing_frame = QFrame()
        dosing_frame.setFrameShape(QFrame.StyledPanel)
        dosing_frame.setStyleSheet("background-color: #252525; border-radius: 5px;")
        
        dosing_layout = QVBoxLayout()
        dosing_layout.setContentsMargins(20, 20, 20, 20)
        
        dosing_header = QLabel("Dosing Status")
        dosing_header.setFont(QFont('Arial', 16, QFont.Bold))
        
        self.auto_dosing_label = QLabel("Auto Dosing: ENABLED")
        self.auto_dosing_label.setFont(QFont('Arial', 14))
        
        # Last dosing events
        self.last_dose_layout = QVBoxLayout()
        
        # Sample dosing events (will be replaced with real data)
        self.last_dose_labels = []
        for i in range(3):
            label = QLabel("No dosing events recorded")
            label.setFont(QFont('Arial', 12))
            self.last_dose_labels.append(label)
            self.last_dose_layout.addWidget(label)
        
        dosing_layout.addWidget(dosing_header)
        dosing_layout.addWidget(self.auto_dosing_label)
        dosing_layout.addLayout(self.last_dose_layout)
        
        dosing_frame.setLayout(dosing_layout)
        
        # Action buttons section
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_ui)
        
        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self.show_calibration)
        
        self.dose_now_button = QPushButton("Dose Now")
        self.dose_now_button.clicked.connect(self.show_manual_dosing)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.calibrate_button)
        button_layout.addWidget(self.dose_now_button)
        
        # Add all sections to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(sensor_frame, 3)  # Give sensor frame more space
        main_layout.addWidget(dosing_frame, 2)
        main_layout.addLayout(button_layout)
        
        # Set the main layout for the widget
        self.setLayout(main_layout)
        
        # Initial UI update
        self.update_ui()
    
    def update_ui(self):
        """Update UI with latest data"""
        try:
            # Update time
            self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
            
            # Get latest sensor readings
            readings = self.system.sensors.get_readings()
            
            # Update pH display
            ph_value = readings.get('ph', 0.0)
            self.ph_value_label.setText(f"{ph_value:.2f}")
            
            # Get target ranges from config
            ph_min = self.system.config.get('sensors', 'ph.target_min', 5.8)
            ph_max = self.system.config.get('sensors', 'ph.target_max', 6.2)
            
            # Update pH status
            if ph_min <= ph_value <= ph_max:
                self.ph_status_label.setText("NORMAL")
                self.ph_status_label.setStyleSheet("color: #22bb33;")
            elif ph_value < ph_min:
                self.ph_status_label.setText("LOW")
                self.ph_status_label.setStyleSheet("color: #ffcc00;")
            else:
                self.ph_status_label.setText("HIGH")
                self.ph_status_label.setStyleSheet("color: #ffcc00;")
            
            # Update EC display
            ec_value = readings.get('ec', 0.0)
            self.ec_value_label.setText(f"{ec_value:.2f}")
            
            # Get target ranges from config
            ec_min = self.system.config.get('sensors', 'ec.target_min', 1.0)
            ec_max = self.system.config.get('sensors', 'ec.target_max', 1.6)
            
            # Update EC status
            if ec_min <= ec_value <= ec_max:
                self.ec_status_label.setText("NORMAL")
                self.ec_status_label.setStyleSheet("color: #22bb33;")
            elif ec_value < ec_min:
                self.ec_status_label.setText("LOW")
                self.ec_status_label.setStyleSheet("color: #ffcc00;")
            else:
                self.ec_status_label.setText("HIGH")
                self.ec_status_label.setStyleSheet("color: #ffcc00;")
            
            # Update temperature display
            temp_value = readings.get('temperature', 0.0)
            self.temp_value_label.setText(f"{temp_value:.1f}")
            
            # Get target ranges from config
            temp_min = self.system.config.get('sensors', 'temperature.target_min', 18.0)
            temp_max = self.system.config.get('sensors', 'temperature.target_max', 22.0)
            
            # Update temperature status
            if temp_min <= temp_value <= temp_max:
                self.temp_status_label.setText("NORMAL")
                self.temp_status_label.setStyleSheet("color: #22bb33;")
            elif temp_value < temp_min:
                self.temp_status_label.setText("LOW")
                self.temp_status_label.setStyleSheet("color: #ffcc00;")
            else:
                self.temp_status_label.setText("HIGH")
                self.temp_status_label.setStyleSheet("color: #ffcc00;")
            
            # Update auto dosing status
            auto_dosing = self.system.config.get('dosing', 'settings.auto_dosing_enabled', True)
            auto_status = "ENABLED" if auto_dosing else "DISABLED"
            self.auto_dosing_label.setText(f"Auto Dosing: {auto_status}")
            
            # TODO: Update last dosing events from history
            # For now, just show placeholders
            for i, label in enumerate(self.last_dose_labels):
                label.setText(f"No recent dosing events")
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")
    
    def show_calibration(self):
        """Show sensor calibration dialog"""
        self.logger.info("Showing calibration dialog")
        # TODO: Implement calibration dialog
        self.show_message("Calibration", "Sensor calibration not yet implemented")
    
    def show_manual_dosing(self):
        """Show manual dosing dialog"""
        self.logger.info("Showing manual dosing dialog")
        # TODO: Implement manual dosing dialog
        self.show_message("Manual Dosing", "Manual dosing not yet implemented")
    
    def show_message(self, title, message):
        """Show a message box to the user"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()