# main.py - Creative Automation Pipeline Entry Point

import json
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any
import logging

# Import our modular components
from src.brief_processor import BriefProcessor
from src.asset_manager import AssetManager
from src.firefly_generator import FireflyGenerator
from src.bannerbear_composer import BannerbearComposer
from src.folder_manager import FolderManager
from src.utils import setup_logging, validate_environment
from config.settings import Settings

def main():
    """
    Main pipeline execution - processes everything in START folder
    """
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Creative Automation Pipeline")
        logger.info("=" * 50)
        
        # Validate environment and credentials
        if not validate_environment():
            logger.error("Environment validation failed. Check your .env file.")
            return False
        
        # Initialize components
        folder_manager = FolderManager()
        brief_processor = BriefProcessor()
        asset_manager = AssetManager()
        firefly_generator = FireflyGenerator()
        bannerbear_composer = BannerbearComposer()
        
        # Step 1: Check for jobs in START folder
        logger.info("Checking START folder for new jobs...")
        start_folder = Path("START")
        
        if not start_folder.exists():
            logger.info("START folder not found. Creating it for you.")
            start_folder.mkdir()
            logger.info("Please place your campaign brief JSON and assets in the START folder and run again.")
            return True
        
        # Find JSON briefs in START folder
        json_files = list(start_folder.glob("*.json"))
        
        if not json_files:
            logger.info("No JSON campaign briefs found in START folder.")
            return True
        
        logger.info(f"Found {len(json_files)} campaign brief(s) to process")
        
        # Process each campaign brief
        overall_success = True
        
        for json_file in json_files:
            logger.info(f"Processing campaign brief: {json_file.name}")
            logger.info("-" * 30)
            
            # Step 2: Process campaign brief
            campaign_data = brief_processor.process_brief(str(json_file))
            if not campaign_data:
                logger.error(f"CRITICAL: Failed to process {json_file.name}")
                overall_success = False
                continue
            
            campaign_name = campaign_data['campaign_clean']
            logger.info(f"Campaign: {campaign_data['campaign']}")
            logger.info(f"Products: {len(campaign_data['product'])} products")
            logger.info(f"Target Region: {campaign_data['target_region']}")
            
            # Step 3: Setup campaign folder structure
            logger.info("Setting up campaign folder structure...")
            campaign_folder = folder_manager.setup_campaign_folders(
                campaign_name, start_folder, campaign_data['hero_image']
            )
            
            if not campaign_folder:
                logger.error("CRITICAL: Failed to setup campaign folders")
                overall_success = False
                continue
            
            # Step 4: Process each product
            campaign_success = True
            total_products = len(campaign_data['product'])
            
            for product_index, product in enumerate(campaign_data['product']):
                logger.info(f"Processing product {product_index + 1}/{total_products}: {product}")
                
                # Step 4a: Upload assets to S3 if not already there
                logger.info("Checking and uploading assets to S3...")
                hero_image_s3_url = asset_manager.ensure_asset_in_s3(
                    hero_image_filename=campaign_data['hero_image'],
                    campaign_folder=campaign_folder,
                    campaign_name=campaign_name,
                    product=product
                )
                
                # Step 4b: Generate missing assets if needed
                if not hero_image_s3_url:
                    logger.info(f"Hero image not found, generating with Firefly...")
                    hero_image_s3_url = firefly_generator.generate_and_upload_image(
                        product=product,
                        campaign_name=campaign_name,
                        asset_manager=asset_manager,
                        target_region=campaign_data['target_region']  # Pass target region for locale-aware generation
                    )
                    
                    if not hero_image_s3_url:
                        logger.error(f"CRITICAL: Failed to generate hero image for {product}")
                        campaign_success = False
                        overall_success = False
                        break  # Stop processing this campaign
                else:
                    logger.info("Using existing hero image from S3")
                
                # Step 4c: Create assets using Bannerbear API
                logger.info("Creating assets with Bannerbear API...")
                success = bannerbear_composer.create_campaign_assets(
                    campaign_data=campaign_data,
                    product=product,
                    hero_image_url=hero_image_s3_url,
                    campaign_folder=campaign_folder
                )
                
                if success:
                    logger.info(f"SUCCESS: Successfully created assets for {product}")
                else:
                    logger.error(f"CRITICAL: Failed to create assets for {product}")
                    campaign_success = False
                    overall_success = False
                    break  # Stop processing this campaign
            
            # Step 5: Clean up - archive processed files (only if campaign succeeded)
            if campaign_success:
                logger.info("Archiving processed campaign brief...")
                folder_manager.archive_processed_files(json_file, campaign_folder)
                logger.info(f"SUCCESS: Campaign '{campaign_data['campaign']}' completed successfully!")
            else:
                logger.error(f"FAILED: Campaign '{campaign_data['campaign']}' failed - keeping brief in START folder")
            
            logger.info("=" * 50)
        
        # Final status
        if overall_success:
            logger.info("SUCCESS: All campaigns processed successfully!")
            return True
        else:
            logger.error("FAILED: One or more campaigns failed to process completely")
            return False
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)