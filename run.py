#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Main Runner
Simple script to run the NuTetra web application directly.
"""
import os
import sys
import subprocess
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nutetra")

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        logger.error("Python 3.7 or higher is required")
        return False
    return True

def run_nutetra(host='0.0.0.0', port=5000, debug=False):
    """Run the NuTetra web application."""
    try:
        # Try to import Flask to check if dependencies are installed
        import flask
        
        # Change to the web directory
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
        os.chdir(web_dir)
        
        # Run the application
        from web.app import socketio, app
        
        logger.info(f"Starting NuTetra on http://{host}:{port}")
        socketio.run(app, host=host, port=port, debug=debug)
        
    except ImportError:
        logger.error("Required dependencies are not installed.")
        logger.info("Please install the required dependencies using:")
        logger.info("pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"Error starting NuTetra: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NuTetra Hydroponic System")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the web server to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    if not check_python_version():
        sys.exit(1)
    
    if not run_nutetra(args.host, args.port, args.debug):
        sys.exit(1)

if __name__ == "__main__":
    main() 