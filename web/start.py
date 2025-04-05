#!/usr/bin/env python3
"""
nutetra Hydroponic System - Web Interface Launcher
Script to start the web interface and configure it to run on boot.
"""
import os
import sys
import subprocess
import argparse
import logging
import time

# Make sure we can import from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nutetra_launcher")

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import flask
        import flask_socketio
        logger.info("All required dependencies are installed.")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Installing required dependencies...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-socketio", "eventlet"])
            logger.info("Dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False

def start_web_server(host='0.0.0.0', port=5000, debug=False, no_setup=False):
    """Start the Flask web server."""
    try:
        # Change to the directory containing app.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        if debug:
            os.environ['FLASK_ENV'] = 'development'
            os.environ['FLASK_DEBUG'] = '1'
        
        # Import directly from main.py in the same directory
        try:
            # Import from main.py in the web directory (new approach)
            # Note: We no longer try to import from parent_dir/main.py
            from main import app, socketio, nutetra
            logger.info("Successfully imported Flask app from web/main.py")
            
            # Initialize the NuTetra system if not in no-setup mode
            if not no_setup:
                logger.info("Initializing NuTetra system from main.py")
                nutetra.start()
                
        except ImportError as e:
            logger.error(f"Could not import from web/main.py: {e}")
            logger.error("Please ensure main.py is in the web directory")
            return False
        
        # Start the web server
        logger.info(f"Starting web server on {host}:{port}...")
        socketio.run(app, host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        return False
    
    return True

def setup_autostart(chromium_kiosk=False):
    """Configure the application to start on boot."""
    try:
        # Get absolute path to this script
        script_path = os.path.abspath(__file__)
        python_path = sys.executable
        
        # Directory for the service file
        systemd_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(systemd_dir, exist_ok=True)
        
        # Create systemd service file for nutetra web app
        service_file = os.path.join(systemd_dir, "nutetra-web.service")
        with open(service_file, "w") as f:
            f.write(f"""[Unit]
Description=nutetra Hydroponic System Web Interface
After=network.target

[Service]
ExecStart={python_path} {script_path} --no-setup
WorkingDirectory={os.path.dirname(script_path)}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
""")
        
        # If chromium kiosk mode is requested, create a service for it
        if chromium_kiosk:
            chromium_service = os.path.join(systemd_dir, "nutetra-chromium.service")
            with open(chromium_service, "w") as f:
                f.write("""[Unit]
Description=nutetra Chromium Kiosk
After=nutetra-web.service
Requires=nutetra-web.service

[Service]
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium-browser --kiosk --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/dev/null http://localhost:5000
Restart=always
RestartSec=5
User=pi
Group=pi

[Install]
WantedBy=graphical.target
""")
        
            # Enable Chromium service
            subprocess.run(["systemctl", "--user", "enable", "nutetra-chromium.service"])
            logger.info("Chromium kiosk mode service has been configured to start on boot.")
        
        # Enable nutetra web service
        subprocess.run(["systemctl", "--user", "enable", "nutetra-web.service"])
        logger.info("nutetra web service has been configured to start on boot.")
        
        return True
            
    except Exception as e:
        logger.error(f"Failed to setup autostart: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="nutetra Hydroponic System Web Interface Launcher")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the web server to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--setup", action="store_true", help="Configure to run on boot")
    parser.add_argument("--no-setup", action="store_true", help="Skip setup, just run the server")
    parser.add_argument("--chromium-kiosk", action="store_true", help="Configure Chromium to start in kiosk mode on boot")
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup autostart if requested
    if args.setup:
        if not setup_autostart(args.chromium_kiosk):
            sys.exit(1)
    
    # Start the web server
    start_web_server(args.host, args.port, args.debug, args.no_setup) 