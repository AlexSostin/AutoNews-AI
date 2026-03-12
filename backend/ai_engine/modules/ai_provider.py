"""
AI Provider Factory - supports both Groq and Gemini
Uses google-genai (new unified SDK) for Gemini access
"""
import os
from groq import Groq

# Safe import of google-genai (new SDK)
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception as e:
    print(f"Warning: google.genai import failed: {e}")
    genai = None
    types = None
    GENAI_AVAILABLE = False

# Get API keys from environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = None
if GEMINI_API_KEY and GENAI_AVAILABLE:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to create Gemini client: {e}")

# Tracks which model was actually used in the last successful generation
_last_model_used = ''


class AIProvider:
    """Base class for AI providers"""
    
    @staticmethod
    def generate_completion(prompt, system_prompt=None, temperature=0.8, max_tokens=3000):
        raise NotImplementedError


class GroqProvider(AIProvider):
    """Groq AI Provider - Fast inference"""
    
    @staticmethod
    def generate_completion(prompt, system_prompt=None, temperature=0.8, max_tokens=3000):
        if not groq_client:
            raise Exception("Groq API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content if response.choices else ""


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider - Multimodal capabilities (uses google-genai SDK)"""
    
    @staticmethod
    def generate_completion(prompt, system_prompt=None, temperature=0.8, max_tokens=3000):
        if not GEMINI_API_KEY:
            raise Exception("Gemini API key not configured")
        if not GENAI_AVAILABLE or not gemini_client:
            raise Exception("google-genai library not available or client not initialised")
        
        # Model priority (updated March 2026):
        # gemini-3.1-pro (best quality, preview) > gemini-3-flash (frontier at Flash price)
        # > gemini-2.5-pro-exp (free backup) > gemini-2.5-flash > gemini-2.0-flash (last resort)
        # NOTE: gemini-3-pro was SHUT DOWN on March 9 2026 — do NOT use it
        model_names_to_try = [
            'gemini-3.1-pro-preview',
            'gemini-3-flash-preview',
            'gemini-2.5-pro-exp-03-25',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
        ]
        
        # Build config with proper system_instruction isolation
        # (prevents prompt injection from user content overriding system behavior)
        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            gen_config.system_instruction = system_prompt
        
        last_error = None
        for model_name in model_names_to_try:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config,
                )
                
                # Robust text extraction
                text = ""
                try:
                    text = response.text
                except Exception:
                    # Fallback: extract from candidates
                    if response.candidates:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'text'):
                                text += part.text
                
                if text:
                    print(f"✅ Generated with {model_name}")
                    # Record which model succeeded for provider tracker
                    import ai_engine.modules.ai_provider as _self_mod
                    _self_mod._last_model_used = model_name
                    return text
                    
            except Exception as e:
                last_error = str(e)
                print(f"Failed with model {model_name}: {e}")
                continue
        
        # If all models failed, raise the last error
        raise Exception(f"All Gemini models failed. Last error: {last_error}")



def get_ai_provider(provider_name='gemini'):
    """
    Factory function to get AI provider
    
    Args:
        provider_name: 'groq' or 'gemini'
    
    Returns:
        AIProvider instance
    """
    provider_name = provider_name.lower()
    
    if provider_name == 'groq':
        return GroqProvider()
    elif provider_name == 'gemini':
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}. Use 'groq' or 'gemini'")


def get_light_provider():
    """Return Groq for lightweight tasks (classification, short JSON, tagging).
    
    Falls back to Gemini if Groq API key is not configured.
    Use this for tasks that don't need Gemini's quality:
    - Structured JSON extraction
    - Short text generation (verdict, summaries)
    - Classification / tagging
    - License checks
    """
    if GROQ_API_KEY and groq_client:
        return GroqProvider()
    return GeminiProvider()


def get_available_providers():
    """
    Returns list of available/configured providers
    
    Returns:
        list of dicts with provider info
    """
    providers = []
    
    if GROQ_API_KEY:
        providers.append({
            'name': 'groq',
            'display_name': 'Groq (Fast)',
            'model': GROQ_MODEL,
            'available': True
        })
    
    if GEMINI_API_KEY and GENAI_AVAILABLE and gemini_client:
        providers.append({
            'name': 'gemini',
            'display_name': 'Google Gemini',
            'model': GEMINI_MODEL,
            'available': True
        })
    
    return providers
