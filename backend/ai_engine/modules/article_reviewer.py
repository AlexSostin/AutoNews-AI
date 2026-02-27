"""
AI Article Reviewer — Second pass quality check.

After article generation, sends the HTML to AI for fact-checking,
hallucination removal, and quality improvement.

IMPORTANT: This module NEVER blocks article generation.
If the review fails for any reason, the original article is returned unchanged.
"""
import logging
import re

logger = logging.getLogger(__name__)


def review_article(article_html: str, specs: dict, provider: str = 'gemini') -> str:
    """
    AI editor second pass — reviews generated article for quality issues.
    
    Checks for:
    - Hallucinated features (e.g. "hydraulic cargo lift" on a mini car)
    - Factual inconsistencies between sections
    - Repetitive/water text with no concrete information
    - Nonsensical translations (e.g. "free spoiler")
    - Specs contradictions (different numbers in different sections)
    
    Args:
        article_html: Generated HTML article content
        specs: Extracted car specifications dict
        provider: AI provider to use ('gemini' or 'groq')
    
    Returns:
        Improved HTML article content, or original if review fails
    """
    try:
        try:
            from ai_engine.modules.ai_provider import get_ai_provider
        except ImportError:
            from modules.ai_provider import get_ai_provider
        ai = get_ai_provider(provider)
        
        # Build context about the car from specs
        car_context = _build_car_context(specs)
        
        system_prompt = """You are an expert automotive journalist and fact-checker.
Your job is to review and improve an AI-generated car article.

RULES:
1. Return ONLY the corrected HTML. No explanations, no markdown, no comments.
2. Keep the EXACT same HTML structure (h2, h3, p, ul, li tags).
3. Do NOT add new sections or remove existing sections.
4. Do NOT change the article's tone or style significantly.
5. Keep ALL specific numbers and specs that are accurate.
6. The output must start with <h2> and be valid HTML."""

        review_prompt = f"""Review this automotive article and fix any issues:

CAR INFO:
{car_context}

ARTICLE TO REVIEW:
{article_html}

CHECK FOR AND FIX:
1. HALLUCINATED FEATURES — Remove or fix any features that don't exist for this type of vehicle.
   Example: "hydraulic cargo lift" on a mini city car = hallucination. Remove it.
   Example: "free spoiler" is likely a bad translation. Fix to "integrated rear spoiler" or similar.

2. FACTUAL CONTRADICTIONS — If one section says "405 km range" but another says "305 km", 
   make them consistent (prefer the number from the specs section).

3. REPETITION CHECK — Count how many times each number or spec appears in the article.
   If any specific number (e.g. "1505 km", "449 hp", "$53,500") appears MORE than 2 times:
   - Keep the FIRST mention
   - Keep ONE mention in the specs section (if applicable)
   - REMOVE or rephrase all other mentions
   Each paragraph must add NEW information. If "Why This Matters" repeats the introduction → rewrite it with fresh market insight.

4. LAZY CONS FIX — This is CRITICAL. Check every item in the Cons list:
   - If a Con says "aren't detailed", "not specified", "remain to be seen", "while specific", 
     "no information available", or any phrase about MISSING DATA → it is NOT a real Con.
   - REPLACE lazy Cons with REAL car weaknesses based on the vehicle type:
     For SUVs: heavy curb weight, large turning radius, poor fuel economy, firm ride, limited cargo behind 3rd row
     For EVs: charging time, range anxiety in cold weather, heavy battery weight, limited service network
     For luxury: high maintenance costs, complex infotainment learning curve, expensive consumables
     For all: no Apple CarPlay/Android Auto (if not mentioned), limited color options, no spare tire
   - Pick weaknesses that are REALISTIC for this specific car type and price point.
   - 3 genuine Cons > 5 filler Cons.

5. FILLER OPENER FIX — Check the FIRST sentence of the article:
   If it contains clichés like "isn't just another", "isn't just dipping its toes", 
   "isn't merely", "not content to rest on its laurels", "forget everything you knew":
   → Rewrite it as a DIRECT, factual hook.
   ✅ Good: "AITO's M8 pairs a 1505 km CLTC range with six seats and a $53,500 price tag."
   ❌ Bad: "AITO isn't just dipping its toes into the luxury SUV market..."

6. WATER TEXT — Replace vague sentences like "provides a smooth and enjoyable driving experience" 
   with specific observations. If you can't add specifics, DELETE the sentence entirely.
   Sentences with ZERO concrete numbers or specific features serve no purpose.

7. REGION-SPECIFIC DETAILS — Adapt China-specific references for international audience.
   Example: "green number plate" → explain briefly what it means or remove if not relevant.

8. MEASUREMENT STANDARDS — If range is mentioned, clarify the standard (CLTC/WLTP/EPA) 
   if it's not already specified. Default to CLTC for Chinese vehicles.

9. SUSPICIOUS SPECS — Flag only truly impossible specs (negative numbers, 0 hp, etc).
   High performance numbers ARE valid (some cars have 1000+ hp).

Return the corrected HTML only. Preserve the alt-texts div and the generation comment at the end."""

        logger.info("🔍 AI Editor: Starting article review...")
        
        result = ai.generate_completion(
            prompt=review_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Low temperature for precise editing
            max_tokens=6000
        )
        
        if not result or len(result.strip()) < 100:
            logger.warning("AI Editor: Review returned empty/too short result, using original")
            return article_html
        
        # Clean up: remove markdown code fences if AI wrapped it
        cleaned = _clean_ai_response(result)
        
        # Sanity check: the result should have HTML tags
        if '<h2>' not in cleaned and '<p>' not in cleaned:
            logger.warning("AI Editor: Review result doesn't look like HTML, using original")
            return article_html
        
        # Sanity check: result shouldn't be drastically shorter (AI might have truncated)
        original_length = len(article_html)
        reviewed_length = len(cleaned)
        if reviewed_length < original_length * 0.5:
            logger.warning(
                f"AI Editor: Review result is too short ({reviewed_length} vs {original_length} chars), "
                f"using original"
            )
            return article_html
        
        logger.info(
            f"✅ AI Editor: Article reviewed successfully. "
            f"Original: {original_length} chars → Reviewed: {reviewed_length} chars "
            f"(diff: {reviewed_length - original_length:+d} chars)"
        )
        return cleaned
        
    except Exception as e:
        logger.error(f"❌ AI Editor failed (using original article): {e}")
        return article_html


def _build_car_context(specs: dict) -> str:
    """Build a concise car context string from specs for the reviewer."""
    if not specs or not isinstance(specs, dict):
        return "No specs available"
    
    parts = []
    if specs.get('make'):
        parts.append(f"Make: {specs['make']}")
    if specs.get('model'):
        parts.append(f"Model: {specs['model']}")
    if specs.get('year'):
        parts.append(f"Year: {specs['year']}")
    if specs.get('body_type'):
        parts.append(f"Body type: {specs['body_type']}")
    if specs.get('horsepower'):
        parts.append(f"Horsepower: {specs['horsepower']}")
    if specs.get('engine_type'):
        parts.append(f"Engine: {specs['engine_type']}")
    if specs.get('price'):
        parts.append(f"Price: {specs['price']}")
    if specs.get('range_km'):
        parts.append(f"Range: {specs['range_km']} km")
    
    return '\n'.join(parts) if parts else "No specs available"


def _clean_ai_response(text: str) -> str:
    """Remove markdown code fences and other artifacts from AI response."""
    # Remove ```html ... ``` wrapping
    text = re.sub(r'^```(?:html)?\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())
    
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    return text
