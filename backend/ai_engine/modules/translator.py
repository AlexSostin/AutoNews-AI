"""
Translate & Enhance Module
Translates Russian text to English and formats it as a professional HTML article.
"""
import re
import os

try:
    from ai_engine.modules.ai_provider import get_ai_provider
    from ai_engine.modules.utils import calculate_reading_time, validate_article_quality
except ImportError:
    from modules.ai_provider import get_ai_provider
    from modules.utils import calculate_reading_time, validate_article_quality


# Length presets (approximate word counts)
LENGTH_PRESETS = {
    'short': {'words': '400-600', 'max_tokens': 2000},
    'medium': {'words': '800-1200', 'max_tokens': 3500},
    'long': {'words': '1500-2000', 'max_tokens': 5000},
}

# Tone descriptions for the AI
TONE_DESCRIPTIONS = {
    'professional': 'Write in a professional, authoritative automotive journalism style. Use formal language and industry terminology.',
    'casual': 'Write in a friendly, conversational tone. Make it engaging and easy to read for a general audience.',
    'technical': 'Write in a detailed, technical style. Include precise specifications, engineering details, and data-driven analysis.',
}


def translate_and_enhance(
    russian_text: str,
    category: str = 'News',
    target_length: str = 'medium',
    tone: str = 'professional',
    seo_keywords: str = '',
    provider: str = 'gemini',
) -> dict:
    """
    Translates Russian text to English and creates a professional HTML article.

    Args:
        russian_text: Source text in Russian (can be a few sentences or paragraphs)
        category: Article category (EVs, News, Reviews, Technology, Luxury)
        target_length: 'short', 'medium', or 'long'
        tone: 'professional', 'casual', or 'technical'
        seo_keywords: Comma-separated SEO keywords (optional)
        provider: AI provider - 'gemini' or 'groq'

    Returns:
        dict with keys: title, content, summary, meta_description, suggested_slug,
                        suggested_categories, reading_time, seo_keywords
    """
    provider_display = 'Groq' if provider == 'groq' else 'Google Gemini'
    print(f'🌐 Translating & enhancing with {provider_display}...')

    # Get length and tone settings
    length_config = LENGTH_PRESETS.get(target_length, LENGTH_PRESETS['medium'])
    tone_desc = TONE_DESCRIPTIONS.get(tone, TONE_DESCRIPTIONS['professional'])

    # Build SEO keywords instruction
    seo_section = ''
    if seo_keywords.strip():
        seo_section = f"""
SEO KEYWORDS TO INCLUDE NATURALLY:
{seo_keywords}
Ensure these keywords appear naturally throughout the article (in headings, paragraphs, and meta description).
"""

    prompt = f"""
You are a professional automotive journalist and translator. Your task is to:
1. Translate the following Russian text into fluent, natural English
2. Expand it into a complete, well-structured HTML article
3. Optimize it for SEO

RUSSIAN SOURCE TEXT:
---
{russian_text}
---

ARTICLE REQUIREMENTS:

TONE: {tone_desc}

TARGET LENGTH: {length_config['words']} words

CATEGORY: {category}

{seo_section}

OUTPUT FORMAT - Return a JSON object (and NOTHING else) with these fields:
{{
  "title": "Engaging, SEO-optimized title with year/brand/model if applicable (plain text, no HTML)",
  "content": "Full HTML article content (use <h2>, <p>, <ul>, <li>, <strong> etc.)",
  "summary": "2-3 sentence article summary for preview cards (plain text)",
  "meta_description": "SEO meta description, 150-160 characters (plain text)",
  "suggested_slug": "url-friendly-slug-like-this",
  "suggested_categories": ["category1", "category2"],
  "seo_keywords": ["keyword1", "keyword2", "keyword3"]
}}

HTML CONTENT STRUCTURE (for the "content" field):
- Start with an engaging introduction paragraph (2-3 sentences)
- Use <h2> for section headings
- Use <p> for paragraphs
- Use <ul>/<li> for lists
- Use <strong> for emphasis
- Include specific numbers, data, and comparisons
- If the text is about a specific car model, include:
  * Performance & Specs section
  * Design & Features section
  * Market Availability & Pricing section
  * Pros & Cons section (using <h3> and <ul>/<li>)
- End with a conclusion paragraph

CRITICAL RULES:
1. Do NOT copy the Russian text - translate and ENHANCE it
2. Add context, comparisons, and analysis beyond the source material
3. Ensure the English reads naturally (not like a translation)
4. Fix any factual inconsistencies in the source
5. NO <html>, <head>, or <body> tags in content
6. NO "Advertisement", "Sponsor", or placeholder blocks
7. Make the title engaging and click-worthy
8. The meta_description must be 150-160 characters
9. Output ONLY the JSON object, nothing else
"""

    system_prompt = (
        'You are a bilingual (Russian/English) automotive journalist. '
        'You translate and enhance Russian automotive content into professional '
        'English articles. Always output valid JSON only.'
    )

    try:
        ai = get_ai_provider(provider)
        raw_response = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=length_config['max_tokens'],
        )

        if not raw_response:
            raise Exception(f'{provider_display} returned empty response')

        # Parse JSON from the response
        result = _parse_ai_response(raw_response)

        # Post-processing
        result['content'] = _clean_html(result.get('content', ''))
        result['reading_time'] = calculate_reading_time(result.get('content', ''))

        # Validate
        quality = validate_article_quality(result.get('content', ''))
        if not quality['valid']:
            print('⚠️  Quality issues:')
            for issue in quality['issues']:
                print(f'   - {issue}')

        print(f'✅ Translation complete! Title: {result.get("title", "N/A")}')
        print(f'📖 Reading time: ~{result.get("reading_time", "?")} min')
        print(f'📝 Content length: {len(result.get("content", ""))} chars')

        return result

    except Exception as e:
        print(f'❌ Translation error: {e}')
        raise


def _parse_ai_response(raw: str) -> dict:
    """Extract and parse JSON from raw AI response (may have markdown fences)."""
    import json

    # Remove markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        # Remove opening fence (```json or ```)
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        # Remove closing fence
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return a minimal result
    print('⚠️  Could not parse JSON from AI response, using fallback')
    return {
        'title': 'Article',
        'content': f'<p>{cleaned}</p>',
        'summary': cleaned[:200],
        'meta_description': cleaned[:160],
        'suggested_slug': 'article',
        'suggested_categories': [],
        'seo_keywords': [],
    }


def _clean_html(html: str) -> str:
    """Clean up generated HTML content."""
    if not html:
        return ''

    # Remove full document tags if accidentally included
    html = re.sub(r'</?(!DOCTYPE|html|head|body|meta)[^>]*>', '', html, flags=re.IGNORECASE)

    # Fix common issues
    html = html.replace('&amp;amp;', '&amp;')

    # Ensure proper list wrapping
    if '<li>' in html and '<ul>' not in html and '<ol>' not in html:
        html = html.replace('<li>', '<ul><li>', 1)
        last_li = html.rfind('</li>')
        if last_li != -1:
            html = html[:last_li + 5] + '</ul>' + html[last_li + 5:]

    return html.strip()
