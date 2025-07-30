# Image utility functions for LSNP profile pictures
import base64
import os
import mimetypes

def encode_image_to_base64(image_path):
    """
    Encode an image file to base64 string
    Returns tuple: (mime_type, base64_data, size_bytes)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError(f"File is not a valid image: {image_path}")
    
    # Read and encode file
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        
    # Check size (limit to ~20KB as per spec)
    size_bytes = len(image_data)
    if size_bytes > 20480:  # 20KB
        raise ValueError(f"Image too large: {size_bytes} bytes (max 20KB)")
    
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    return mime_type, base64_data, size_bytes

def decode_base64_to_image(base64_data, output_path, mime_type=None):
    """
    Decode base64 string to image file
    """
    try:
        image_data = base64.b64decode(base64_data)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as image_file:
            image_file.write(image_data)
        
        return True
    except Exception as e:
        print(f"Error decoding image: {e}")
        return False

def display_avatar_info(avatar_type, avatar_data):
    """
    Display avatar information in a user-friendly way
    """
    if not avatar_type or not avatar_data:
        return "No profile picture"
    
    # Calculate approximate size
    size_bytes = len(avatar_data) * 3 // 4  # Approximate size from base64
    size_kb = size_bytes / 1024
    
    return f"Profile picture: {avatar_type} ({size_kb:.1f}KB)"

def is_valid_image_file(file_path):
    """
    Check if file is a valid image
    """
    if not os.path.exists(file_path):
        return False
    
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type and mime_type.startswith('image/')

def get_supported_extensions():
    """
    Get list of supported image extensions
    """
    return ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
