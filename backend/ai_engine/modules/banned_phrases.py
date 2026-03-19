"""
Banned phrase patterns and cleanup for AI-generated automotive articles.

Gemini sometimes ignores prompt-level bans. This module is the safety net
that removes or replaces filler phrases, source leaks, and AI clichés
in post-processing.
"""
import re
import logging

logger = logging.getLogger(__name__)


# ── Banned phrase post-processing ──────────────────────────────────────────
# Gemini sometimes ignores prompt bans.  This is the safety net.

_BANNED_SENTENCE_PATTERNS = re.compile(
    r'<(?:p|li)>[^<]*?('
    r'While a comprehensive driving review is pending'
    r'|While I haven\'t personally driven'
    r'|some assumptions can be made'
    r'|specific .{3,30} figures are still emerging'
    r'|specific .{3,30} figures are not available'
    r'|specific .{3,30} figures .{3,30} not .{3,30} released'
    r'|horsepower and torque figures are not specified'
    r'|exact battery capacity is not specified'
    r'|further details .{3,30} will be released'
    r'|pricing details .{3,30} have not been officially announced'
    r'|details .{3,30} are .{0,20}under wraps'
    r'|details .{3,30} are .{0,20}currently confidential'
    r'|details .{3,30} are yet to be .{3,30} detailed'
    r'|I wish I could dive'
    r'|the truth is, .{3,50} not .{3,30} released'
    r'|without official confirmation'
    r'|without concrete information'
    r'|we cannot .{3,30} any specific'
    r'|we can\'t speak to the'
    r'|information .{3,30} currently unavailable'
    r'|have not yet been officially released'
    r'|are currently confidential'
    r'|we\'d anticipate'
    r'|it\'s reasonable to expect'
    # Filler openers
    r'|isn\'t just another'
    r'|isn\'t just dipping'
    r'|isn\'t merely another'
    r'|this isn\'t your typical'
    r'|this isn\'t your average'
    # AI filler
    r'|a compelling proposition'
    r'|a compelling package'
    r'|for the discerning'
    r'|effectively eliminat(?:ing|es?) range anxiety'
    r'|in the evolving landscape'
    r'|prioritizing .{3,30} and .{3,30} comfort'
    r'|central to .{3,40} identity'
    # Lazy Cons
    r'|While specific cons .{3,60} aren\'t detailed'
    r'|While specific cons .{3,60} not .{3,30} detailed'
    # Cons about missing specs (NOT real cons)
    r'|[Ss]pecific .{3,60} (?:is |are )not (?:yet )?(?:detailed|public|available|confirmed|released)'
    r'|[Dd]etailed .{3,60} (?:is |are |have )not (?:been )?(?:publicly )?(?:available|released|detailed|confirmed)'
    r'|[Ee]xact .{3,40} (?:is |are )not (?:yet )?confirmed'
    r'|has not yet been officially announced'
    r'|details remain .{3,20} to be .{3,20} confirmed'
    r'|specifics have yet to be .{3,20} disclosed'
    r'|the complexity inherent in'
    r'|might be a consideration for some buyers'
    # Empty "still emerging" paragraphs
    r'|are still emerging'
    r'|remain to be seen'
    r'|only time will tell'
    r'|it remains to be seen'
    # Conversational filler paragraphs
    r'|this is where .{3,40} truly shines'
    r'|this is where .{3,40} really shines'
    r'|this is where things get .{3,20} interesting'
    ')[^<]*?</(?:p|li)>',
    re.IGNORECASE
)

