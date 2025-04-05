#!/usr/bin/env python3
# NuTetra UI Application
# Main UI application for the touchscreen interface

import os
import sys
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                           QWidget, QVBoxLayout, QLabel, QStyleFactory)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor

# Import UI screens
from ui.dashboard import DashboardScreen
from ui.dosing_settings import DosingSettingsScreen
from ui.pump_control import PumpControlScreen
from ui.alerts import AlertsScreen
from ui.logs import LogsScreen
from ui.system_settings import SystemSettingsScreen

class NuTetraApp:
    def __init__(self, system):
        self.logger = logging.getLogger("NuTetra.UI")
        self.logger.info("Initializing NuTetra UI Application")
        
        self.system = system
        
        # Create the Qt application
        self.app = QApplication(sys.argv)
        self.app.setStyle(QStyleFactory.create('Fusion'))  # Modern style
        
        # Apply dark theme
        self._apply_dark_theme()
        
        # Create the main window
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("NuTetra Hydroponic System")
        
        # Set window to fullscreen for Raspberry Pi touchscreen
        self.main_window.setWindowFlags(Qt.FramelessWindowHint)
        self.main_window.showFullScreen()
        
        # Create the tab widget for navigation
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)  # Tabs at the bottom for better touch access
        self.tabs.setIconSize(Qt.QSize(36, 36))  # Larger icons for tabs
        
        # Create the screen instances
        self.screens = {
            'dashboard': DashboardScreen(self.system),
            'dosing_settings': DosingSettingsScreen(self.system),
            'pump_control': PumpControlScreen(self.system),
            'alerts': AlertsScreen(self.system),
            'logs': LogsScreen(self.system),
            'system_settings': SystemSettingsScreen(self.system)
        }
        
        # Add screens to tabs
        self.tabs.addTab(self.screens['dashboard'], "Dashboard")
        self.tabs.addTab(self.screens['dosing_settings'], "Dosing Settings")
        self.tabs.addTab(self.screens['pump_control'], "Pump Control")
        self.tabs.addTab(self.screens['alerts'], "Alerts")
        self.tabs.addTab(self.screens['logs'], "Logs")
        self.tabs.addTab(self.screens['system_settings'], "System")
        
        # Set up the main window layout
        self.main_window.setCentralWidget(self.tabs)
        
        # Set up update timer (every 1 second)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(1000)  # 1 second interval
        
        self.logger.info("UI Application initialized")
    
    def _apply_dark_theme(self):
        """Apply the dark theme styling to the application"""
        # Dark color scheme based on AC Infinity products
        dark_palette = self.app.palette()
        
        # Set color scheme
        dark_palette.setColor(dark_palette.Window, QColor(25, 25, 25))
        dark_palette.setColor(dark_palette.WindowText, QColor(240, 240, 240))
        dark_palette.setColor(dark_palette.Base, QColor(40, 40, 40))
        dark_palette.setColor(dark_palette.AlternateBase, QColor(35, 35, 35))
        dark_palette.setColor(dark_palette.ToolTipBase, QColor(240, 240, 240))
        dark_palette.setColor(dark_palette.ToolTipText, QColor(240, 240, 240))
        dark_palette.setColor(dark_palette.Text, QColor(240, 240, 240))
        dark_palette.setColor(dark_palette.Button, QColor(45, 45, 45))
        dark_palette.setColor(dark_palette.ButtonText, QColor(240, 240, 240))
        dark_palette.setColor(dark_palette.BrightText, Qt.red)
        dark_palette.setColor(dark_palette.Link, QColor(42, 130, 218))
        dark_palette.setColor(dark_palette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(dark_palette.HighlightedText, Qt.black)
        
        # Apply the palette
        self.app.setPalette(dark_palette)
        
        # Set stylesheet for additional customization
        self.app.setStyleSheet("""
            QTabWidget::pane { 
                border: 0; 
                background: #191919;
            }
            QTabBar::tab {
                background: #282828;
                color: #e0e0e0;
                padding: 15px 30px;
                border: 1px solid #444;
                border-bottom: none;
                font-size: 16px;
            }
            QTabBar::tab:selected {
                background: #2a82da;
                color: #ffffff;
                border: 1px solid #2a82da;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                padding: 12px 25px;
                font-weight: bold;
                border-radius: 3px;
                min-height: 40px;
                min-width: 100px;
            }
            QPushButton:pressed {
                background-color: #1a6eb0;
            }
            QPushButton:disabled {
                background-color: #505050;
                color: #a0a0a0;
            }
            QLabel {
                font-size: 16px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #333;
                color: white;
                border: 1px solid #444;
                padding: 8px;
                border-radius: 3px;
                min-height: 30px;
            }
        """)
    
    def _update_ui(self):
        """Update UI components with latest data"""
        # Update the active screen
        current_index = self.tabs.currentIndex()
        current_screen = self.tabs.widget(current_index)
        if hasattr(current_screen, 'update_ui'):
            current_screen.update_ui()
    
    def run(self):
        """Run the application main loop"""
        self.logger.info("Starting UI Application")
        self.main_window.show()
        return self.app.exec_()
    
    def show_message(self, title, message):
        """Show a message to the user"""
        # Call this from any component to show messages to the user
        self.screens['dashboard'].show_message(title, message) 