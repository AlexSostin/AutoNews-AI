"""
AI-powered title, SEO description, and summary generation.

Runs AFTER article generation so the AI can pick the most impressive
fact from the completed article for the title hook.
"""
import re
import logging

logger = logging.getLogger(__name__)


def _truncate_summary(text: str, max_len: int = 3000) -> str:
    """Truncate summary at a sentence or word boundary.
    
    Priority: last sentence end (.) within limit > last word boundary > hard cut.
    Targets ~500 words (3000 chars) for rich article preview cards.
    """
    if len(text) <= max_len:
        return text
    
    truncated = text[:max_len]
    
    # Try to cut at last sentence end (period followed by space or end)
    last_period = truncated.rfind('. ')
    if last_period > max_len * 0.4:  # Only if we keep at least 40% of content
        return truncated[:last_period + 1]
    
    # Fall back to last word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.5:
        return truncated[:last_space]
    
    # Hard cut (very rare — would need 1500+ char word)
    return truncated


def _generate_title_and_seo(article_html: str, specs: dict) -> dict:
    """
    Generate an engaging title and SEO description using a lightweight AI call.
    
    This runs AFTER article generation, so the AI can pick the most impressive
    fact from the completed article for the title hook.
    
    Returns: {'title': str, 'seo_description': str} or None on failure.
    """
    try:
        from ai_engine.modules.ai_provider import get_generate_provider
    except ImportError:
        from modules.ai_provider import get_generate_provider
    
    # Extract key specs for the prompt
    make = specs.get('make', '')
    model = specs.get('model', '')
    year = specs.get('year', '')
    trim = specs.get('trim', '')
    hp = specs.get('horsepower', '')
    price = specs.get('price', '')
    range_val = specs.get('range', '')
    
    if not make or make == 'Not specified' or not model or model == 'Not specified':
        print("⚠️ Cannot generate AI title: missing make/model")
        return None
    
    # Format specs nicely
    year_str = f"{year} " if year else ""
    trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
    hp_str = f" • {hp}" if hp else ""
    price_str = f" • {price}" if price else ""
    range_str = f" • {range_val}" if range_val else ""
    
    # Prepare preview
    article_preview = _truncate_summary(article_html, max_len=4000)
    
    prompt = f"""Generate a TITLE, SEO DESCRIPTION, and SUMMARY for this car article.

CAR: {year_str}{make} {model}{trim_str}
KEY SPECS: {hp_str}{price_str}{range_str}

ARTICLE PREVIEW:
{article_preview}

═══ TITLE RULES ═══
- LENGTH: 50-90 characters (STRICT — count carefully)
- FORMAT: "[Year] [Brand] [Model]: [Engaging hook with standout spec or price]"

═══ SEO DESCRIPTION RULES ═══  
- LENGTH: STRICTLY 150-160 CHARACTERS (letters, not words!). This is usually 20-25 words.
- MUST include: car name, standout specs, and a reason to click.
- Include numbers if possible: price, range, horsepower, 0-100 time.

═══ SUMMARY RULES ═══
- LENGTH: STRICTLY 150-200 CHARACTERS (2-3 sentences).
- Used on article cards, social previews, and listing pages.
- Include the car name and its most impressive spec or selling point.
- Must be a complete, engaging sentence — NOT truncated mid-word.
- Do NOT write a long essay. Just 2-3 punchy sentences.

═══ OUTPUT FORMAT (strict) ═══
TITLE: [your title here]
SEO_DESCRIPTION: [your description here, STRICTLY 150-160 chars]
SUMMARY: [your 150-200 char summary here]
"""

    try:
        ai = get_generate_provider()
        result = ai.generate_completion(
            prompt=prompt,
            system_prompt="You are a senior automotive SEO specialist and editor. Generate concise, high-quality metadata.",
            temperature=0.7,
            max_tokens=2500,
            caller='title_seo'
        )

        
        if not result:
            return None
        
        # Parse the response
        title = None
        seo_desc = None
        
        title_match = re.search(r'TITLE:\s*(.+?)(?=\nSEO_DESCRIPTION:|\nSUMMARY:|$)', result, re.IGNORECASE | re.DOTALL)
        seo_match = re.search(r'SEO_?DESCRIPTION:\s*(.+?)(?=\nSUMMARY:|\nTITLE:|$)', result, re.IGNORECASE | re.DOTALL)
        summary_match = re.search(r'SUMMARY:\s*(.+?)(?=\nSEO_DESCRIPTION:|\nTITLE:|$)', result, re.IGNORECASE | re.DOTALL)
        
        title = title_match.group(1).strip().strip('"').strip("'") if title_match else None
        seo_desc = seo_match.group(1).strip().strip('"').strip("'") if seo_match else None
        summary = summary_match.group(1).strip().strip('"').strip("'") if summary_match else None
        
        if seo_desc:
            seo_desc = seo_desc.replace('\n', ' ')
        
        # Validate title
        if title:
            title = title.strip('"').strip("'")
            if len(title) < 20 or len(title) > 120:
                print(f"⚠️ AI title rejected (length {len(title)}): {title}")
                title = None
            elif title.lower().endswith(('review', 'review & specs', 'range & specs')):
                print(f"⚠️ AI title rejected (generic suffix): {title}")
                title = None
        
        # Validate SEO description
        if seo_desc:
            seo_desc = seo_desc.strip('"').strip("'")
            if len(seo_desc) < 80:
                print(f"⚠️ AI SEO description rejected (too short: {len(seo_desc)}): {seo_desc}")
                seo_desc = None
            elif len(seo_desc) > 160:
                # Strategy 1: Cut at last sentence boundary (period + space) within 160
                candidate = seo_desc[:160]
                last_period = candidate.rfind('. ')
                last_period_end = candidate.rfind('.')  # period at very end
                if last_period > 80:
                    seo_desc = candidate[:last_period + 1]
                elif last_period_end > 80 and last_period_end == len(candidate) - 1:
                    seo_desc = candidate[:last_period_end + 1]
                else:
                    # Strategy 2: cut at last word boundary, add ellipsis
                    seo_desc = candidate[:157].rsplit(' ', 1)[0]
                    if not seo_desc.endswith('.'):
                        seo_desc += '...'
                print(f"⚠️ SEO desc truncated to {len(seo_desc)} chars: {seo_desc[:60]}…")
            # Fix truncated endings: dangling numbers, prices, specs, or
            # incomplete phrases (e.g. "...and a blistering 2." or "...starting from $")
            if seo_desc and re.search(r'[\s,](\$?\d{1,3}|[a-z]{1,3})[.!]?$', seo_desc):
                last_period = seo_desc.rfind('. ')
                if last_period > 60:
                    seo_desc = seo_desc[:last_period + 1]
                    print(f"⚠️ SEO desc trimmed (dangling fragment): {seo_desc}")

        
        # Validate summary
        if summary:
            summary = summary.strip('"').strip("'").replace('\n', ' ')
            # Newline replacement can expand length — re-strip
            summary = re.sub(r'\s+', ' ', summary).strip()
            # Reject garbage summaries about transcript errors
            _summary_garbage = ['captcha', 'error page', 'could not be extracted',
                                'automated query', 'no specifications', 'consequently',
                                'rather than', 'not the actual', 'provided text']
            if any(g in summary.lower() for g in _summary_garbage):
                print(f"⚠️ AI summary rejected (garbage): {summary[:60]}")
                summary = None
            elif len(summary) < 80:
                print(f"⚠️ AI summary rejected (too short: {len(summary)}): {summary}")
                summary = None
            elif len(summary) > 200:
                # Truncate at sentence boundary
                truncated = summary[:200]
                last_period = truncated.rfind('. ')
                if last_period > 100:
                    summary = truncated[:last_period + 1]
                else:
                    summary = truncated.rsplit(' ', 1)[0]
                    if not summary.endswith('.'):
                        summary += '...'
                print(f"⚠️ AI summary truncated to {len(summary)} chars")

        if title or seo_desc or summary:
            return {'title': title, 'seo_description': seo_desc, 'summary': summary}
        
        return None
        
    except Exception as e:
        print(f"⚠️ _generate_title_and_seo failed: {e}")
        return None
