"""
AI Provider Factory - supports Gemini
Uses google-genai (new unified SDK) for Gemini access
"""
import os

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
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# Initialize clients
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
    def generate_completion(prompt, system_prompt=None, temperature=0.8, max_tokens=3000, caller='unknown'):
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider - Multimodal capabilities (uses google-genai SDK)"""
    
    @staticmethod
    def generate_completion(prompt, system_prompt=None, temperature=0.8, max_tokens=3000, caller='unknown'):
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
                    
                    # ── Token usage tracking ──────────────────────────
                    try:
                        usage = getattr(response, 'usage_metadata', None)
                        if usage:
                            prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
                            completion_tokens = getattr(usage, 'candidates_token_count', 0) or 0
                            from ai_engine.modules.token_tracker import record as _record_tokens
                            _record_tokens(
                                caller=caller,
                                model=model_name,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                            )
                    except Exception as _tok_err:
                        # Never let token tracking break generation
                        pass
                    # ──────────────────────────────────────────────────
                    
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
        provider_name: 'gemini'
    
    Returns:
        AIProvider instance
    """
    provider_name = provider_name.lower()
    
    if provider_name == 'gemini':
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}. Use 'gemini'")


def get_light_provider():
    """Return Gemini for lightweight tasks (classification, short JSON, tagging).
    
    This used to return Groq, but Groq was removed in favor of standardizing
    on Gemini for all tasks to improve output formatting stability.
    """
    return GeminiProvider()

def get_generate_provider():
    """Return Gemini for heavy tasks.
    
    This used to differentiate from light provider, but now all use Gemini.
    """
    return GeminiProvider()

def get_available_providers():
    """
    Returns list of available/configured providers
    
    Returns:
        list of dicts with provider info
    """
    providers = []
    
    if GEMINI_API_KEY and GENAI_AVAILABLE and gemini_client:
        providers.append({
            'name': 'gemini',
            'display_name': 'Google Gemini',
            'model': GEMINI_MODEL,
            'available': True
        })
    
    return providers
