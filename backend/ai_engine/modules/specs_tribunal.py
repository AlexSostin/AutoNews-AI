"""
Specs Tribunal — The ultimate judge for vehicle specifications.

This module resolves conflicting information between the video transcript (audio),
video visuals (Gemini Vision), web context, and the internal database.
It outputs a single, unified, verified "Absolute Truth" dictionary of specs
that the rest of the generation pipeline must obey.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.ai_provider import get_ai_provider
    from ai_engine.modules.prompt_sanitizer import wrap_untrusted, ANTI_INJECTION_NOTICE
except ImportError:
    from modules.ai_provider import get_ai_provider
    from modules.prompt_sanitizer import wrap_untrusted, ANTI_INJECTION_NOTICE


def convene_specs_tribunal(
    transcript_analysis: str,
    video_facts: dict,
    web_context: str,
    internal_specs_text: str,
    provider: str = 'gemini'
) -> dict:
    """
    Compiles evidence from all sources and asks the AI to act as a judge.
    Returns a unified dict containing 'verified_specs' and 'summary_for_writer'.
    """
    ai = get_ai_provider(provider)
    
    # Format video facts into a clean string if it's a dict
    video_facts_str = ""
    if video_facts and isinstance(video_facts, dict) and video_facts.get('specs'):
        video_facts_str = json.dumps(video_facts.get('specs', {}), indent=2, ensure_ascii=False)
    
    prompt = f"""You are the SPECS TRIBUNAL — an expert automotive judge.
Your job is to review conflicting evidence about a vehicle from 4 different sources
and establish the ABSOLUTE TRUTH for its specifications.

EVIDENCE SOURCE 1: TRANSCRIPT ANALYSIS (What the reviewer *said*)
{wrap_untrusted(transcript_analysis or 'No transcript data', 'AUDIO_TRANSCRIPT', 3000)}

EVIDENCE SOURCE 2: VIDEO VISUALS (What optical character recognition saw on screen)
```json
{video_facts_str or '{}'}
```

EVIDENCE SOURCE 3: WEB CONTEXT (What the internet search found)
{wrap_untrusted(web_context or 'No web data', 'WEB_CONTEXT', 5000)}

EVIDENCE SOURCE 4: INTERNAL DATABASE (Our verified ground truth — HIGHEST AUTHORITY if present)
{wrap_untrusted(internal_specs_text or 'No internal database data', 'INTERNAL_DB', 2000)}
{ANTI_INJECTION_NOTICE}

═══ TRIBUNAL RULES ═══
1. INTERNAL DB WINS: If Evidence 4 (Internal DB) exists, its numbers are the absolute truth.
2. MAJORITY RULES: If 2 or 3 sources agree on a number, it becomes the truth.
3. VISUALS > AUDIO: If the reviewer says "1000 hp" but the video visual (Evidence 2) says "300 hp", trust the visual. Reviewers exaggerate.
4. WEB > AUDIO: If the web context contradicts the transcript with realistic numbers, trust the web.
5. NO GUESSING: If all sources are silent on a metric, output null.

Return ONLY valid JSON in this exact structure:
{{
  "verified_specs": {{
    "make": "String",
    "model": "String",
    "trim": "String or null",
    "year": 2026,
    "engine": "String or null",
    "horsepower": 1381,
    "torque": "String or null",
    "acceleration": "String or null",
    "top_speed": "String or null",
    "drivetrain": "String or null",
    "battery": "String or null",
    "range": "String or null",
    "price": "String or null"
  }},
  "rulings": [
    "Web context confirmed 1381 hp, overriding reviewer's claim of 1700 hp.",
    "Battery size was taken from Video Visuals as it was missing in Web Context."
  ]
}}
"""

    system_prompt = "You are the Specs Tribunal. Output ONLY valid JSON."
    
    fallback_result = {
        'verified_specs': None,
        'summary_for_writer': ""
    }
    
    try:
        response = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # Avoid 0.0 to prevent Gemini repetition bugs
            max_tokens=2000,
            caller='specs_tribunal'
        )
        
        text = response.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        result = json.loads(text.strip())
        
        # Build a plain text summary for the article writer LLM
        verified_specs = result.get('verified_specs', {})
        rulings = result.get('rulings', [])
        
        lines = ["═══ TRIBUNAL VERDICT (ABSOLUTE GROUND TRUTH) ═══"]
        for k, v in verified_specs.items():
            if v:
                lines.append(f"  ▸ {str(k).title().replace('_', ' ')}: {v}")
                
        if rulings:
            lines.append("\n  [Tribunal Rulings]:")
            for r in rulings:
                lines.append(f"  • {r}")
                
        summary_for_writer = "\n".join(lines) + "\n═══════════════════════════════════════════════"
        
        # Clean up the output specs so they mirror what `extract_specs_dict` would produce
        safe_specs = {}
        for k, v in verified_specs.items():
            safe_specs[k] = v if v is not None else "Not specified"
            
        # Ensure year and horsepower are integers or None, not "Not specified" strings
        for num_field in ['year', 'horsepower']:
            val = safe_specs.get(num_field)
            if val == "Not specified" or val is None:
                safe_specs[num_field] = None
            else:
                try:
                    safe_specs[num_field] = int(val)
                except (ValueError, TypeError):
                    safe_specs[num_field] = None
                    
        return {
            'verified_specs': safe_specs,
            'summary_for_writer': summary_for_writer
        }
        
    except Exception as e:
        logger.error(f"Specs Tribunal failed: {e}")
        return fallback_result
