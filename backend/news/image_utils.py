"""
Image optimization utilities for WebP conversion
"""
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
import os


def convert_to_webp(image_file, quality=85):
    """
    Convert uploaded image to WebP format for better performance
    
    Args:
        image_file: Django UploadedFile object
        quality: WebP quality (1-100), default 85
    
    Returns:
        ContentFile with WebP image data and new filename
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Apply EXIF orientation (fixes rotated phone photos)
        img = ImageOps.exif_transpose(img)
        
        # Convert RGBA to RGB if necessary (WebP doesn't support transparency in some modes)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to BytesIO as WebP
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)  # method=6 for best compression
        output.seek(0)
        
        # Generate new filename
        original_name = os.path.basename(os.path.splitext(image_file.name)[0])
        new_filename = f"{original_name}.webp"
        
        return ContentFile(output.read(), name=new_filename)
    
    except Exception as e:
        print(f"Error converting image to WebP: {e}")
        return image_file  # Return original if conversion fails


def optimize_image(image_file, max_width=1920, max_height=1080, quality=85):
    """
    Optimize image by resizing and converting to WebP
    
    Args:
        image_file: Django UploadedFile object
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: WebP quality (1-100)
    
    Returns:
        ContentFile with optimized WebP image
    """
    try:
        img = Image.open(image_file)
        
        # Apply EXIF orientation FIRST (fixes rotated phone photos)
        img = ImageOps.exif_transpose(img)
        
        # Resize if larger than max dimensions
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as WebP
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)
        output.seek(0)
        
        # Generate new filename
        original_name = os.path.basename(os.path.splitext(image_file.name)[0])
        new_filename = f"{original_name}_optimized.webp"
        
        return ContentFile(output.read(), name=new_filename)
    
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return convert_to_webp(image_file, quality)  # Try simple conversion as fallback

