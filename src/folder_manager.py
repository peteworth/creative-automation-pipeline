# src/folder_manager.py - Campaign Folder Structure Management

import logging
import shutil
from pathlib import Path
from typing import Optional
import os

class FolderManager:
    """Manages campaign folder structure and file organization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def setup_campaign_folders(self, campaign_name: str, start_folder: Path, 
                             hero_image_filename: str) -> Optional[Path]:
        """
        Setup campaign folder structure and move assets
        
        Args:
            campaign_name: Clean campaign name for folder
            start_folder: START folder containing assets
            hero_image_filename: Name of hero image file
            
        Returns:
            Path to campaign folder if successful, None if failed
        """
        
        try:
            # Create main campaign folder
            campaign_folder = Path(campaign_name)
            campaign_folder.mkdir(exist_ok=True)
            
            # Create input and output subfolders
            input_folder = campaign_folder / "input"
            output_folder = campaign_folder / "output"
            
            input_folder.mkdir(exist_ok=True)
            output_folder.mkdir(exist_ok=True)
            
            # Move hero image from START to input folder if it exists and is specified
            if hero_image_filename != "auto":
                hero_image_path = start_folder / hero_image_filename
                if hero_image_path.exists():
                    destination = input_folder / hero_image_filename
                    if not destination.exists():  # Don't overwrite if already processed
                        shutil.copy2(hero_image_path, destination)
                        self.logger.info(f"Moved {hero_image_filename} to {input_folder}")
                    else:
                        self.logger.info(f"{hero_image_filename} already exists in input folder")
                else:
                    self.logger.info(f"Hero image {hero_image_filename} not found in START folder (will use naming convention)")
            else:
                self.logger.info("Hero image set to 'auto' - will use campaign_product_hero naming convention")
            
            # Move any other assets from START folder
            asset_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.ai', '.psd']
            for asset_file in start_folder.iterdir():
                if asset_file.is_file() and asset_file.suffix.lower() in asset_extensions:
                    if asset_file.name != hero_image_filename:  # Don't duplicate hero image
                        destination = input_folder / asset_file.name
                        if not destination.exists():
                            shutil.copy2(asset_file, destination)
                            self.logger.info(f"Moved additional asset: {asset_file.name}")
            
            self.logger.info(f"Campaign folder structure created: {campaign_folder}")
            self.logger.info(f"  ├── input/")
            self.logger.info(f"  └── output/")
            
            return campaign_folder
            
        except Exception as e:
            self.logger.error(f"Failed to setup campaign folders: {str(e)}")
            return None
    
    def create_output_structure(self, campaign_folder: Path, product: str) -> Path:
        """
        Create output folder structure for a product
        
        Args:
            campaign_folder: Main campaign folder
            product: Product name
            
        Returns:
            Path to product output folder
        """
        
        output_folder = campaign_folder / "output" / product
        output_folder.mkdir(parents=True, exist_ok=True)
        
        return output_folder
    
    def archive_processed_files(self, json_file: Path, campaign_folder: Path):
        """
        Archive processed JSON file to campaign input folder
        
        Args:
            json_file: Original JSON brief file
            campaign_folder: Campaign folder where to archive
        """
        
        try:
            # Copy JSON brief to campaign INPUT folder (not root campaign folder)
            input_folder = campaign_folder / "input"
            archived_brief = input_folder / "campaign_brief.json"
            shutil.copy2(json_file, archived_brief)
            
            # Remove original JSON from START folder
            json_file.unlink()
            
            self.logger.info(f"Archived campaign brief to {archived_brief}")
            
        except Exception as e:
            self.logger.error(f"Failed to archive files: {str(e)}")