"""
RLAIF Judge — AI evaluator for article quality before publishing.

Implements Reinforcement Learning from AI Feedback (RLAIF):
1. "Judge" AI model evaluates generated article on 5 dimensions
2. Returns structured JSON scores + specific improvement instructions
3. If score < threshold → article is sent for regeneration with feedback
4. Judge decisions are logged for future model improvement

Dimensions scored (each 1-10):
- accuracy:    Factual correctness, specs consistency
- engagement:  Compelling writing, hooks, storytelling
- completeness: Coverage of key specs, pros/cons, verdict
- seo_quality:  Heading structure, keyword usage, meta potential
- readability:  Flow, grammar, paragraph length, jargon balance
"""
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger('news')

# Default threshold for passing the judge
DEFAULT_MIN_SCORE = 6.0
MAX_REGENERATION_ATTEMPTS = 2


def judge_article(article_html: str, source_title: str = '',
                  specs: dict = None, provider: str = 'gemini') -> dict:
    """
    AI Judge evaluates article quality and returns structured scores.
    
    Args:
        article_html: Generated HTML content
        source_title: Original source title (for accuracy grounding)
        specs: Car specifications dict
        provider: AI provider for the judge (uses same as generator)
    
    Returns:
        {
            'overall_score': float (1-10),
            'dimensions': {
                'accuracy': {'score': int, 'feedback': str},
                'engagement': {'score': int, 'feedback': str},
                'completeness': {'score': int, 'feedback': str},
                'seo_quality': {'score': int, 'feedback': str},
                'readability': {'score': int, 'feedback': str},
            },
            'passed': bool,
            'critical_issues': [str],
            'improvement_suggestions': [str],
        }
    """
    try:
        try:
            from ai_engine.modules.ai_provider import get_ai_provider
        except ImportError:
            from modules.ai_provider import get_ai_provider
        
        ai = get_ai_provider(provider)
        
        # Build specs context
        specs_context = ""
        if specs:
            relevant_specs = {k: v for k, v in specs.items() 
                            if v and str(v) not in ('', 'Not specified', 'None', '0')}
            if relevant_specs:
                specs_context = f"\nKNOWN SPECS:\n{json.dumps(relevant_specs, indent=2)}"
        
        title_context = f"\nORIGINAL SOURCE TITLE: {source_title}" if source_title else ""
        
        system_prompt = """You are a senior automotive journalism editor and quality assessor.
Your role is to evaluate AI-generated car articles and provide structured feedback.
You must respond ONLY with valid JSON — no explanations, no markdown, just the JSON object."""

        judge_prompt = f"""Evaluate this automotive article and return a JSON quality assessment.
{title_context}
{specs_context}

ARTICLE TO EVALUATE:
{article_html[:6000]}

Rate each dimension from 1-10 and provide specific feedback. Return ONLY this JSON:
{{
    "accuracy": {{
        "score": <1-10>,
        "feedback": "<specific issues found or 'No issues detected'>"
    }},
    "engagement": {{
        "score": <1-10>,
        "feedback": "<what makes it engaging or what's missing>"
    }},
    "completeness": {{
        "score": <1-10>,
        "feedback": "<missing sections or well-covered areas>"
    }},
    "seo_quality": {{
        "score": <1-10>,
        "feedback": "<heading structure, keyword usage assessment>"
    }},
    "readability": {{
        "score": <1-10>,
        "feedback": "<grammar, flow, paragraph length issues>"
    }},
    "critical_issues": ["<list critical problems, or empty if none>"],
    "improvement_suggestions": ["<top 3 actionable improvements>"]
}}

SCORING GUIDE:
- 1-3: Major problems, should not publish
- 4-5: Below average, needs significant fixes
- 6-7: Acceptable, minor improvements needed
- 8-9: Good quality, publishable
- 10: Exceptional

Be CRITICAL but FAIR. Focus on specific, actionable feedback."""

        logger.info("🧑‍⚖️ RLAIF Judge: Evaluating article...")
        
        result = ai.generate_completion(
            prompt=judge_prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # Low temperature for consistent evaluation
            max_tokens=1500,
        )
        
        if not result:
            logger.warning("[RLAIF] Judge returned empty response, defaulting to pass")
            return _default_result(passed=True, reason="Judge unavailable")
        
        # Parse JSON response
        parsed = _parse_judge_response(result)
        
        if parsed is None:
            logger.warning("[RLAIF] Could not parse judge response, defaulting to pass")
            return _default_result(passed=True, reason="Parse error")
        
        # Calculate overall score (weighted average)
        dimensions = parsed.get('dimensions', {})
        weights = {
            'accuracy': 0.30,
            'engagement': 0.25,
            'completeness': 0.20,
            'seo_quality': 0.10,
            'readability': 0.15,
        }
        
        weighted_sum = sum(
            dimensions.get(dim, {}).get('score', 5) * weight
            for dim, weight in weights.items()
        )
        overall = round(weighted_sum, 1)
        
        result_dict = {
            'overall_score': overall,
            'dimensions': dimensions,
            'passed': overall >= DEFAULT_MIN_SCORE,
            'critical_issues': parsed.get('critical_issues', []),
            'improvement_suggestions': parsed.get('improvement_suggestions', []),
        }
        
        status = "✅ PASSED" if result_dict['passed'] else "❌ FAILED"
        logger.info(
            f"[RLAIF] {status}: {overall}/10 "
            f"(acc={dimensions.get('accuracy', {}).get('score', '?')}, "
            f"eng={dimensions.get('engagement', {}).get('score', '?')}, "
            f"comp={dimensions.get('completeness', {}).get('score', '?')}, "
            f"seo={dimensions.get('seo_quality', {}).get('score', '?')}, "
            f"read={dimensions.get('readability', {}).get('score', '?')})"
        )
        
        return result_dict
        
    except Exception as e:
        logger.error(f"[RLAIF] Judge failed: {e}")
        return _default_result(passed=True, reason=f"Error: {e}")


