#!/usr/bin/env python3
# NuTetra System Settings Screen
# Configure system-wide settings and perform maintenance

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGridLayout, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class SystemSettingsScreen(QWidget):
    def __init__(self, system):
        super().__init__()
        self.logger = logging.getLogger("NuTetra.UI.SystemSettings")
        self.logger.info("Initializing System Settings Screen")
        
        self.system = system
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("System Settings")
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Placeholder text
        placeholder = QLabel("System Settings Screen - Coming Soon")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setFont(QFont('Arial', 14))
        main_layout.addWidget(placeholder)
        
        # Exit button
        exit_button = QPushButton("Exit NuTetra")
        exit_button.clicked.connect(self.confirm_exit)
        main_layout.addWidget(exit_button)
        
        self.setLayout(main_layout)
    
    def update_ui(self):
        """Update UI with latest data"""
        # No live updates needed for this placeholder
        pass
    
    def confirm_exit(self):
        """Confirm and exit the application"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Exit")
        msg_box.setText("Are you sure you want to exit NuTetra?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        if msg_box.exec_() == QMessageBox.Yes:
            self.logger.info("User requested application exit")
            self.system.cleanup()  # Clean up resources
            import sys
            sys.exit(0)
    
    def show_message(self, title, message):
        """Show a message box to the user"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_() 