_BANNED_INLINE_REPLACEMENTS = [
    # (pattern, replacement)
    (re.compile(r'is making waves (?:as |in )', re.I), 'is positioned as '),
    (re.compile(r'making waves in the .{3,30} segment', re.I), 'competing in this segment'),
    (re.compile(r'setting a new benchmark', re.I), 'raising the bar'),
    (re.compile(r'a hefty amount of torque', re.I), 'strong torque'),
    (re.compile(r'expected to be equipped', re.I), 'equipped'),
    (re.compile(r'anticipated to be a key component', re.I), 'a key component'),
    (re.compile(r'potentially with', re.I), 'with'),
    (re.compile(r'likely running', re.I), 'running'),
    (re.compile(r'is expected to feature', re.I), 'features'),
    (re.compile(r'it\'s reasonable to expect', re.I), 'we expect'),
    (re.compile(r'we can expect', re.I), 'expect'),
    (re.compile(r'we\'d anticipate', re.I), 'we expect'),
    (re.compile(r'As a journalist, I wish I could[^.]*\.\s*', re.I), ''),
    (re.compile(r'However, the truth is,?\s*', re.I), ''),
    (re.compile(r'details .{3,30} under wraps', re.I), 'details pending'),
    # Filler clichés
    (re.compile(r'isn\'t just dipping (?:its|their) toes[^.]*[.;]\s*', re.I), ''),
    (re.compile(r'they\'re cannonballing in[^.]*[.;]\s*', re.I), ''),
    (re.compile(r'nothing short of phenomenal[^.]*[.;]?', re.I), 'strong'),
    (re.compile(r'has been nothing short of', re.I), 'has been'),
    (re.compile(r'a prime example of .{3,40} strategy', re.I), 'a clear strategic move'),
    (re.compile(r'Not content to rest on (?:its|their) laurels,?\s*', re.I), ''),
    # AI-typical filler
    (re.compile(r'commanding (?:road |on-road )?presence', re.I), 'strong visual impact'),
    (re.compile(r'prioritiz(?:ing|es?) (?:both )?comfort and', re.I), 'balancing comfort and'),
    (re.compile(r'generous dimensions', re.I), 'large dimensions'),
    (re.compile(r'the market response has been .{3,30}phenomenal:?\s*', re.I), 'Market response: '),
    (re.compile(r'it\'s clear (?:that )?', re.I), ''),
    # Round 3: AITO M9 article filler
    (re.compile(r',? which is quite brisk(?:\s+for .{3,30})?', re.I), ''),
    (re.compile(r',? which sounds absolutely \w+', re.I), ''),
    (re.compile(r'\bWell, ', re.I), ''),
    (re.compile(r'for a touch of futuristic flair,?\s*', re.I), ''),
    (re.compile(r'for those wanting to stand out,?\s*', re.I), ''),
    (re.compile(r'for those (?:who|looking)\s+(?:want|prefer)\s+(?:to )?stand out,?\s*', re.I), ''),
    (re.compile(r'\bplus, for a touch of\b', re.I), 'Additionally, for'),
    (re.compile(r'(?:the )?real party trick (?:here )?is', re.I), 'The key figure is'),
    (re.compile(r'doing its thing,?\s*', re.I), 'working, '),
    (re.compile(r'a testament to its appeal', re.I), 'a sign of strong demand'),
    (re.compile(r'(?:Its|The) rapid ascent to a top.selling position[^.]*\.\s*', re.I), ''),
    # Clickbait / hype tone
    (re.compile(r'Hold on to your hats,?\s*(?:folks,?\s*)?(?:because\s*)?', re.I), ''),
    (re.compile(r'Buckle up,?\s*(?:folks,?\s*)?(?:because\s*)?', re.I), ''),
    (re.compile(r'Fasten your seatbelts,?\s*(?:because\s*)?', re.I), ''),
    (re.compile(r'(?:is|are)\s+(?:at it|back at it)\s+again,?\s*', re.I), ''),
    (re.compile(r'dropping\s+(?:another\s+)?bombshell(?:s)?', re.I), 'releasing'),
    (re.compile(r'eye[\s-]?watering', re.I), 'competitive'),
    (re.compile(r'jaw[\s-]?dropping', re.I), 'impressive'),
    (re.compile(r'mind[\s-]?blowing', re.I), 'notable'),
    (re.compile(r'game[\s-]?chang(?:ing|er)', re.I), 'significant'),
    (re.compile(r'this thing is set to make a serious splash', re.I), 'this model enters a competitive segment'),
    (re.compile(r'is here to shake up', re.I), 'targets'),
    (re.compile(r'forget (?:everything you knew about |about )?(?:range )?anxiety,?\s*', re.I), ''),
    (re.compile(r',?\s*folks\b', re.I), ''),
    # Round 4: BYD Sealion article filler (2026-03-08)
    (re.compile(r'in the burgeoning .{3,30} market', re.I), 'in this market segment'),
    (re.compile(r'a significant contender', re.I), 'a strong option'),
    (re.compile(r'aiming to blend .{3,40},', re.I), 'combining'),
    (re.compile(r'without the premium price tag', re.I), 'at a lower cost'),
    (re.compile(r'brisk acceleration', re.I), 'quick acceleration'),
    (re.compile(r'reduces? range anxiety', re.I), 'provides sufficient range'),
    (re.compile(r'a compelling (?:option|choice|proposition|package)', re.I), 'a strong choice'),
    (re.compile(r'a key player in', re.I), 'an important model in'),
    (re.compile(r'further enhancing its credentials', re.I), 'additionally'),
    (re.compile(r'contribut(?:ing|es?) to (?:a|the) (?:modern|premium) (?:and (?:premium|modern) )?appearance', re.I), 'adds to the design'),
    # Round 5: AdSense anti-AI-cliché cleanup (2026-03-16)
    (re.compile(r'(?:a\s+)?paradigm\s+shift', re.I), 'a major change'),
    (re.compile(r'(?:a\s+)?tour\s+de\s+force', re.I), 'an impressive achievement'),
    (re.compile(r'(?:a\s+)?technological\s+tour\s+de\s+force', re.I), 'a strong technical achievement'),
    (re.compile(r'(?:a\s+)?technological\s+marvel', re.I), 'a well-engineered vehicle'),
    (re.compile(r'(?:a\s+)?game[\s-]chang(?:ing|er)\s+(?:in\s+)?(?:the\s+)?', re.I), 'notable in '),
    (re.compile(r'disruptive\s+price', re.I), 'competitive price'),
    (re.compile(r'disrupt(?:ing|s?)\s+the\s+(?:market|segment|industry)', re.I), 'entering this market'),
    (re.compile(r'redefin(?:ing|es?)\s+(?:the|what)', re.I), 'expanding'),
    (re.compile(r'push(?:ing|es?)\s+the\s+(?:boundaries|envelope)', re.I), 'advancing'),
    (re.compile(r'(?:a\s+)?breath\s+of\s+fresh\s+air', re.I), 'a welcome addition'),
    (re.compile(r'(?:a\s+)?masterpiece', re.I), 'a well-executed model'),
    (re.compile(r'without\s+(?:further\s+)?ado', re.I), ''),
    (re.compile(r'let\'s\s+dive\s+(?:right\s+)?in', re.I), ''),
    (re.compile(r'(?:truly|undeniably)\s+(?:a\s+)?(?:remarkable|exceptional|extraordinary)', re.I), 'notable'),
    # Mid-sentence "While X not specified/detailed, Y" → keep only Y
    (re.compile(r'While\s+(?:the\s+)?(?:exact|specific|precise|detailed)\s+[^,]{5,80}(?:are|is|were)\s+not\s+(?:specified|provided|detailed|disclosed|confirmed|available|announced)[^,]*,\s*', re.I), ''),
    (re.compile(r'Although\s+(?:the\s+)?(?:exact|specific|precise)\s+[^,]{5,80}(?:are|is)\s+not\s+(?:specified|provided|detailed|disclosed|confirmed)[^,]*,\s*', re.I), ''),
    # Round 6: Marketing hype (Zeekr 8X review, 2026-03-19)
    (re.compile(r'pavement[- ]crushing', re.I), 'heavy'),
    (re.compile(r'unprecedented\s+(?:mix|blend|combination|level)', re.I), 'notable combination'),
    (re.compile(r'sheer\s+brute\s+force', re.I), 'strong performance'),
    (re.compile(r'hypercar[- ]level', re.I), 'rapid'),
    (re.compile(r'aggressively\s+(?:positioned|priced)', re.I), 'competitively priced'),
    (re.compile(r'completely\s+disrupt', re.I), 'enter'),
    (re.compile(r'definitive[, ]+(?:a\s+)?(?:pavement-crushing\s+)?proof\s+point', re.I), 'a clear example'),
    (re.compile(r'poised\s+to\s+redefine', re.I), 'entering'),
    (re.compile(r'stole\s+the\s+show', re.I), 'attracted attention'),
    (re.compile(r'takes?\s+it\s+to\s+(?:a(?:nother)?\s+)?(?:whole\s+)?(?:new\s+)?level', re.I), 'improves significantly'),
    # Round 7: Zeekr 8X verdict filler (2026-03-19)
    (re.compile(r'\bblistering\b', re.I), 'rapid'),
    (re.compile(r'\bmonumental\s+achievement\b', re.I), 'strong achievement'),
    (re.compile(r'\blavishly\s+appointed\b', re.I), 'well-appointed'),
    (re.compile(r'\bserenity\s+of\s+(?:its|the)\b', re.I), 'comfort of its'),
    (re.compile(r'\bsheer\s+violence\b', re.I), 'speed'),
    (re.compile(r'\bbloody\s+fast\b', re.I), 'very fast'),
]


