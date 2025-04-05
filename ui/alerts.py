#!/usr/bin/env python3
# NuTetra Alerts Screen
# Configure notification settings and alerts

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGridLayout, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class AlertsScreen(QWidget):
    def __init__(self, system):
        super().__init__()
        self.logger = logging.getLogger("NuTetra.UI.Alerts")
        self.logger.info("Initializing Alerts Screen")
        
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
        title_label = QLabel("Alerts Configuration")
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Placeholder text
        placeholder = QLabel("Alerts Configuration Screen - Coming Soon")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setFont(QFont('Arial', 14))
        main_layout.addWidget(placeholder)
        
        self.setLayout(main_layout)
    
    def update_ui(self):
        """Update UI with latest data"""
        # No live updates needed for this placeholder
        pass
    
    def show_message(self, title, message):
        """Show a message box to the user"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_() 