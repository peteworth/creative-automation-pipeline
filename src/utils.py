# src/utils.py - Utility Functions

import logging
import os
from pathlib import Path
from config.settings import Settings

def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "pipeline.log"),
            logging.StreamHandler()
        ]
    )

def validate_environment() -> bool:
    """Validate that all required environment variables are set"""
    
    settings = Settings()
    required_vars = [
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET',
        'ADOBE_CLIENT_ID', 'ADOBE_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def create_output_directories():
    """Create necessary output directories"""
    
    directories = ["output", "inputs", "logs", "temp"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)