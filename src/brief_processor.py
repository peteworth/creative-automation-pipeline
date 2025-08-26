# src/brief_processor.py - Campaign Brief Processing Module

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

class BriefProcessor:
    """Handles parsing and validation of campaign briefs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_brief(self, brief_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process and validate campaign brief JSON
        
        Args:
            brief_file_path: Path to the JSON brief file
            
        Returns:
            Parsed and validated campaign data or None if invalid
        """
        
        try:
            # Load JSON file
            with open(brief_file_path, 'r', encoding='utf-8') as f:
                brief_data = json.load(f)
            
            # Validate required fields
            if not self._validate_brief(brief_data):
                return None
            
            # Process and normalize data
            processed_data = self._normalize_brief_data(brief_data)
            
            self.logger.info("Campaign brief processed successfully")
            return processed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in brief file: {str(e)}")
            return None
        except FileNotFoundError:
            self.logger.error(f"Brief file not found: {brief_file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error processing brief: {str(e)}")
            return None
    
    def _validate_brief(self, brief_data: Dict[str, Any]) -> bool:
        """Validate that brief contains all required fields"""
        
        required_fields = [
            'campaign', 'target_region', 'target_audience', 
            'product', 'campaign_message', 'file_format'
            # Removed 'hero_image' from required fields - now optional
        ]
        
        for field in required_fields:
            if field not in brief_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Validate product is an array with at least 2 products
        if not isinstance(brief_data['product'], list):
            self.logger.error("'product' field must be an array")
            return False
        
        if len(brief_data['product']) < 2:
            self.logger.error("Brief must contain at least 2 products")
            return False
        
        # Validate file format
        valid_formats = ['PNG', 'JPEG', 'JPG']
        if brief_data['file_format'].upper() not in valid_formats:
            self.logger.error(f"Invalid file format. Must be one of: {valid_formats}")
            return False
        
        return True
    
    def _normalize_brief_data(self, brief_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and clean brief data"""
        
        # Clean campaign name for file naming
        brief_data['campaign_clean'] = self._clean_filename(brief_data['campaign'])
        
        # Set default hero_image if not provided (will use naming convention)
        if 'hero_image' not in brief_data or not brief_data['hero_image']:
            brief_data['hero_image'] = "auto"  # Placeholder - will use naming convention
            self.logger.info("No hero_image specified - will use campaign_product_hero naming convention")
        
        # Normalize file format
        brief_data['file_format'] = brief_data['file_format'].upper()
        if brief_data['file_format'] == 'JPG':
            brief_data['file_format'] = 'JPEG'
        
        # Clean product names
        brief_data['product'] = [self._clean_filename(product) for product in brief_data['product']]
        
        return brief_data
    
    def _clean_filename(self, filename: str) -> str:
        """Clean string for use in filenames"""
        
        # Replace spaces and special characters
        cleaned = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in filename)
        return cleaned.strip('_')