"""
AI Image Generator - Generate photorealistic car images using Gemini Image API

Uses the new google-genai SDK to generate professional automotive photographs
based on a reference image (e.g., YouTube thumbnail) and style prompt.
"""
import os
import io
import base64
import tempfile
import requests

# Try importing the new google-genai SDK first, fall back to legacy
try:
    from google import genai
    from google.genai import types
    GENAI_NEW_SDK = True
except ImportError:
    GENAI_NEW_SDK = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Available scene styles for the dropdown
SCENE_STYLES = {
    'scenic_road': 'on a dramatic winding mountain road at golden hour, warm sunlight hitting the paint, '
                   'mountains in soft bokeh background, slight motion blur on the road',
    'desert_sunset': 'in an open desert highway at sunset, dramatic orange-purple gradient sky, '
                     'long shadows on warm sand, heat haze visible on the asphalt',
    'urban_city': 'on a rain-slicked city street at night, neon reflections on wet pavement, '
                  'bokeh city lights in background, moody cinematic atmosphere',
    'mountain_pass': 'on an alpine mountain pass overlooking a valley, snow-capped peaks, '
                     'dramatic clouds, crisp cool-toned lighting, epic sense of scale',
    'studio': 'in a professional car photography studio, clean infinite white backdrop, '
              'three-point studio lighting with rim lights, sharp reflections on bodywork',
    'coastal': 'on a dramatic coastal cliff road overlooking turquoise ocean, '
               'golden hour side lighting, waves crashing below, Mediterranean atmosphere',
    'forest': 'on a winding road through an autumn forest, golden and red leaves, '
              'dappled sunlight through the canopy, natural warm color palette',
    'showroom': 'in a luxury modern showroom with polished dark marble floors, '
                'dramatic spotlights creating pools of light, reflections on the floor',
}

# Image generation model — easy to swap later
IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.0-flash-exp-image-generation')


def generate_car_image(image_url: str, car_name: str, style: str = 'scenic_road', custom_prompt: str = '') -> dict:
    """
    Generate a photorealistic car image based on a reference image.
    
    Args:
        image_url: URL of the reference image (existing thumbnail)
        car_name: e.g., "2025 BYD Seal EV"
        style: key from SCENE_STYLES dict
        custom_prompt: Optional custom prompt to override the default car photo prompt
        
    Returns:
        dict with 'success', 'image_data' (base64), 'mime_type', or 'error'
    """
    if not GENAI_NEW_SDK:
        return {'success': False, 'error': 'google-genai SDK not installed. Run: pip install google-genai'}
    
    if not PIL_AVAILABLE:
        return {'success': False, 'error': 'Pillow not installed. Run: pip install Pillow'}
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return {'success': False, 'error': 'GEMINI_API_KEY not set'}
    
    if custom_prompt and custom_prompt.strip():
        # User provided a custom prompt — use it with photography enhancements
        prompt = (
            f"{custom_prompt.strip()}"
            f"\n\nPhotography direction: "
            f"Shot with a Canon EOS R5, 85mm f/1.4 lens. Professional lighting setup. "
            f"Shallow depth of field, tack-sharp focus on the main subject. "
            f"Rich, vibrant color grading with cinematic warmth. Ultra-realistic details. "
            f"\n\nCritical requirements: "
            f"Use the reference image as visual context/inspiration. "
            f"NO text, watermarks, or logos. "
            f"Output a single stunning, magazine-quality photograph."
        )
    else:
        # Default auto-prompt for car photos
        scene_desc = SCENE_STYLES.get(style, SCENE_STYLES['scenic_road'])
        
        prompt = (
            f"Create a stunning photorealistic automotive photograph of this exact car: {car_name}. "
            f"\n\nScene: Place the car {scene_desc}. "
            f"\n\nPhotography direction: "
            f"Shot with a Canon EOS R5, 85mm f/1.4 lens at eye level, three-quarter front angle. "
            f"Professional 3-point automotive lighting setup. Shallow depth of field with the car "
            f"in tack-sharp focus. Rule of thirds composition. "
            f"Rich, vibrant color grading with cinematic warmth. "
            f"Ultra-realistic reflections on paint and glass surfaces. "
            f"Visible microdetails: panel gaps, badge lettering, tire tread. "
            f"\n\nCritical requirements: "
            f"The car must match the EXACT make, model, body shape, headlights, grille, and color "
            f"from the reference image. Do NOT change the car's design. "
            f"NO text, watermarks, logos, or license plates. "
            f"Output a single hero shot, magazine cover quality."
        )
    
    try:
        # 1. Download reference image
        print(f"🖼️ Downloading reference image: {image_url[:80]}...")
        resp = requests.get(image_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; FreshMotors/1.0)'
        })
        resp.raise_for_status()
        
        # 2. Open as PIL Image
        ref_image = Image.open(io.BytesIO(resp.content))
        # Resize if too large (Gemini has limits)
        max_size = 1024
        if max(ref_image.size) > max_size:
            ref_image.thumbnail((max_size, max_size), Image.LANCZOS)
        
        # 3. Call Gemini Image API
        print(f"🎨 Generating AI image: {car_name} — {style}...")
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[prompt, ref_image],
            config=types.GenerateContentConfig(
                response_modalities=['Text', 'Image'],
            ),
        )
        
        # 4. Extract generated image from response
        if not response.candidates or not response.candidates[0].content.parts:
            return {'success': False, 'error': 'No image data in response'}
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type or 'image/png'
                
                # Convert to base64 for API transport
                if isinstance(image_data, bytes):
                    b64_data = base64.b64encode(image_data).decode('utf-8')
                else:
                    b64_data = image_data  # Already base64
                
                print(f"✅ AI image generated successfully ({len(image_data)} bytes)")
                return {
                    'success': True,
                    'image_data': b64_data,
                    'mime_type': mime_type,
                }
            elif hasattr(part, 'text') and part.text:
                print(f"  AI text response: {part.text[:200]}")
        
        return {'success': False, 'error': 'Response contained no image data, only text.'}
        
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Failed to download reference image: {e}'}
    except Exception as e:
        error_msg = str(e)
        # Check for common API errors
        if 'SAFETY' in error_msg.upper() or 'BLOCKED' in error_msg.upper():
            return {'success': False, 'error': f'Image generation blocked by safety filters. Try a different style. ({error_msg[:200]})'}
        if 'QUOTA' in error_msg.upper() or 'RATE' in error_msg.upper():
            return {'success': False, 'error': f'API quota exceeded. Try again later. ({error_msg[:200]})'}
        return {'success': False, 'error': f'Image generation failed: {error_msg[:300]}'}


def get_available_styles() -> list:
    """Return list of available styles for the frontend dropdown."""
    return [
        {'key': k, 'label': k.replace('_', ' ').title(), 'description': v}
        for k, v in SCENE_STYLES.items()
    ]
