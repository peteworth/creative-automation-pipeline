# config/settings.py - Configuration Management

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Adobe API Configuration
    ADOBE_CLIENT_ID = os.getenv('ADOBE_CLIENT_ID')
    ADOBE_CLIENT_SECRET = os.getenv('ADOBE_CLIENT_SECRET')

    # Bannerbear API Configuration
    BANNERBEAR_API_KEY = os.getenv('BANNERBEAR_API_KEY')
    BANNERBEAR_COLLECTION_ID = os.getenv('BANNERBEAR_COLLECTION_ID')
    
    # Application Settings
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    MOCK_MODE = os.getenv('MOCK_MODE', 'false').lower() == 'true'