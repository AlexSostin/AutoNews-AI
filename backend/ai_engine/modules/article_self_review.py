"""
AI self-review and verdict injection passes for generated articles.

Contains two AI-powered post-processing steps:
1. _self_review_pass: A second AI call where the model re-reads its article as a strict editor.
2. _ensure_verdict_written: Guarantees the FreshMotors Verdict section is present and complete.
"""
import re
import logging

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.ai_provider import get_ai_provider, get_light_provider
except ImportError:
    from modules.ai_provider import get_ai_provider, get_light_provider

from ai_engine.modules.html_normalizer import ensure_html_only


def _self_review_pass(html: str, analysis_data, provider: str = 'gemini') -> str:
    """
    Self-Review Pass (Layer 5): The same AI re-reads its article as a strict editor.
    Checks spec consistency, premium HTML structure, and overall quality.
    Returns the improved HTML, or the original if the review fails.
    """
    import time as _time

    start = _time.time()
    print("📝 Running AI Self-Review pass...")

    # Extract article plain text for context (truncated for token efficiency)
    plain_text = re.sub(r'<[^>]+>', ' ', html)
    word_count = len(plain_text.split())

    # Skip review for very short articles (press release stubs)
    if word_count < 400:
        print(f"  ⏭ Skipping review — article too short ({word_count} words)")
        return html

    review_prompt = f"""You are a STRICT senior editor at FreshMotors.com reviewing a draft article before publication.

YOUR TASK: Review and IMPROVE the article below. Return the COMPLETE improved HTML article.

ORIGINAL SOURCE DATA (use to verify accuracy):
{str(analysis_data)[:3000]}

DRAFT ARTICLE TO REVIEW:
{html}

═══════════════════════════════════════════════
EDITOR CHECKLIST — Fix ALL issues you find:
═══════════════════════════════════════════════

1. SPEC CONSISTENCY:
   - Do numbers in the spec-bar match the numbers in the body text?
   - Is the HP figure consistent throughout (intro, Performance section, spec-bar)?
   - Does the price match between price-tag, spec-bar, and Pricing section?
   - Are range figures consistent (same test cycle: WLTP/CLTC/EPA)?

2. PREMIUM HTML STRUCTURE (verify these exist and are correct):
   - <div class="spec-bar"> with spec-item/spec-label/spec-value — after intro paragraph
   - <div class="powertrain-specs"> with ps-item/ps-label/ps-val — inside Performance section
   - <div class="pros-cons"> with pc-block pros/cons and pc-list — for Pros & Cons
   - <div class="fm-verdict"> with verdict-label — for FreshMotors Verdict
   - <div class="price-tag"> with price-main/price-note — for price display
   - If "How It Compares" exists: <div class="compare-grid"> with compare-card
   - If any of these are missing or malformed → ADD or FIX them.

3. FACTUAL ACCURACY:
   - Cross-check key specs (HP, kW, range, battery, 0-100) against source data
   - If a spec in the article differs from source data → fix it to match source
   - If EREV/PHEV: verify range extender is NOT listed as total car power

4. READABILITY & QUALITY:
   - Fix any awkward or repetitive sentences
   - Ensure each section adds NEW information (no spec repetition)
   - Verify verdict is at least 60 words and contains a real opinion

5. BANNED PHRASE CHECK:
   - Remove any "While comprehensive driving review is pending"
   - Remove any "specs are still emerging" / "details under wraps"
   - Remove any sentence explaining what you DON'T know
   - Remove any "As a journalist" / "based on the transcript"

═══════════════════════════════════════════════
OUTPUT RULES:
═══════════════════════════════════════════════
- Return ONLY the complete improved HTML article
- Do NOT add commentary, notes, or explanations
- Do NOT wrap in ```html``` code blocks
- Do NOT add <html>/<head>/<body> tags
- Keep the same overall structure and sections
- Keep the <div class="alt-texts"> block at the end unchanged
- If the article is already good, return it unchanged (do NOT rewrite for no reason)
"""

    try:
        ai = get_ai_provider(provider)
        reviewed = ai.generate_completion(
            prompt=review_prompt,
            system_prompt="You are a meticulous automotive editor. Review and improve the article, then return the COMPLETE HTML. Make only necessary corrections — do not rewrite good content unnecessarily.",
            temperature=0.3,  # Low temp for precise editing
            max_tokens=16384,
            caller='article_review'
        )

        if not reviewed or len(reviewed) < 200:
            print(f"  ⚠️ Review returned empty/short response, keeping original")
            return html

        # Clean up the reviewed content
        reviewed = ensure_html_only(reviewed)

        # Sanity check: the reviewed version shouldn't be dramatically shorter
        reviewed_words = len(re.sub(r'<[^>]+>', ' ', reviewed).split())
        if reviewed_words < word_count * 0.85:
            print(f"  ⚠️ Review trimmed too aggressively ({reviewed_words} vs {word_count} words, >15% loss), keeping original")
            return html

        elapsed = round(_time.time() - start, 1)
        diff = reviewed_words - word_count
        diff_str = f"+{diff}" if diff >= 0 else str(diff)
        print(f"  ✅ Self-review complete in {elapsed}s ({reviewed_words} words, {diff_str} from original)")
        return reviewed

    except Exception as e:
        print(f"  ⚠️ Self-review failed (non-fatal): {e}")
        return html


