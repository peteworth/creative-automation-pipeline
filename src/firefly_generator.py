# src/firefly_generator.py - Adobe Firefly Image Generation Module

import logging
import requests
from typing import Optional, Dict, Any
import json
from config.settings import Settings

class FireflyGenerator:
    """Handles Adobe Firefly image generation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = Settings()
        self.access_token = None
        
        # Get access token on initialization
        self._get_access_token()
    
    def _get_access_token(self) -> bool:
        """Get Adobe access token for API calls"""
        
        url = "https://ims-na1.adobelogin.com/ims/token/v3"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'client_id': self.settings.ADOBE_CLIENT_ID,
            'client_secret': self.settings.ADOBE_CLIENT_SECRET,
            'grant_type': 'client_credentials',
            'scope': 'openid,AdobeID,firefly_enterprise,ff_apis'
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            if self.access_token:
                self.logger.info("Successfully obtained Adobe access token")
                return True
            else:
                self.logger.error("No access token in response")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to get Adobe access token: {str(e)}")
            return False
    
    def generate_and_upload_image(self, product: str, campaign_name: str, asset_manager, target_region: str = None) -> Optional[str]:
        """
        Generate image using Firefly and upload to S3
        
        Args:
            product: Product name
            campaign_name: Campaign name
            asset_manager: AssetManager instance for S3 operations
            target_region: Target region code (e.g., 'en-US', 'fr-FR') for locale-aware generation
            
        Returns:
            S3 presigned URL if successful, None if failed
        """
        
        if not self.access_token:
            self.logger.error("No access token available")
            return None
        
        # Generate prompt
        prompt = f"Professional photography of {product}, modern style, clean background, high quality, commercial photography"
        
        # Generate image with Firefly - PASS target_region parameter
        image_data = self._generate_image(prompt, target_region)
        if not image_data:
            return None
        
        # Upload to S3
        filename = f"hero.jpg"
        s3_url = asset_manager.upload_generated_image(
            image_data=image_data,
            campaign=campaign_name,
            product=product,
            filename=filename
        )
        
        return s3_url
    
    def _generate_image(self, prompt: str, target_region: str = None) -> Optional[bytes]:
        """Generate image using Firefly API with locale-aware biasing"""
        
        url = "https://firefly-api.adobe.io/v2/images/generate"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Api-Key': self.settings.ADOBE_CLIENT_ID,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "prompt": prompt,
            "contentClass": "photo",
            "size": {
                "width": 2048,
                "height": 2048
            },
            "visualIntensity": 6
        }

        # Set promptBiasingLocaleCode - default to en-US or use target_region
        locale_code = target_region if target_region else "en-US"
        payload["promptBiasingLocaleCode"] = locale_code
        
        if target_region:
            self.logger.info(f"Using target region for image generation: {target_region}")
        else:
            self.logger.info("Using default locale for image generation: en-US")
        
        try:
            self.logger.info(f"Generating image with prompt: {prompt}")
            response = requests.post(url, headers=headers, json=payload)
            
            self.logger.info(f"Firefly API response status: {response.status_code}")
            
            if response.status_code != 200:
                self.logger.error(f"Firefly API error: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
            
            result = response.json()
            
            if 'outputs' in result and len(result['outputs']) > 0:
                output = result['outputs'][0]
                
                # Use the correct path: outputs[0].image.presignedUrl
                if 'image' in output and 'presignedUrl' in output['image']:
                    image_url = output['image']['presignedUrl']
                    self.logger.info(f"Got presigned URL for generated image")
                    
                    # Download the generated image
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    
                    self.logger.info(f"Successfully downloaded generated image")
                    return img_response.content
                else:
                    self.logger.error(f"No presignedUrl found in image object: {output}")
                    return None
            else:
                self.logger.error("No image generated by Firefly")
                return None
                
        except Exception as e:
            self.logger.error(f"Firefly image generation failed: {str(e)}")
            return None