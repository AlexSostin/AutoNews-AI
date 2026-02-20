"""
Spec Refill Module — AI-powered gap filler for low-coverage specs.

After initial spec extraction and web enrichment, checks if coverage
is below 70%. If so, makes a focused AI call to fill ONLY the missing fields.
"""
import json
import logging

logger = logging.getLogger(__name__)

# The 10 key fields we consider for coverage
KEY_SPEC_FIELDS = [
    'make', 'model', 'engine', 'horsepower', 'torque',
    'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'year',
]


def _is_filled(value) -> bool:
    """Check if a spec value is meaningfully filled."""
    if value is None:
        return False
    s = str(value).strip()
    return s not in ('', 'Not specified', 'None', '0', 'null')


def compute_coverage(specs: dict) -> tuple:
    """
    Compute spec coverage.
    
    Returns:
        (filled_count, total_count, coverage_pct, missing_fields)
    """
    if not specs:
        return 0, len(KEY_SPEC_FIELDS), 0.0, list(KEY_SPEC_FIELDS)
    
    missing = []
    filled = 0
    for field in KEY_SPEC_FIELDS:
        if _is_filled(specs.get(field)):
            filled += 1
        else:
            missing.append(field)
    
    total = len(KEY_SPEC_FIELDS)
    pct = (filled / total) * 100 if total > 0 else 0.0
    return filled, total, pct, missing


def refill_missing_specs(specs: dict, article_content: str,
                         web_context: str = '', provider: str = 'gemini',
                         threshold: float = 70.0) -> dict:
    """
    Check spec coverage and AI-fill missing fields if below threshold.
    
    Args:
        specs: dict from extract_specs_dict (may have 'Not specified' gaps)
        article_content: the generated HTML article
        web_context: raw text from web search
        provider: AI provider name
        threshold: coverage % below which refill triggers (default 70%)
    
    Returns:
        Updated specs dict with `_refill_meta` key showing what was done
    """
    filled, total, coverage, missing = compute_coverage(specs)
    
    meta = {
        'triggered': False,
        'coverage_before': round(coverage, 1),
        'filled_before': filled,
        'missing_before': missing[:],
    }
    
    if coverage >= threshold:
        logger.info(f"[SPEC-REFILL] Coverage {coverage:.0f}% ≥ {threshold}% — skip")
        meta['reason'] = 'coverage_sufficient'
        specs['_refill_meta'] = meta
        return specs
    
    logger.info(f"[SPEC-REFILL] Coverage {coverage:.0f}% < {threshold}% — refilling {len(missing)} fields")
    meta['triggered'] = True
    
    # Build focused prompt
    make = specs.get('make', 'unknown')
    model = specs.get('model', 'unknown')
    
    # Context: article + web search results
    context_parts = []
    if article_content:
        # Use first 3000 chars of article to stay within token budget
        clean_article = article_content[:3000]
        context_parts.append(f"Article content:\n{clean_article}")
    if web_context:
        context_parts.append(f"Web search results:\n{web_context[:2000]}")
    
    context = '\n\n'.join(context_parts)
    
    field_descriptions = {
        'make': 'car manufacturer brand name (e.g. Toyota, BMW, BYD)',
        'model': 'specific model name (e.g. Camry, X5, Seal)',
        'engine': 'engine type/description (e.g. "2.5L 4-cylinder turbo", "dual electric motors")',
        'horsepower': 'peak power in HP (number only)',
        'torque': 'peak torque (e.g. "350 lb-ft" or "475 Nm")',
        'zero_to_sixty': '0-60 mph time in seconds (e.g. "5.2")',
        'top_speed': 'top speed (e.g. "155 mph" or "250 km/h")',
        'drivetrain': 'AWD, FWD, RWD, or 4WD',
        'price': 'starting price with currency (e.g. "$35,000", "€42,900")',
        'year': 'model year (e.g. 2025, 2026)',
    }
    
    missing_desc = '\n'.join(
        f'- {f}: {field_descriptions.get(f, f)}'
        for f in missing
    )
    
    prompt = f"""You are an automotive specifications expert. I have an article about the {make} {model}.

The following specification fields are MISSING. Extract them from the context below.
If a value is truly not mentioned anywhere, use "Not specified".

Missing fields:
{missing_desc}

{context}

Reply with ONLY valid JSON containing the missing field names as keys and their values as strings.
Example: {{"horsepower": "320", "drivetrain": "AWD"}}
No extra text, no markdown, just the JSON object."""

    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        ai = get_ai_provider(provider)
        
        response = ai.generate_completion(
            prompt=prompt,
            temperature=0.2,
            max_tokens=500,
        )
        
        # Parse response
        response_text = response.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        refill_data = json.loads(response_text)
        
        # Merge into specs
        filled_by_refill = []
        for field in missing:
            value = refill_data.get(field)
            if value and str(value).strip() not in ('', 'Not specified', 'None', 'null'):
                specs[field] = str(value).strip()
                filled_by_refill.append(field)
                logger.info(f"[SPEC-REFILL] ✓ {field} = {value}")
        
        # Compute new coverage
        _, _, coverage_after, missing_after = compute_coverage(specs)
        
        meta['filled_by_refill'] = filled_by_refill
        meta['coverage_after'] = round(coverage_after, 1)
        meta['missing_after'] = missing_after
        meta['provider'] = provider
        
        logger.info(f"[SPEC-REFILL] Coverage: {coverage:.0f}% → {coverage_after:.0f}% "
                     f"(+{len(filled_by_refill)} fields)")
        
    except json.JSONDecodeError as e:
        logger.warning(f"[SPEC-REFILL] JSON parse error: {e}")
        meta['error'] = f'json_parse: {e}'
    except Exception as e:
        logger.warning(f"[SPEC-REFILL] Failed: {e}")
        meta['error'] = str(e)
    
    specs['_refill_meta'] = meta
    return specs