def _ensure_verdict_written(html: str, analysis_data, provider: str = 'gemini') -> str:
    """
    Post-generation guarantee: if FreshMotors Verdict section is missing or empty,
    make a short targeted API call to write a proper verdict and inject it.
    
    Handles all Gemini output patterns:
    1. Proper <div class="fm-verdict"> with <p> content inside → check word count
    2. Empty <div class="fm-verdict"> + duplicate <h2>FreshMotors Verdict</h2> → strip both, regenerate
    3. Bare <h2>FreshMotors Verdict</h2> with truncated <p> → strip, regenerate
    4. No verdict at all → generate and append
    """

    # ── Step 1: Check for existing verdict content ────────────────────────
    # First check the fm-verdict div (the correct format)
    fm_verdict_match = re.search(
        r'<div\s+class="fm-verdict">\s*<div\s+class="verdict-label">.*?</div>\s*(.*?)</div>',
        html, re.IGNORECASE | re.DOTALL
    )
    
    verdict_text = ""
    if fm_verdict_match:
        verdict_text = re.sub(r'<[^>]+>', ' ', fm_verdict_match.group(1)).strip()
    
    # Also check for bare <h2>...Verdict...</h2> followed by content
    h2_verdict_match = re.search(
        r'(<h2[^>]*>[^<]*(?:verdict|conclusion|final)[^<]*</h2>)(.*?)(?=<h2|<div class="alt-texts"|<!-- Generated|$)',
        html, re.IGNORECASE | re.DOTALL
    )
    if h2_verdict_match and not verdict_text:
        verdict_text = re.sub(r'<[^>]+>', ' ', h2_verdict_match.group(2)).strip()
    
    verdict_words = len(verdict_text.split()) if verdict_text else 0
    
    if verdict_words >= 60:
        # Verdict is fine — but clean up any duplicate <h2> if fm-verdict div exists
        if fm_verdict_match and h2_verdict_match:
            html = html[:h2_verdict_match.start()] + html[h2_verdict_match.end():]
            print(f"  🧹 Cleaned duplicate verdict <h2> (fm-verdict div has {verdict_words} words)")
        return html
    
    print(f"  🔧 Verdict injector: {'found but only ' + str(verdict_words) + ' words' if verdict_words else 'missing'} — generating verdict...")

    # ── Step 2: Strip ALL existing verdict artifacts ──────────────────────
    # Remove orphaned/empty fm-verdict divs
    html = re.sub(
        r'<div\s+class="fm-verdict">\s*<div\s+class="verdict-label">.*?</div>\s*(?:<p>.*?</p>\s*)?</div>\s*',
        '', html, flags=re.IGNORECASE | re.DOTALL
    )
    # Remove bare <h2>...Verdict...</h2> + any trailing truncated <p>
    html = re.sub(
        r'<h2[^>]*>[^<]*(?:verdict|conclusion|final)[^<]*</h2>\s*(?:<p>.*?</p>\s*)*',
        '', html, flags=re.IGNORECASE | re.DOTALL
    )

    # ── Step 3: Generate verdict via AI ───────────────────────────────────
    article_text = re.sub(r'<[^>]+>', ' ', html)[:2500]

    verdict_prompt = f"""You are writing the final section of an automotive article for FreshMotors.com.

Here is the article so far (plain text summary):
{article_text}

Write ONLY the FreshMotors Verdict section — a single paragraph of 70-100 words.
Rules:
- Be specific and opinionated about WHO should buy this car and WHY
- Mention 1-2 real strengths (use specific specs from the article)  
- Mention 1 genuine weakness or caveat
- End with a clear recommendation
- Write in plain prose — NO bullet points, NO subheadings
- Output ONLY the verdict paragraph wrapped in <p> tags, nothing else
- Do NOT include the <h2>FreshMotors Verdict</h2> heading — just the paragraph

Example of good verdict:
<p>The VOYAH Taishan 1430 is the ultimate long-haul family SUV for buyers who want to leave range anxiety behind permanently. Its 1,430 km combined range and 350 km electric-only capability make it genuinely useful for both daily commutes and cross-country trips, while the Huawei-powered tech stack keeps it feeling premium throughout. The 2.8-ton curb weight is a real-world caveat, but for families prioritizing space and range over outright agility, this is a serious contender at its price point.</p>
"""

    def _inject_verdict(verdict_para):
        """Clean and inject verdict into the proper fm-verdict div structure."""
        nonlocal html
        verdict_para = verdict_para.strip()
        if not verdict_para.startswith('<p'):
            verdict_para = f'<p>{verdict_para}</p>'
        # Remove any heading the model might have added
        verdict_para = re.sub(r'<h2[^>]*>.*?</h2>', '', verdict_para, flags=re.IGNORECASE | re.DOTALL).strip()
        # Remove any fm-verdict wrapper the model might have added
        verdict_para = re.sub(r'<div[^>]*class="fm-verdict"[^>]*>.*?<div class="verdict-label">.*?</div>', '', verdict_para, flags=re.IGNORECASE | re.DOTALL).strip()
        verdict_para = re.sub(r'</div>\s*$', '', verdict_para).strip()

        verdict_block = (
            '<div class="fm-verdict">\n'
            '  <div class="verdict-label">FreshMotors Verdict</div>\n'
            f'  {verdict_para}\n'
            '</div>'
        )

        # Insert before alt-texts div, comment tag, or at the end
        alt_pos = html.find('<div class="alt-texts"')
        comment_pos = html.find('<!-- Generated')
        insert_pos = -1
        if alt_pos > 0:
            insert_pos = alt_pos
        elif comment_pos > 0:
            insert_pos = comment_pos
        
        if insert_pos > 0:
            html = html[:insert_pos] + verdict_block + '\n' + html[insert_pos:]
        else:
            html = html.rstrip() + '\n' + verdict_block

        verdict_word_count = len(verdict_para.split())
        print(f"  ✅ Verdict injected ({verdict_word_count} words)")
        if verdict_word_count < 60:
            print(f"  ⚠️ Verdict too short ({verdict_word_count} words < 60) — will regenerate")

    try:
        ai = get_light_provider()
        verdict_para = ai.generate_completion(
            prompt=verdict_prompt,
            system_prompt="You are a precise automotive journalist. Output only a single <p> paragraph as instructed.",
            temperature=0.7,
            max_tokens=300,
            caller='article_verdict'
        )
        if verdict_para:
            _inject_verdict(verdict_para)
    except Exception as e:
        print(f"  ⚠️ Verdict injector failed: {e}")
        try:
            print("  🔄 Retrying verdict with Gemini fallback...")
            fallback_ai = get_ai_provider('gemini')
            verdict_para = fallback_ai.generate_completion(
                prompt=verdict_prompt,
                system_prompt="You are a precise automotive journalist. Output only a single <p> paragraph as instructed.",
                temperature=0.7,
                max_tokens=300,
                caller='article_verdict_fallback'
            )
            if verdict_para:
                _inject_verdict(verdict_para)
        except Exception as fb_err:
            print(f"  ⚠️ Verdict fallback injector also failed: {fb_err}")

    return html
