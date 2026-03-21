"""
AI Provider Factory - supports Gemini
Uses google-genai (new unified SDK) for Gemini access.

Model routing: PRO tier (3.1-pro) for article generation, FLASH tier for everything else.
Rate limiter: Redis counters prevent 429s by auto-skipping models near their limits.
"""
import os
import time
import hashlib
import logging

logger = logging.getLogger(__name__)

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
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={'timeout': 150000}  # Timeout is in milliseconds (150s)
        )
    except Exception as e:
        print(f"Warning: Failed to create Gemini client: {e}")

# Tracks which model was actually used in the last successful generation
_last_model_used = ''

# ─── Model Tier Configuration ────────────────────────────────────────────
# Callers that NEED Pro-quality output (long-form generation, creative work)
PRO_CALLERS = frozenset({
    'article_generate',
    'rss_generate',
    'article_review',
    'article_enhance',
    'comparison',
    'article_verdict_fallback',
})

# Model cascades by tier
PRO_MODELS = [
    'gemini-3.1-pro-preview',
    'gemini-3-flash-preview',
    'gemini-2.5-pro-exp-03-25',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
]
FLASH_MODELS = [
    'gemini-3-flash-preview',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
]

# Rate limits per model (from Google AI Studio dashboard)
# We use 80% of the limit as our soft cap
MODEL_RATE_LIMITS = {
    'gemini-3.1-pro-preview': {'rpm': 25, 'rpd': 250},
    'gemini-3-flash-preview': {'rpm': 1000, 'rpd': 10000},
    'gemini-2.5-pro-exp-03-25': {'rpm': 10, 'rpd': 500},
    'gemini-2.5-flash': {'rpm': 1000, 'rpd': 10000},
    'gemini-2.0-flash': {'rpm': 2000, 'rpd': None},  # unlimited RPD
}
RATE_LIMIT_THRESHOLD = 0.80  # Skip model at 80% of its limit


def _check_rate_limit(model_name: str) -> bool:
    """
    Check if we should skip this model because it's near its rate limit.
    Uses Redis counters for RPM (per-minute) and RPD (per-day).
    
    Returns True if model should be SKIPPED.
    """
    limits = MODEL_RATE_LIMITS.get(model_name)
    if not limits:
        return False  # Unknown model, allow
    
    try:
        from django.core.cache import cache
        
        # Check RPM (requests per minute)
        minute_key = f"rl_rpm:{model_name}:{int(time.time()) // 60}"
        rpm_count = cache.get(minute_key, 0)
        rpm_limit = limits['rpm']
        if rpm_count >= int(rpm_limit * RATE_LIMIT_THRESHOLD):
            logger.info(f"⚡ Rate limit: {model_name} RPM {rpm_count}/{rpm_limit} — skipping")
            return True
        
        # Check RPD (requests per day)
        rpd_limit = limits.get('rpd')
        if rpd_limit:
            day_key = f"rl_rpd:{model_name}:{time.strftime('%Y%m%d')}"
            rpd_count = cache.get(day_key, 0)
            if rpd_count >= int(rpd_limit * RATE_LIMIT_THRESHOLD):
                logger.info(f"⚡ Rate limit: {model_name} RPD {rpd_count}/{rpd_limit} — skipping")
                return True
        
        return False
    except Exception:
        return False  # Redis down → allow all


def _record_rate_limit(model_name: str):
    """Increment rate limit counters after a successful API call."""
    try:
        from django.core.cache import cache
        
        # Increment RPM counter (expires in 60s)
        minute_key = f"rl_rpm:{model_name}:{int(time.time()) // 60}"
        try:
            cache.incr(minute_key)
        except ValueError:
            cache.set(minute_key, 1, timeout=60)
        
        # Increment RPD counter (expires end of day → 24h is safe)
        day_key = f"rl_rpd:{model_name}:{time.strftime('%Y%m%d')}"
        try:
            cache.incr(day_key)
        except ValueError:
            cache.set(day_key, 1, timeout=86400)
    except Exception:
        pass


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
        
        # Smart model routing: PRO tier for heavy tasks, FLASH for lightweight
        if caller in PRO_CALLERS:
            model_names_to_try = PRO_MODELS
        else:
            model_names_to_try = FLASH_MODELS
            logger.debug(f"🔀 Routing '{caller}' to FLASH tier")
        
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
            # Rate limit check — skip models near their quota
            if _check_rate_limit(model_name):
                continue
            
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
                    tier = 'PRO' if caller in PRO_CALLERS else 'FLASH'
                    print(f"✅ Generated with {model_name} [{tier}] caller={caller}")
                    
                    # Record rate limit counter
                    _record_rate_limit(model_name)
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
