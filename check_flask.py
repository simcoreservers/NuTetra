#!/usr/bin/env python3
# Script to check Flask app details and API routes

import os
import sys
import json
import glob
import subprocess
from pathlib import Path

def find_flask_app_files():
    """Find all potential Flask app files"""
    result = []
    
    # Look for main.py files
    for path in glob.glob("/home/pi/**/main.py", recursive=True):
        result.append(path)
    
    # Look for app.py files
    for path in glob.glob("/home/pi/**/app.py", recursive=True):
        result.append(path)
        
    # Look for other Python files that might be Flask apps
    for path in glob.glob("/home/pi/**/*.py", recursive=True):
        with open(path, 'r') as f:
            content = f.read()
            if 'from flask import' in content and 'app = Flask' in content:
                if path not in result:
                    result.append(path)
    
    return result

def check_running_processes():
    """Check what Python processes are running"""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    python_processes = []
    
    for line in result.stdout.split('\n'):
        if 'python' in line:
            python_processes.append(line)
    
    return python_processes

def check_service_status():
    """Check if any NuTetra services are running"""
    result = subprocess.run(['systemctl', 'list-units', '--type=service', '--all'], 
                           capture_output=True, text=True)
    
    services = []
    for line in result.stdout.split('\n'):
        if 'nutetra' in line.lower():
            services.append(line)
    
    return services

def check_api_endpoint(endpoint):
    """Try to access an API endpoint locally"""
    result = subprocess.run(['curl', '-s', f'http://localhost:5000{endpoint}'], 
                           capture_output=True, text=True)
    return result.stdout

# Check Flask apps and save results
output = {
    'flask_app_files': find_flask_app_files(),
    'python_processes': check_running_processes(),
    'services': check_service_status(),
    'api_test': {
        '/': check_api_endpoint('/'),
        '/api/sensor-readings': check_api_endpoint('/api/sensor-readings'),
        '/api/system/info': check_api_endpoint('/api/system/info')
    }
}

# Write results to file
with open('/home/pi/flask_check_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Flask app check complete. Results written to /home/pi/flask_check_results.json") 