def judge_and_improve(article_html: str, source_title: str = '',
                      specs: dict = None, provider: str = 'gemini',
                      min_score: float = DEFAULT_MIN_SCORE) -> dict:
    """
    Full RLAIF loop: evaluate → improve → re-evaluate if needed.
    
    This is the main entry point for the generation pipeline.
    
    Returns:
        {
            'html': str,              # Final (possibly improved) HTML
            'judge_score': float,      # Final judge score
            'attempts': int,           # Number of attempts
            'improved': bool,          # Whether the article was improved
            'judge_result': dict,      # Full judge evaluation
        }
    """
    current_html = article_html
    best_html = article_html
    best_score = 0
    attempts = 0
    
    for attempt in range(1, MAX_REGENERATION_ATTEMPTS + 1):
        attempts = attempt
        
        # Judge the article
        judge_result = judge_article(
            current_html, source_title=source_title,
            specs=specs, provider=provider
        )
        
        score = judge_result['overall_score']
        
        # Track best version
        if score > best_score:
            best_score = score
            best_html = current_html
        
        # If passes, we're done
        if score >= min_score:
            logger.info(f"[RLAIF] Article passed on attempt {attempt}: {score}/10")
            return {
                'html': current_html,
                'judge_score': score,
                'attempts': attempts,
                'improved': attempts > 1,
                'judge_result': judge_result,
            }
        
        # If last attempt, return best version
        if attempt >= MAX_REGENERATION_ATTEMPTS:
            logger.warning(
                f"[RLAIF] Article did not pass after {attempts} attempts "
                f"(best: {best_score}/10). Returning best version."
            )
            break
        
        # Try to improve based on feedback
        logger.info(f"[RLAIF] Score {score}/10 < {min_score}. Attempting improvement...")
        improved = _improve_article(
            current_html, judge_result, specs, provider
        )
        
        if improved and improved != current_html:
            current_html = improved
        else:
            logger.warning("[RLAIF] Improvement produced no changes, stopping")
            break
    
    return {
        'html': best_html,
        'judge_score': best_score,
        'attempts': attempts,
        'improved': best_html != article_html,
        'judge_result': judge_result,
    }


