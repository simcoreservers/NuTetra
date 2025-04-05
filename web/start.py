#!/usr/bin/env python3
"""
NuTetra Hydroponic System - Web Application Starter
Entry point for starting the NuTetra web application
"""
import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Configure logging
def setup_logging():
    """Set up logging configuration"""
    log_dir = Path("/NuTetra/logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except:
        # Fallback to current directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "nutetra.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers if they don't exist already
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Create logger for this module
    logger = logging.getLogger('NuTetra.Start')
    return logger

# Parse command line arguments
def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='NuTetra Hydroponic System')
    parser.add_argument('--no-setup', action='store_true', help='Skip system initialization')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', type=str, help='Path to config file')
    return parser.parse_args()

# Ensure required directories exist
def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        "/NuTetra/logs",
        "/NuTetra/data",
        "/NuTetra/config",
        "/NuTetra/exports"
    ]
    
    for directory in dirs:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create directory {directory}: {e}")
            # Create local fallback directories
            local_dir = Path(directory.lstrip('/'))
            local_dir.mkdir(parents=True, exist_ok=True)

# Main function
def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting NuTetra Web Application")
    
    # Ensure directories exist
    ensure_directories()
    
    # Add project root to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    try:
        # Import Flask application from main.py
        from web.main import app, socketio, initialize_system
        
        # Initialize the system if not skipped
        if not args.no_setup:
            logger.info("Initializing NuTetra system...")
            success = initialize_system(args.config)
            if not success:
                logger.error("Failed to initialize system, continuing without it")
        else:
            logger.info("Skipping system initialization (--no-setup flag)")
        
        # Run the Flask application
        logger.info(f"Starting Flask application on {args.host}:{args.port}")
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False
        )
    except Exception as e:
        logger.critical(f"Error starting application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 