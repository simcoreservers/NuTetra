#!/usr/bin/env python3
# NuTetra Data Logger
# Records sensor readings and dosing events

import os
import csv
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

class DataLogger:
    def __init__(self, data_dir="/NuTetra/data/history"):
        self.logger = logging.getLogger("NuTetra.DataLogger")
        self.logger.info("Initializing Data Logger")
        
        self.data_dir = data_dir
        self.ensure_data_directory()
        
        self.current_day = None
        self.sensor_file = None
        self.dosing_file = None
        self.csv_writers = {}
        
        # Initialize files for the current day
        self._init_daily_files()
        
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Ensured data directory exists: {self.data_dir}")
        
    def _init_daily_files(self):
        """Initialize the log files for the current day"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.current_day != today:
            # Close existing files if open
            self._close_files()
            
            self.current_day = today
            
            # Sensor readings file
            sensor_path = os.path.join(self.data_dir, f"sensor_{today}.csv")
            is_new_file = not os.path.exists(sensor_path)
            
            self.sensor_file = open(sensor_path, 'a', newline='')
            self.csv_writers['sensor'] = csv.writer(self.sensor_file)
            
            # Write header if new file
            if is_new_file:
                self.csv_writers['sensor'].writerow([
                    'timestamp', 'ph', 'ec', 'temperature'
                ])
                
            # Dosing events file
            dosing_path = os.path.join(self.data_dir, f"dosing_{today}.csv")
            is_new_file = not os.path.exists(dosing_path)
            
            self.dosing_file = open(dosing_path, 'a', newline='')
            self.csv_writers['dosing'] = csv.writer(self.dosing_file)
            
            # Write header if new file
            if is_new_file:
                self.csv_writers['dosing'].writerow([
                    'timestamp', 'pump_id', 'pump_name', 'volume_ml', 'reason'
                ])
                
            self.logger.info(f"Initialized log files for {today}")
    
    def _close_files(self):
        """Close any open log files"""
        if self.sensor_file:
            self.sensor_file.close()
            self.sensor_file = None
            
        if self.dosing_file:
            self.dosing_file.close()
            self.dosing_file = None
    
    def log_sensor_readings(self, readings):
        """
        Log sensor readings to CSV
        readings: dict with keys 'ph', 'ec', 'temperature'
        """
        try:
            # Ensure we have the right files for today
            self._init_daily_files()
            
            # Get current timestamp
            timestamp = datetime.now().isoformat()
            
            # Write to CSV
            self.csv_writers['sensor'].writerow([
                timestamp, 
                readings.get('ph', ''), 
                readings.get('ec', ''),
                readings.get('temperature', '')
            ])
            
            # Flush to disk
            self.sensor_file.flush()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging sensor readings: {e}")
            return False
    
    def log_dosing_event(self, pump_id, pump_name, volume_ml, reason="manual"):
        """
        Log a dosing event to CSV
        """
        try:
            # Ensure we have the right files for today
            self._init_daily_files()
            
            # Get current timestamp
            timestamp = datetime.now().isoformat()
            
            # Write to CSV
            self.csv_writers['dosing'].writerow([
                timestamp, pump_id, pump_name, volume_ml, reason
            ])
            
            # Flush to disk
            self.dosing_file.flush()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging dosing event: {e}")
            return False
    
    def get_sensor_history(self, days=1, start_date=None, end_date=None):
        """
        Get sensor reading history for the specified period
        days: Number of days to retrieve (default: 1)
        start_date, end_date: Optional date range (format: YYYY-MM-DD)
        """
        try:
            data = []
            
            if start_date and end_date:
                # Use specified date range
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                date_range = []
                
                current = start
                while current <= end:
                    date_range.append(current.strftime("%Y-%m-%d"))
                    current += timedelta(days=1)
            else:
                # Use relative days count
                date_range = []
                for day_offset in range(days):
                    date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                    date_range.append(date)
            
            # Read data for each date
            for date in date_range:
                file_path = os.path.join(self.data_dir, f"sensor_{date}.csv")
                
                if os.path.exists(file_path):
                    with open(file_path, 'r', newline='') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            data.append(row)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error retrieving sensor history: {e}")
            return []
    
    def get_dosing_history(self, days=1, start_date=None, end_date=None):
        """
        Get dosing event history for the specified period
        days: Number of days to retrieve (default: 1)
        start_date, end_date: Optional date range (format: YYYY-MM-DD)
        """
        try:
            data = []
            
            if start_date and end_date:
                # Use specified date range
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                date_range = []
                
                current = start
                while current <= end:
                    date_range.append(current.strftime("%Y-%m-%d"))
                    current += timedelta(days=1)
            else:
                # Use relative days count
                date_range = []
                for day_offset in range(days):
                    date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                    date_range.append(date)
            
            # Read data for each date
            for date in date_range:
                file_path = os.path.join(self.data_dir, f"dosing_{date}.csv")
                
                if os.path.exists(file_path):
                    with open(file_path, 'r', newline='') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            data.append(row)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error retrieving dosing history: {e}")
            return []
    
    def export_data(self, export_dir, start_date=None, end_date=None, format='csv'):
        """
        Export data to CSV or JSON files
        export_dir: Directory to export files to
        start_date, end_date: Date range (format: YYYY-MM-DD)
        format: 'csv' or 'json'
        """
        try:
            # Ensure export directory exists
            Path(export_dir).mkdir(parents=True, exist_ok=True)
            
            # Determine date range
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
                
            # Get data for the date range
            sensor_data = self.get_sensor_history(start_date=start_date, end_date=end_date)
            dosing_data = self.get_dosing_history(start_date=start_date, end_date=end_date)
            
            # Export based on format
            if format.lower() == 'json':
                # Export to JSON
                with open(os.path.join(export_dir, 'sensor_data.json'), 'w') as f:
                    json.dump(sensor_data, f, indent=2)
                
                with open(os.path.join(export_dir, 'dosing_data.json'), 'w') as f:
                    json.dump(dosing_data, f, indent=2)
                    
            else:
                # Export to CSV (default)
                if sensor_data:
                    with open(os.path.join(export_dir, 'sensor_data.csv'), 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=sensor_data[0].keys())
                        writer.writeheader()
                        writer.writerows(sensor_data)
                
                if dosing_data:
                    with open(os.path.join(export_dir, 'dosing_data.csv'), 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=dosing_data[0].keys())
                        writer.writeheader()
                        writer.writerows(dosing_data)
            
            self.logger.info(f"Data exported to {export_dir} in {format} format")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return False
    
    def cleanup_old_logs(self, days_to_keep=90):
        """Remove log files older than the specified number of days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Get all log files
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.csv'):
                    # Extract date from filename (format: sensor_YYYY-MM-DD.csv or dosing_YYYY-MM-DD.csv)
                    parts = filename.split('_')
                    if len(parts) == 2:
                        date_str = parts[1].replace('.csv', '')
                        try:
                            file_date = datetime.strptime(date_str, "%Y-%m-%d")
                            
                            # Check if file is older than cutoff
                            if file_date < cutoff_date:
                                file_path = os.path.join(self.data_dir, filename)
                                os.remove(file_path)
                                self.logger.info(f"Removed old log file: {filename}")
                        except:
                            # Skip files with invalid date format
                            pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {e}")
            return False
    
    def close(self):
        """Close the data logger"""
        self._close_files()
        self.logger.info("Data logger closed") 