def _improve_article(article_html: str, judge_result: dict,
                     specs: dict = None, provider: str = 'gemini') -> str:
    """
    Improve article based on judge feedback.
    """
    try:
        try:
            from ai_engine.modules.ai_provider import get_ai_provider
        except ImportError:
            from modules.ai_provider import get_ai_provider
        
        ai = get_ai_provider(provider)
        
        # Build improvement instructions from judge feedback
        issues = judge_result.get('critical_issues', [])
        suggestions = judge_result.get('improvement_suggestions', [])
        dimensions = judge_result.get('dimensions', {})
        
        # Focus on lowest-scoring dimensions
        low_dims = sorted(
            dimensions.items(),
            key=lambda x: x[1].get('score', 10) if isinstance(x[1], dict) else 10
        )[:3]
        
        fix_instructions = []
        for dim_name, dim_data in low_dims:
            if isinstance(dim_data, dict) and dim_data.get('score', 10) < 7:
                fix_instructions.append(
                    f"- {dim_name.upper()}: {dim_data.get('feedback', 'Improve this area')}"
                )
        
        if issues:
            fix_instructions.extend([f"- CRITICAL: {issue}" for issue in issues[:3]])
        if suggestions:
            fix_instructions.extend([f"- IMPROVE: {s}" for s in suggestions[:3]])
        
        if not fix_instructions:
            return article_html  # Nothing specific to fix
        
        improvement_prompt = f"""Improve this automotive article based on the following feedback.

FEEDBACK & REQUIRED FIXES:
{chr(10).join(fix_instructions)}

ARTICLE TO IMPROVE:
{article_html}

RULES:
1. Return ONLY the corrected HTML. No explanations.
2. Keep the same HTML structure (h2, h3, p, ul, li tags).
3. Focus on the specific issues mentioned above.
4. Do NOT shorten the article significantly.
5. Start with <h2> tag.
"""
        
        result = ai.generate_completion(
            prompt=improvement_prompt,
            system_prompt="You are an expert automotive editor. Fix the specific issues mentioned. Return only HTML.",
            temperature=0.3,
            max_tokens=4000,
        )
        
        if not result or len(result.strip()) < 100:
            return article_html
        
        # Clean response
        cleaned = re.sub(r'^```(?:html)?\n?', '', result.strip())
        cleaned = re.sub(r'\n?```$', '', cleaned)
        
        # Sanity check
        if '<h2>' not in cleaned and '<p>' not in cleaned:
            return article_html
        if len(cleaned) < len(article_html) * 0.5:
            return article_html
        
        logger.info(
            f"[RLAIF] Article improved: {len(article_html)} → {len(cleaned)} chars"
        )
        return cleaned
        
    except Exception as e:
        logger.error(f"[RLAIF] Improvement failed: {e}")
        return article_html


def _parse_judge_response(response: str) -> dict:
    """Parse the JSON response from the judge AI."""
    try:
        # Try direct JSON parse
        cleaned = response.strip()
        
        # Remove markdown code fences if present
        cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
        
        # Find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            data = json.loads(json_match.group())
        else:
            return None
        
        # Normalize structure
        dimensions = {}
        for dim in ['accuracy', 'engagement', 'completeness', 'seo_quality', 'readability']:
            if dim in data:
                dim_data = data[dim]
                if isinstance(dim_data, dict):
                    dimensions[dim] = {
                        'score': max(1, min(10, int(dim_data.get('score', 5)))),
                        'feedback': str(dim_data.get('feedback', '')),
                    }
                elif isinstance(dim_data, (int, float)):
                    dimensions[dim] = {'score': max(1, min(10, int(dim_data))), 'feedback': ''}
        
        return {
            'dimensions': dimensions,
            'critical_issues': data.get('critical_issues', []),
            'improvement_suggestions': data.get('improvement_suggestions', []),
        }
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"[RLAIF] Failed to parse judge response: {e}")
        return None


def _default_result(passed=True, reason='') -> dict:
    """Return a default result when judge is unavailable."""
    return {
        'overall_score': 5.0 if passed else 3.0,
        'dimensions': {
            dim: {'score': 5, 'feedback': reason}
            for dim in ['accuracy', 'engagement', 'completeness', 'seo_quality', 'readability']
        },
        'passed': passed,
        'critical_issues': [],
        'improvement_suggestions': [],
    }


# ──────────────────────────────────────────────
# Decision Logging (for future training)
# ──────────────────────────────────────────────

def log_judge_decision(article_id: int, judge_result: dict, 
                       final_engagement: float = None):
    """
    Log a judge decision for future RLAIF model training.
    
    Stores the judge's prediction alongside eventual reader engagement,
    enabling calibration of the judge over time.
    """
    import os
    
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data'
    )
    log_file = os.path.join(log_dir, 'rlaif_decisions.jsonl')
    
    os.makedirs(log_dir, exist_ok=True)
    
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'article_id': article_id,
        'judge_score': judge_result.get('overall_score', 0),
        'dimensions': {
            k: v.get('score', 0) if isinstance(v, dict) else v
            for k, v in judge_result.get('dimensions', {}).items()
        },
        'passed': judge_result.get('passed', True),
        'critical_issues_count': len(judge_result.get('critical_issues', [])),
        'final_engagement': final_engagement,
    }
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        logger.debug(f"[RLAIF] Decision logged for article #{article_id}")
    except Exception as e:
        logger.warning(f"[RLAIF] Failed to log decision: {e}")