def clean_banned_phrases(html: str) -> str:
    """Remove or replace banned filler phrases that Gemini sometimes ignores."""
    original_len = len(html)
    
    # 1. Remove entire <p> blocks that are pure filler
    html = _BANNED_SENTENCE_PATTERNS.sub('', html)
    
    # 2. Inline replacements for smaller phrases
    for pattern, replacement in _BANNED_INLINE_REPLACEMENTS:
        html = pattern.sub(replacement, html)
    
    # 3. Remove ALT_TEXT / SEO metadata that AI sometimes leaks into visible content
    # Remove entire hidden div block (when AI wraps it correctly)
    html = re.sub(r'<div\s+class="alt-texts"[^>]*>.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove raw ALT_TEXT lines (when AI doesn't wrap them in a div)
    html = re.sub(r'(?:^|\n)\s*ALT_TEXT_\d+:.*?(?:\n|$)', '\n', html)
    # Remove "SEO Visual Assets:" header
    html = re.sub(r'<p>\s*(?:<strong>)?SEO Visual Assets:?(?:</strong>)?\s*</p>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'(?:^|\n)\s*SEO Visual Assets:?\s*(?:\n|$)', '\n', html, flags=re.IGNORECASE)

    # 3b. Remove <li> items that describe missing data (banned Cons in prompt)
    _banned_cons_rx = re.compile(
        r'<li>[^<]*(?:'
        r'(?:are|is)\s+not\s+(?:fully\s+)?(?:detailed|specified|disclosed|confirmed|announced|yet\s+public|provided|available)'
        r'|details?\s+(?:have\s+)?not\s+(?:yet\s+)?been\s+(?:released|confirmed|disclosed|provided)'
        r'|(?:specific|full|complete)\s+[^<]*(?:not\s+(?:available|provided|disclosed|released|detailed))'
        r'|not\s+yet\s+confirmed|remain\s+unknown|awaiting\s+(?:official\s+)?confirmation'
        r')[^<]*</li>',
        re.IGNORECASE
    )
    cleaned_cons = _banned_cons_rx.sub('', html)
    if cleaned_cons != html:
        removed_li = html.count('<li>') - cleaned_cons.count('<li>')
        print(f"  🧹 Removed {removed_li} invalid Cons items (missing-data phrases)")
        html = cleaned_cons

    # 3c. Remove sentences/blocks that leak source format (transcript, video, YouTube, etc.)
    # These must NEVER appear in published articles — they signal AI-generated content to Google
    _source_leak_rx = re.compile(
        r'<(p|li)>[^<]*(?:'
        r'(?:not\s+)?(?:detailed|described|mentioned|covered|provided|available|specified|included)'
        r'\s+in\s+(?:the\s+)?(?:provided\s+)?transcript'
        r'|(?:in|from|based\s+on|as\s+(?:shown|mentioned|noted|discussed)\s+in)'
        r'\s+(?:the\s+)?(?:video|transcript|footage|clip|source\s+material)'
        r'|transcript\s+(?:mentions?|shows?|notes?|describes?|includes?|covers?|provides?)'
        r'|according\s+to\s+(?:the\s+)?(?:video|transcript|reviewer|footage)'
        r'|as\s+(?:shown|seen|demonstrated)\s+in\s+(?:the\s+)?(?:video|footage|clip)'
        r'|from\s+(?:the\s+)?(?:youtube|video)\s+(?:review|footage|clip)'
        r')[^<]*</(?:p|li)>',
        re.IGNORECASE | re.DOTALL,
    )
    cleaned_leaks = _source_leak_rx.sub('', html)
    if cleaned_leaks != html:
        removed_leaks = html.count('<p>') + html.count('<li>') - cleaned_leaks.count('<p>') - cleaned_leaks.count('<li>')
        print(f"  🔒 Source leak cleanup: removed {removed_leaks} blocks mentioning transcript/video")
        html = cleaned_leaks

    # 4. Clean up empty paragraphs left behind
    html = re.sub(r'<p>\s*</p>', '', html)

    # 4b. Remove orphan section headers — h2/h3 with no content before next header
    # Happens when all <p> inside a section are stripped by banned-phrase filters
    # e.g. <h2>Driving Experience</h2><h2>Pricing & Availability</h2> → remove the empty one
    html = re.sub(
        r'(<h[23][^>]*>[^<]+</h[23]>)\s*(?=<h[23])',
        '',
        html,
        flags=re.IGNORECASE,
    )

    # 5. Strip spec-table lines where value is 'Not specified in web context'
    #    Pattern: '▸ FIELD: Not specified in web context' (plain text lines inside <p> or bare)
    _not_specified_rx = re.compile(
        r'(?m)^[ \t]*(?:▸\s*|•\s*)?[A-Z0-9 /()]+:\s*Not specified in web context\s*$\n?',
        re.IGNORECASE,
    )
    cleaned_spec = _not_specified_rx.sub('', html)
    if cleaned_spec != html:
        print("  🧹 Spec-table cleaner: removed 'Not specified in web context' lines")
        html = cleaned_spec
    # Also remove inside <li> or <p> tags
    html = re.sub(
        r'<(?:li|p)>[^<]*Not specified in web context[^<]*</(?:li|p)>',
        '', html, flags=re.IGNORECASE,
    )

    # 6. Currency normalisation:
    #    a) RMB → CNY
    html = re.sub(r'\bRMB\b', 'CNY', html)
    #    b) If CNY price present but no USD approximation, add one
    # Get live CNY/USD rate from currency_service, fallback to approximate
    try:
        from ai_engine.modules.currency_service import get_cached_rates
        cached = get_cached_rates()
        cny_rate = cached['rates'].get('CNY', 7.25) if cached and cached.get('rates') else 7.25
    except Exception:
        cny_rate = 7.25

    def _inject_usd(m):
        amount_str = m.group(1).replace(',', '')
        try:
            cny = float(amount_str)
            usd = round(cny / cny_rate / 1000) * 1000
            usd_str = f'${usd:,.0f}'
            return f"{m.group(0)} (approx. {usd_str})"
        except ValueError:
            return m.group(0)
    # Only inject if '(approx.' not already present next to the price
    html = re.sub(
        r'CNY\s+([\d,]+(?:\.\d+)?)(?!\s*(?:\(approx|\s*–|\s*to|\s*/|\s*\~))',
        _inject_usd, html,
    )

    cleaned = original_len - len(html)
    if cleaned > 0:
        print(f"  🧹 Post-processing: removed {cleaned} chars of filler")

    return html


# Backward-compatible alias (used by old imports with underscore prefix)
_clean_banned_phrases = clean_banned_phrases
