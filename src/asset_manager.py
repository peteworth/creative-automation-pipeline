# src/asset_manager.py - S3 Asset Management Module

import boto3
import logging
import os
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
import requests
from config.settings import Settings

class AssetManager:
    """Handles S3 storage operations and asset management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = Settings()
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.settings.AWS_REGION
            )
            self.bucket_name = self.settings.AWS_S3_BUCKET
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def ensure_asset_in_s3(self, hero_image_filename: str, campaign_folder: Path,
                          campaign_name: str, product: str) -> Optional[str]:
        """
        Ensure hero image exists in S3, upload if not present
        Uses campaign_product_hero naming convention for local search
        Search priority: Local files first, then S3/generated to reduce API calls
        
        Args:
            hero_image_filename: Name of the hero image file from JSON (or "auto")
            campaign_folder: Local campaign folder containing assets
            campaign_name: Campaign name
            product: Product name
            
        Returns:
            S3 presigned URL if successful, None if failed
        """
        
        # PRIORITY 1: Look for the file using campaign_product_hero naming convention in START folder
        start_folder = Path("START")
        hero_file = self._find_hero_image_by_naming_convention(
            start_folder, campaign_name, product
        )
        
        if hero_file:
            self.logger.info(f"Found hero image using naming convention: {hero_file}")
            s3_key = f"assets/{hero_file.name}"
            return self._upload_local_file_to_s3(hero_file, s3_key)
        
        # PRIORITY 2: Look for exact filename in campaign input folder (if specified and not "auto")
        if hero_image_filename != "auto":
            input_folder = campaign_folder / "input"
            exact_file = input_folder / hero_image_filename
            if exact_file.exists():
                self.logger.info(f"Found hero image with exact filename: {exact_file}")
                s3_key = f"assets/{hero_image_filename}"
                return self._upload_local_file_to_s3(exact_file, s3_key)
        
        # PRIORITY 3: Check if already exists in S3 (only if filename was specified)
        if hero_image_filename != "auto":
            s3_key = f"assets/{hero_image_filename}"
            if self._object_exists_in_s3(s3_key):
                self.logger.info(f"Asset already exists in S3: {s3_key}")
                return self.generate_presigned_url(s3_key)
        
        # PRIORITY 4: Check for previously generated images in the generated/ folder
        generated_asset_url = self._check_for_generated_asset(campaign_name, product)
        if generated_asset_url:
            self.logger.info(f"Found previously generated asset for {campaign_name}_{product}")
            return generated_asset_url
        
        self.logger.warning(f"Hero image not found using any method for {campaign_name}_{product}")
        self.logger.info("Will proceed to Firefly generation...")
        return None
    
    def _find_hero_image_by_naming_convention(self, start_folder: Path, 
                                            campaign_name: str, product: str) -> Optional[Path]:
        """
        Find hero image using campaign_product_hero naming convention
        
        Args:
            start_folder: START folder to search in
            campaign_name: Clean campaign name
            product: Clean product name
            
        Returns:
            Path to found image file or None
        """
        
        # Expected naming patterns
        patterns = [
            f"{campaign_name}_{product}_hero.*",
            f"{campaign_name.lower()}_{product.lower()}_hero.*",
            f"{campaign_name}_{product}_Hero.*",  # Capital H
        ]
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        self.logger.info(f"Searching for hero images with patterns:")
        for pattern in patterns:
            self.logger.info(f"  - {pattern}")
        
        self.logger.info(f"In folder: {start_folder}")
        
        # List all files in START folder for debugging
        try:
            all_files = list(start_folder.iterdir())
            self.logger.info(f"Files found in START folder ({len(all_files)} total):")
            for file_path in all_files:
                if file_path.is_file():
                    self.logger.info(f"  - {file_path.name}")
        except Exception as e:
            self.logger.error(f"Could not list files in START folder: {e}")
        
        for pattern in patterns:
            # Search for files matching the pattern
            matches = list(start_folder.glob(pattern))
            self.logger.info(f"Pattern '{pattern}' found {len(matches)} matches")
            
            for file_path in matches:
                if file_path.suffix.lower() in image_extensions:
                    self.logger.info(f"SUCCESS: Found hero image with pattern {pattern}: {file_path.name}")
                    return file_path
                else:
                    self.logger.info(f"Skipped {file_path.name} - not an image file")
        
        self.logger.warning(f"No hero image found using naming convention for {campaign_name}_{product}")
        return None
    
    def _check_for_generated_asset(self, campaign_name: str, product: str) -> Optional[str]:
        """
        Check if there's already a generated asset for this campaign/product combination
        
        Args:
            campaign_name: Campaign name
            product: Product name
            
        Returns:
            Presigned URL if found, None if not found
        """
        
        try:
            # Search in the generated/ folder for files matching campaign and product
            prefix = f"generated/{campaign_name}_{product}_"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=10
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                # Found existing generated asset(s), use the first one
                existing_key = response['Contents'][0]['Key']
                self.logger.info(f"Found existing generated asset: {existing_key}")
                return self.generate_presigned_url(existing_key)
            else:
                self.logger.info(f"No existing generated assets found for {campaign_name}_{product}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking for generated assets: {str(e)}")
            return None
    
    def _upload_local_file_to_s3(self, local_path: Path, s3_key: str) -> Optional[str]:
        """Upload local file to S3 and return presigned URL"""
        
        try:
            with open(local_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=f,
                    ContentType=self._get_content_type(local_path.suffix)
                )
            
            self.logger.info(f"SUCCESS: Uploaded {local_path.name} to S3: {s3_key}")
            return self.generate_presigned_url(s3_key)
            
        except Exception as e:
            self.logger.error(f"FAILED: Failed to upload {local_path} to S3: {str(e)}")
            return None
    
    def upload_generated_image(self, image_data: bytes, campaign: str, product: str, filename: str) -> Optional[str]:
        """
        Upload generated image to S3
        
        Args:
            image_data: Binary image data
            campaign: Campaign name
            product: Product name
            filename: Filename for the asset
            
        Returns:
            Presigned URL if successful, None if failed
        """
        
        s3_key = f"generated/{campaign}_{product}_{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType='image/jpeg'
            )
            
            self.logger.info(f"SUCCESS: Uploaded generated image to S3: {s3_key}")
            return self.generate_presigned_url(s3_key)
            
        except Exception as e:
            self.logger.error(f"FAILED: Failed to upload generated image: {str(e)}")
            return None
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for S3 object
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if failed
        """
        
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except Exception as e:
            self.logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
            return None
    
    def download_file_from_url(self, url: str, local_path: Path) -> bool:
        """Download file from URL to local path"""
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Create parent directories if they don't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"SUCCESS: Downloaded file to: {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"FAILED: Failed to download file from {url}: {str(e)}")
            return False
    
    def _object_exists_in_s3(self, s3_key: str) -> bool:
        """Check if object exists in S3"""
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def _get_content_type(self, file_extension: str) -> str:
        """Get content type based on file extension"""
        
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.indt': 'application/octet-stream',
            '.indd': 'application/octet-stream'
        }
        
        return content_types.get(file_extension.lower(), 'application/octet-stream')