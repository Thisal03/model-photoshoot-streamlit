import base64
import requests
import boto3
import os
from datetime import datetime
import uuid
from typing import Dict, Optional

# Valid image type categories for uploads
IMAGE_TYPES = {
    # Model references
    "model_ref": "Model reference images",
    "model": "Model reference images (alias)",
    
    # Outfit/clothing references
    "outfit": "Base outfit images",
    "primary": "Primary clothing reference (legacy)",
    
    # Additional items
    "item": "Additional clothing items",
    "jacket": "Jacket reference",
    "shoes": "Shoes reference",
    "bag": "Bag reference",
    "hat": "Hat reference",
    "scarf": "Scarf reference",
    "belt": "Belt reference",
    "sunglasses": "Sunglasses reference",
    "watch": "Watch reference",
    
    # Jewelry
    "jewelry_neck": "Neck jewelry reference",
    "jewelry_ears": "Ear jewelry reference",
    "jewelry_hands": "Hand/wrist jewelry reference",
    "neck": "Neck jewelry (alias)",
    "ears": "Ear jewelry (alias)",
    "hands": "Hand jewelry (alias)",
    
    # Environment/background
    "background": "Background/environment reference",
    "environment": "Environment reference (alias)",
    
    # Photography references
    "pose": "Pose reference",
    "hair": "Hair styling reference",
    
    # Legacy types
    "accessory": "Accessory reference (legacy)",
    "new_item": "New item upload (temporary)"
}


class S3ImageHandler:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'eu-north-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'crowai-image-bucket')
        self.cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN')
    
    def get_public_url(self, key: str) -> str:
        """Get public URL for S3 object"""
        clean_key = key.lstrip('/')
        if self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{clean_key}"
        region = os.getenv('AWS_REGION', 'eu-north-1')
        return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{clean_key}"
    
    def _get_category_folder(self, image_type: str) -> str:
        """Get the subfolder for an image type category"""
        # Map image types to folder categories
        folder_map = {
            # Model
            "model_ref": "model-refs",
            "model": "model-refs",
            
            # Outfit
            "outfit": "outfit-refs",
            "primary": "outfit-refs",
            
            # Items
            "item": "item-refs",
            "jacket": "item-refs",
            "shoes": "item-refs",
            "bag": "item-refs",
            "hat": "item-refs",
            "scarf": "item-refs",
            "belt": "item-refs",
            "sunglasses": "item-refs",
            "watch": "item-refs",
            "new_item": "item-refs",
            
            # Jewelry
            "jewelry_neck": "jewelry-refs",
            "jewelry_ears": "jewelry-refs",
            "jewelry_hands": "jewelry-refs",
            "neck": "jewelry-refs",
            "ears": "jewelry-refs",
            "hands": "jewelry-refs",
            
            # Environment
            "background": "environment-refs",
            "environment": "environment-refs",
            
            # Photography
            "pose": "pose-refs",
            "hair": "hair-refs",
            
            # Legacy
            "accessory": "accessory-refs"
        }
        
        return folder_map.get(image_type, "photoshoot-refs")
    
    def upload_reference_image(
        self,
        image_bytes: bytes,
        filename: str,
        image_type: str = "primary"
    ) -> Dict[str, str]:
        """
        Upload reference image to S3.
        
        Supports all image types defined in IMAGE_TYPES.
        
        Path format: generated-images/{category-folder}/photoshoot_{type}_{timestamp}_{randomId}.{ext}
        
        Args:
            image_bytes: The image data as bytes
            filename: Original filename (used for extension)
            image_type: Type of image (see IMAGE_TYPES for valid types)
        
        Returns:
            Dict with 'success', 'public_url', 's3_key', and optionally 'error'
        """
        try:
            # Generate unique filename
            timestamp = int(datetime.now().timestamp() * 1000)
            random_id = str(uuid.uuid4()).split('-')[0]
            file_extension = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
            
            # Validate extension
            if file_extension not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                file_extension = 'jpg'
            
            # Get category folder
            category_folder = self._get_category_folder(image_type)
            
            # Build filename and path
            s3_filename = f"photoshoot_{image_type}_{timestamp}_{random_id}.{file_extension}"
            file_path = f"{category_folder}/{s3_filename}"
            s3_key = f"generated-images/{file_path}"
            
            # Determine content type
            content_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp',
                'gif': 'image/gif'
            }
            content_type = content_type_map.get(file_extension, 'image/jpeg')
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_bytes,
                ContentType=content_type,
                CacheControl='max-age=3600'
            )
            
            # Get public URL
            public_url = self.get_public_url(s3_key)
            
            return {
                'success': True,
                'public_url': public_url,
                's3_key': s3_key,
                'image_type': image_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'public_url': '',
                's3_key': '',
                'error': str(e)
            }
    
    def upload_generated_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        job_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload generated image to S3.
        
        Path format: generated-images/model-photoshoots/{timestamp}/photoshoot_{timestamp}_{randomId}.{ext}
        
        Args:
            image_bytes: The generated image data as bytes
            mime_type: MIME type of the image
            job_id: Optional job ID for grouping (uses timestamp if not provided)
        
        Returns:
            Dict with 'success', 'public_url', 's3_key', and optionally 'error'
        """
        try:
            timestamp = int(datetime.now().timestamp() * 1000)
            random_id = str(uuid.uuid4()).split('-')[0]
            
            # Use job_id or timestamp for folder grouping
            folder_id = job_id if job_id else str(timestamp)
            
            # Determine file extension from MIME type
            ext_map = {
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/webp': 'webp',
                'image/gif': 'gif'
            }
            file_ext = ext_map.get(mime_type, 'png')
            
            # Build filename and path
            s3_filename = f"photoshoot_{timestamp}_{random_id}.{file_ext}"
            folder_path = f"model-photoshoots/{folder_id}/{s3_filename}"
            s3_key = f"generated-images/{folder_path}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_bytes,
                ContentType=mime_type,
                CacheControl='max-age=3600'
            )
            
            # Get public URL
            public_url = self.get_public_url(s3_key)
            
            return {
                'success': True,
                'public_url': public_url,
                's3_key': s3_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'public_url': '',
                's3_key': '',
                'error': str(e)
            }
    
    def delete_image(self, s3_key: str) -> Dict[str, bool]:
        """
        Delete an image from S3.
        
        Args:
            s3_key: The S3 key of the image to delete
        
        Returns:
            Dict with 'success' and optionally 'error'
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def url_to_base64(image_url: str) -> str:
    """
    Fetch image from URL and convert to base64.
    
    Args:
        image_url: The URL of the image to fetch
    
    Returns:
        Base64 encoded string of the image data
    
    Raises:
        requests.RequestException: If the image cannot be fetched
    """
    response = requests.get(image_url, timeout=30)
    response.raise_for_status()
    return base64.b64encode(response.content).decode('utf-8')


def get_image_mime_type(filename: str) -> str:
    """
    Get MIME type from filename extension.
    
    Args:
        filename: The filename to check
    
    Returns:
        MIME type string
    """
    ext = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
    mime_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif'
    }
    return mime_map.get(ext, 'image/jpeg')
