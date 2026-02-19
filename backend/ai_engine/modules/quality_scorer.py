"""
Quality scorer for pending articles.

Evaluates articles using heuristic metrics (no AI API calls)
to determine if they're suitable for auto-publishing.

Score range: 1-10
Threshold for auto-publish is configurable in AutomationSettings (default: 7)
"""
import re
import logging

logger = logging.getLogger('news')


def calculate_quality_score(title: str, content: str, specs: dict = None,
                            tags: list = None, featured_image: str = '',
                            images: list = None) -> int:
    """
    Calculate a quality score (1-10) for a pending article.
    
    Scoring breakdown:
    - Content length:     0-2 points
    - Title quality:      0-2 points  
    - Content structure:  0-2 points
    - Has images:         0-1 point
    - Has specs/data:     0-1 point
    - Has tags:           0-1 point
    - No red flags:       0-1 point
    """
    score = 0
    details = []
    
    # --- Content Length (0-2 points) ---
    word_count = len(content.split()) if content else 0
    if word_count >= 800:
        score += 2
        details.append(f"length: 2/2 ({word_count} words)")
    elif word_count >= 400:
        score += 1
        details.append(f"length: 1/2 ({word_count} words)")
    else:
        details.append(f"length: 0/2 ({word_count} words - too short)")
    
    # --- Title Quality (0-2 points) ---
    title_len = len(title) if title else 0
    title_words = len(title.split()) if title else 0
    title_score = 0
    
    if 30 <= title_len <= 100 and title_words >= 4:
        title_score += 1  # Good length
    if title and not title.isupper() and '???' not in title:
        title_score += 1  # Not all-caps, no garbage
    
    score += title_score
    details.append(f"title: {title_score}/2 ({title_len} chars, {title_words} words)")
    
    # --- Content Structure (0-2 points) ---
    structure_score = 0
    
    # Has headings (H2/H3)
    headings = len(re.findall(r'<h[23][^>]*>', content, re.IGNORECASE)) if content else 0
    if headings == 0:
        headings = len(re.findall(r'^#{2,3}\s', content, re.MULTILINE)) if content else 0
    
    if headings >= 2:
        structure_score += 1
    
    # Has paragraphs (not a wall of text)
    paragraphs = content.count('</p>') if content else 0
    if paragraphs == 0:
        paragraphs = content.count('\n\n') if content else 0
    
    if paragraphs >= 3:
        structure_score += 1
    
    score += structure_score
    details.append(f"structure: {structure_score}/2 ({headings} headings, {paragraphs} paragraphs)")
    
    # --- Has Images (0-1 point) ---
    has_image = bool(featured_image) or bool(images and len(images) > 0)
    if has_image:
        score += 1
        details.append("images: 1/1")
    else:
        details.append("images: 0/1 (no featured image)")
    
    # --- Has Specs/Data (0-1 point) ---
    has_specs = bool(specs and any(v for v in specs.values() if v))
    if has_specs:
        score += 1
        details.append(f"specs: 1/1 ({len([v for v in specs.values() if v])} fields)")
    else:
        details.append("specs: 0/1")
    
    # --- Has Tags (0-1 point) ---
    has_tags = bool(tags and len(tags) >= 2)
    if has_tags:
        score += 1
        details.append(f"tags: 1/1 ({len(tags)} tags)")
    else:
        details.append(f"tags: 0/1 ({len(tags) if tags else 0} tags)")
    
    # --- Red Flags Check (0-1 point) ---
    red_flags = []
    if content:
        # Check for placeholder text
        placeholders = ['lorem ipsum', 'TODO', 'FIXME', '[insert', '{placeholder']
        for p in placeholders:
            if p.lower() in content.lower():
                red_flags.append(p)
        
        # Check for very repetitive content
        sentences = re.split(r'[.!?]', content)
        if len(sentences) > 5:
            unique_ratio = len(set(s.strip().lower() for s in sentences if s.strip())) / len(sentences)
            if unique_ratio < 0.5:
                red_flags.append('repetitive content')
    
    if not red_flags:
        score += 1
        details.append("quality: 1/1 (no red flags)")
    else:
        details.append(f"quality: 0/1 (flags: {', '.join(red_flags)})")
    
    # Clamp to 1-10
    final_score = max(1, min(10, score))
    
    logger.info(f"📊 Quality score: {final_score}/10 — {'; '.join(details)}")
    
    return final_score


def score_pending_article(pending_article) -> int:
    """Calculate and save quality score for a PendingArticle instance."""
    score = calculate_quality_score(
        title=pending_article.title,
        content=pending_article.content,
        specs=pending_article.specs,
        tags=pending_article.tags,
        featured_image=pending_article.featured_image,
        images=pending_article.images,
    )
    
    pending_article.quality_score = score
    pending_article.save(update_fields=['quality_score'])
    
    return score
