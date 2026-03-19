"""
Video Fact Extractor — sends YouTube URL to Gemini for visual spec extraction.

Gemini 2.0+ can "watch" a YouTube video and extract structured data that
text-only transcription misses: on-screen spec sheets, comparison tables,
price slides, reviewer ratings, etc.

This module provides a single public function:
    extract_facts_from_video(youtube_url) -> dict

The result is merged into the article generation prompt so the AI writer
has data from TWO sources: textual transcript + visual analysis.

Cost: ~$0.02-0.05 per video (Gemini Flash).
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (reuse the project-wide instance from ai_provider)
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


def _get_gemini_client():
    """Return a Gemini client or None if unavailable."""
    if not GEMINI_API_KEY or not GENAI_AVAILABLE:
        return None
    try:
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to create Gemini client for video extractor: {e}")
        return None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are an expert automotive data analyst. You are watching a YouTube video
about a car. Your job is to extract EVERY concrete fact visible or mentioned.

Focus on:
1. ALL numeric specs shown on screen or spoken (HP, kW, Nm, range, battery,
   0-100, top speed, dimensions, weight, price in any currency)
2. Competitor cars mentioned or shown in comparison tables
3. The reviewer's overall opinion / verdict (1-2 sentences)
4. Key visual facts only visible on screen (carbon roof, interior materials,
   screen sizes, special design elements)

Return ONLY valid JSON with this exact structure (no markdown fences):
{
  "specs": {
    "horsepower": "value or null",
    "torque_nm": "value or null",
    "range_km": "value or null",
    "battery_kwh": "value or null",
    "acceleration_0_100": "value or null",
    "top_speed_kmh": "value or null",
    "price": "value with currency or null",
    "drivetrain": "AWD/FWD/RWD or null",
    "curb_weight_kg": "value or null",
    "dimensions_mm": "LxWxH or null"
  },
  "competitors_mentioned": ["Brand Model 1", "Brand Model 2"],
  "reviewer_verdict_summary": "1-2 sentence summary of opinion or null",
  "key_visual_facts": ["fact 1", "fact 2"]
}

Rules:
- Use null for any field you couldn't find — do NOT guess.
- For prices, include the original currency: "$34,300" or "CNY 199,800".
- For range, note the test cycle if mentioned: "620 km WLTP".
- Competitors: list ONLY cars explicitly named or shown, not generic segments.
- Return raw JSON only — no commentary, no code fences.
"""


def extract_facts_from_video(youtube_url: str) -> dict:
    """
    Send a YouTube URL to Gemini for visual spec extraction.

    Returns a dict with keys: specs, competitors_mentioned,
    reviewer_verdict_summary, key_visual_facts.
    Returns empty dict on any failure (never raises).
    """
    if not youtube_url:
        return {}

    client = _get_gemini_client()
    if not client:
        logger.info("Video fact extractor: Gemini client unavailable, skipping.")
        return {}

    # Normalise URL for Gemini (needs standard watch URL)
    video_url = _normalise_youtube_url(youtube_url)
    if not video_url:
        logger.warning(f"Could not normalise YouTube URL: {youtube_url}")
        return {}

    # Models to try (cheapest first — Flash is ideal for this)
    models = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
    ]

    for model_name in models:
        try:
            print(f"🎬 Extracting video facts with {model_name}...")

            # Build content parts: YouTube URL + extraction prompt
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_uri(
                        file_uri=video_url,
                        mime_type="video/mp4",
                    ),
                    _EXTRACTION_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Very low — we want precise facts
                    max_output_tokens=2000,
                ),
            )

            text = ""
            try:
                text = response.text
            except Exception:
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            text += part.text

            if not text:
                logger.warning(f"Video fact extraction returned empty from {model_name}")
                continue

            # Token usage tracking
            try:
                usage = getattr(response, 'usage_metadata', None)
                if usage:
                    from ai_engine.modules.token_tracker import record as _record
                    _record(
                        caller='video_fact_extractor',
                        model=model_name,
                        prompt_tokens=getattr(usage, 'prompt_token_count', 0) or 0,
                        completion_tokens=getattr(usage, 'candidates_token_count', 0) or 0,
                    )
            except Exception:
                pass

            # Parse JSON
            facts = _parse_json_response(text)
            if facts:
                _log_extraction_result(facts)
                return facts

        except Exception as e:
            logger.warning(f"Video fact extraction failed with {model_name}: {e}")
            print(f"  ⚠️ {model_name} failed: {e}")
            continue

    logger.info("Video fact extraction: all models failed, returning empty.")
    return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_youtube_url(url: str) -> str:
    """Convert any YouTube URL form to a standard https://www.youtube.com/watch?v=ID."""
    if not url:
        return ""
    # Extract video ID from various formats
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
    # Already a full URL?
    if 'youtube.com/watch' in url:
        return url
    return ""


def _parse_json_response(text: str) -> dict:
    """Extract and parse JSON from Gemini response, handling markdown fences."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Could not parse video facts JSON")
                return {}
        else:
            return {}

    # Validate expected structure
    if not isinstance(data, dict):
        return {}

    # Normalise: ensure all expected keys exist
    return {
        'specs': data.get('specs', {}),
        'competitors_mentioned': data.get('competitors_mentioned', []),
        'reviewer_verdict_summary': data.get('reviewer_verdict_summary'),
        'key_visual_facts': data.get('key_visual_facts', []),
    }


def _log_extraction_result(facts: dict) -> None:
    """Print a summary of extracted facts."""
    specs = facts.get('specs', {})
    filled = sum(1 for v in specs.values() if v and v != 'null')
    competitors = facts.get('competitors_mentioned', [])
    verdict = facts.get('reviewer_verdict_summary')
    visual = facts.get('key_visual_facts', [])

    print(f"  ✅ Video facts extracted: {filled} specs, "
          f"{len(competitors)} competitors, "
          f"{'verdict found' if verdict else 'no verdict'}, "
          f"{len(visual)} visual facts")


def format_video_facts_for_prompt(facts: dict) -> str:
    """
    Format extracted video facts into a text block suitable for
    appending to the article generation prompt / analysis data.

    Returns empty string if facts are empty or trivial.
    """
    if not facts:
        return ""

    parts = []
    specs = facts.get('specs', {})
    filled_specs = {k: v for k, v in specs.items() if v and str(v).lower() != 'null'}

    if filled_specs:
        spec_lines = []
        for key, val in filled_specs.items():
            label = key.replace('_', ' ').title()
            spec_lines.append(f"  ▸ {label}: {val}")
        parts.append("SPECS FROM VIDEO (visually confirmed):\n" + "\n".join(spec_lines))

    competitors = facts.get('competitors_mentioned', [])
    if competitors:
        parts.append("COMPETITORS MENTIONED IN VIDEO: " + ", ".join(competitors))

    verdict = facts.get('reviewer_verdict_summary')
    if verdict and str(verdict).lower() != 'null':
        parts.append(f"REVIEWER'S VERDICT: {verdict}")

    visual = facts.get('key_visual_facts', [])
    if visual:
        parts.append("KEY VISUAL OBSERVATIONS:\n" + "\n".join(f"  • {f}" for f in visual))

    if not parts:
        return ""

    return (
        "\n\n═══ VIDEO ANALYSIS (Gemini visual extraction — HIGH CONFIDENCE) ═══\n"
        + "\n\n".join(parts)
        + "\n═══════════════════════════════════════════════\n"
    )
