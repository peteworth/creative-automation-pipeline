# src/bannerbear_composer.py - Bannerbear API Integration Module

import logging
import requests
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from config.settings import Settings

class BannerbearComposer:
    """Handles Bannerbear API operations for asset composition"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = Settings()
        
        # You'll need to add this to your .env file
        self.api_key = self.settings.BANNERBEAR_API_KEY
        
        # Bannerbear collection ID (replaces individual template IDs)
        self.collection_id = self.settings.BANNERBEAR_COLLECTION_ID
        
    def create_campaign_assets(self, campaign_data: Dict[str, Any], product: str, 
                             hero_image_url: str, campaign_folder: Path) -> bool:
        """
        Create campaign assets using Bannerbear Collection API
        
        Args:
            campaign_data: Campaign data from brief
            product: Current product being processed
            hero_image_url: S3 presigned URL for hero image
            campaign_folder: Path to campaign folder for output
            
        Returns:
            True if successful, False if failed
        """
        
        if not self.api_key:
            self.logger.error("No Bannerbear API key found in settings")
            return False
            
        if not self.collection_id:
            self.logger.error("No Bannerbear collection ID found in settings")
            return False
        
        # Create product output folder
        from src.folder_manager import FolderManager
        folder_manager = FolderManager()
        product_output_folder = folder_manager.create_output_structure(campaign_folder, product)
        
        self.logger.info(f"Creating assets for {product} using Bannerbear collection")
        
        # Create all assets with single API call to collection
        asset_data = self._create_bannerbear_collection(
            product_name=product,
            campaign_message=campaign_data['campaign_message'],
            hero_image_url=hero_image_url
        )
        
        if not asset_data:
            self.logger.error(f"Failed to create assets with Bannerbear collection")
            return False
        
        # Download each generated asset using actual dimensions and user's preferred format
        success_count = 0
        
        for asset_info in asset_data:
            height = asset_info['height']
            width = asset_info['width']
            
            # Get the appropriate URL based on campaign file format preference
            file_format = campaign_data['file_format'].lower()
            
            if file_format in ['jpg', 'jpeg']:
                asset_url = asset_info.get('image_url_jpg')
                file_extension = 'jpg'
            elif file_format == 'png':
                asset_url = asset_info.get('image_url_png')
                file_extension = 'png'
            else:
                # Default to PNG if format is unrecognized, fallback to JPG if PNG not available
                asset_url = asset_info.get('image_url_png') or asset_info.get('image_url_jpg')
                file_extension = 'png' if asset_info.get('image_url_png') else 'jpg'
            
            if not asset_url:
                self.logger.error(f"No URL available for requested format '{file_format}' - skipping {width}x{height} asset")
                continue
                
            # Use new naming convention: heightxwidth_campaign_name_product.ext
            output_filename = f"{height}x{width}_{campaign_data['campaign_clean']}_{product}.{file_extension}"
            output_path = product_output_folder / output_filename
            
            # Use asset_manager to download
            from src.asset_manager import AssetManager
            asset_manager = AssetManager()
            
            if asset_manager.download_file_from_url(asset_url, output_path):
                success_count += 1
                # Use a simpler path display to avoid Windows path issues
                self.logger.info(f"SUCCESS: Created {output_path}")
            else:
                self.logger.error(f"Failed to download: {output_filename}")
        
        return success_count > 0
    
    def _get_file_extension_from_url(self, url: str, fallback_format: str) -> str:
        """
        Determine file extension from URL or use fallback format
        
        Args:
            url: Asset URL from Bannerbear
            fallback_format: Campaign file format setting
            
        Returns:
            File extension (jpg, png, etc.)
        """
        
        try:
            # Try to get extension from URL
            if '.png' in url.lower():
                return 'png'
            elif '.jpg' in url.lower() or '.jpeg' in url.lower():
                return 'jpg'
            elif '.gif' in url.lower():
                return 'gif'
            elif '.webp' in url.lower():
                return 'webp'
            else:
                # Fall back to campaign format setting
                fallback = fallback_format.lower()
                return 'jpg' if fallback == 'jpeg' else fallback
                
        except Exception:
            # If anything goes wrong, use fallback
            fallback = fallback_format.lower()
            return 'jpg' if fallback == 'jpeg' else fallback
    
    def _create_bannerbear_collection(self, product_name: str, campaign_message: str, 
                                    hero_image_url: str) -> Optional[List[Dict[str, Any]]]:
        """Create assets using Bannerbear Collection API"""
        
        url = "https://api.bannerbear.com/v2/collections"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use your exact payload structure
        payload = {
            "template_set": self.collection_id,
            "modifications": [
                {
                    "name": "message",
                    "text": f"{campaign_message}",
                    "color": None,
                    "background": None
                },
                {
                    "name": "hero_image",
                    "image_url": hero_image_url
                }
            ],
            "webhook_url": None,
            "metadata": None
        }
        
        self.logger.info(f"Creating collection assets for {product_name}")
        # Removed detailed payload logging for cleaner output
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            self.logger.info(f"Bannerbear collection created successfully")
            # Removed detailed response logging for cleaner output
            
            if response.status_code not in [201, 202]:  # Accept both 201 and 202
                self.logger.error(f"Bannerbear Collection API error: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            
            # Collection returns a collection UID and image UIDs
            collection_uid = result.get('uid')
            if not collection_uid:
                self.logger.error("No collection UID in Bannerbear response")
                return None
            
            # Poll for completion and get all download URLs with dimensions
            return self._wait_for_collection_completion(collection_uid)
            
        except Exception as e:
            self.logger.error(f"Bannerbear Collection API call failed: {str(e)}")
            return None
    
    def _wait_for_collection_completion(self, collection_uid: str, max_wait: int = 120) -> Optional[List[Dict[str, Any]]]:
        """
        Wait for Bannerbear collection generation to complete
        
        Args:
            collection_uid: Bannerbear collection UID
            max_wait: Maximum wait time in seconds
            
        Returns:
            List of dicts with 'url', 'height', 'width' if successful, None if failed
        """
        
        url = f"https://api.bannerbear.com/v2/collections/{collection_uid}"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        start_time = time.time()
        poll_count = 0
        
        # Collection might take longer than individual images
        poll_intervals = [3, 5, 5, 10, 10, 15, 15]  # seconds
        
        self.logger.info("Polling Bannerbear for collection completion...")
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                status = result.get('status')
                
                poll_count += 1
                elapsed = int(time.time() - start_time)
                
                self.logger.info(f"Poll #{poll_count} ({elapsed}s): Collection Status = {status}")
                
                if status == 'completed':
                    # Get all image data from the collection including dimensions
                    images = result.get('images', [])
                    asset_data = []
                    
                    for image in images:
                        # Bannerbear provides separate URLs for different formats
                        image_url_png = image.get('image_url_png')
                        image_url_jpg = image.get('image_url_jpg')
                        height = image.get('height')
                        width = image.get('width')
                        
                        if (image_url_png or image_url_jpg) and height is not None and width is not None:
                            asset_info = {
                                'image_url_png': image_url_png,
                                'image_url_jpg': image_url_jpg,
                                'height': height,
                                'width': width
                            }
                            asset_data.append(asset_info)
                            self.logger.info(f"Found completed image: {width}x{height} - PNG: {bool(image_url_png)}, JPG: {bool(image_url_jpg)}")
                        else:
                            self.logger.warning(f"Image missing required data - PNG: {image_url_png}, JPG: {image_url_jpg}, Height: {height}, Width: {width}")
                    
                    if asset_data:
                        self.logger.info(f"SUCCESS: Collection completed with {len(asset_data)} images")
                        return asset_data
                    else:
                        self.logger.error("Collection completed but no valid image data found")
                        return None
                        
                elif status == 'failed':
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f"Bannerbear collection generation failed: {error}")
                    return None
                    
                elif status in ['pending', 'processing']:
                    # Still processing
                    interval_index = min(poll_count - 1, len(poll_intervals) - 1)
                    sleep_time = poll_intervals[interval_index]
                    self.logger.info(f"Collection still {status}, waiting {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"Unknown collection status: {status}")
                    time.sleep(10)
                    
            except Exception as e:
                self.logger.error(f"Error polling Bannerbear collection: {str(e)}")
                time.sleep(10)
        
        self.logger.error(f"Bannerbear collection timed out after {max_wait} seconds")
        return None
    
    def test_bannerbear_connection(self) -> bool:
        """Test Bannerbear API connection and credentials"""
        
        url = "https://api.bannerbear.com/v2/account"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                account_info = response.json()
                self.logger.info(f"Bannerbear connection successful!")
                self.logger.info(f"Account: {account_info.get('name', 'Unknown')}")
                self.logger.info(f"Plan: {account_info.get('plan_name', 'Unknown')}")
                return True
            else:
                self.logger.error(f"Bannerbear connection failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Bannerbear connection test failed: {str(e)}")
            return False
    
    def send_sample_payload(self) -> bool:
        """Send your exact sample payload to test Bannerbear integration"""
        
        sample_payload = {
            "template_set": self.collection_id or "w5vyp8rbk5nzPmQaDK",
            "modifications": [
                {
                    "name": "message",
                    "text": "Test Product - This is a test message",
                    "color": None,
                    "background": None
                },
                {
                    "name": "hero_image",
                    "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"
                }
            ],
            "webhook_url": None,
            "metadata": None
        }
        
        self.logger.info("Sending your sample payload to Bannerbear:")
        self.logger.info(json.dumps(sample_payload, indent=2))
        
        url = "https://api.bannerbear.com/v2/images/collections"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, json=sample_payload)
            
            self.logger.info(f"Sample payload response: {response.status_code}")
            self.logger.info(f"Response body: {response.text}")
            
            if response.status_code == 201:
                result = response.json()
                collection_uid = result.get('uid')
                self.logger.info(f"Sample collection created with UID: {collection_uid}")
                
                # Wait for completion and get data with dimensions
                final_data = self._wait_for_collection_completion(collection_uid)
                if final_data:
                    self.logger.info(f"Sample collection completed with {len(final_data)} images:")
                    for i, asset_info in enumerate(final_data):
                        png_available = "✓" if asset_info.get('image_url_png') else "✗"
                        jpg_available = "✓" if asset_info.get('image_url_jpg') else "✗"
                        self.logger.info(f"  Image {i+1}: {asset_info['width']}x{asset_info['height']} - PNG:{png_available} JPG:{jpg_available}")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Sample payload failed: {str(e)}")
            return False