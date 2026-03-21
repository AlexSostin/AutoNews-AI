"""
Inline image placeholder injection for generated articles.

Inserts {{IMAGE_2}} and {{IMAGE_3}} placeholders at logical section breaks
between <h2> headings, avoiding sections with custom blocks (spec-bar,
compare-grid, etc.).
"""
import re
import logging

logger = logging.getLogger(__name__)


def _inject_inline_image_placeholders(html: str, max_images: int = 2) -> str:
    """
    Insert {{IMAGE_2}} and {{IMAGE_3}} placeholders into article HTML
    at logical section breaks between <h2> headings.

    Strategy:
    - Find all <h2> section boundaries
    - Skip sections containing custom blocks (spec-bar, pros-cons, verdict, compare-grid)
    - Distribute placeholders evenly across remaining text-heavy sections
    - Insert each placeholder BEFORE the <h2> heading of the target section
      (so the image appears at the end of the previous section)

    Args:
        html: Generated article HTML
        max_images: Number of placeholders to insert (typically 2 for IMAGE_2 + IMAGE_3)
    
    Returns:
        HTML with {{IMAGE_2}} and {{IMAGE_3}} placeholders inserted
    """
    # Custom blocks to avoid placing images near
    SKIP_CLASSES = ['spec-bar', 'pros-cons', 'fm-verdict', 'compare-grid',
                    'price-tag', 'powertrain-specs']

    # Find all <h2> positions (these are section boundaries)
    h2_pattern = re.compile(r'<h2[^>]*>', re.IGNORECASE)
    h2_matches = list(h2_pattern.finditer(html))

    if len(h2_matches) < 3:
        print(f"  📸 Not enough sections ({len(h2_matches)}) for inline images, skipping")
        return html

    # Build a list of "insertable" positions (indices of h2 tags where we CAN place an image before)
    insertable = []
    for i, match in enumerate(h2_matches):
        if i == 0:
            continue  # Never before the first h2 (title)

        # Check the content between this h2 and the previous one
        prev_end = h2_matches[i - 1].end()
        section_content = html[prev_end:match.start()]

        # Skip if the section contains custom blocks
        has_custom_block = any(cls in section_content for cls in SKIP_CLASSES)
        if has_custom_block:
            continue

        # Skip if section is too short (< 200 chars of text = probably just a heading + 1 line)
        text_only = re.sub(r'<[^>]+>', '', section_content).strip()
        if len(text_only) < 200:
            continue

        insertable.append(match.start())

    if not insertable:
        print("  📸 No suitable positions found for inline images")
        return html

    # Distribute images evenly across available positions
    num_to_place = min(max_images, len(insertable))
    if num_to_place == 0:
        return html

    # Pick evenly spaced positions
    if num_to_place == 1:
        chosen_indices = [len(insertable) // 2]
    else:
        step = len(insertable) / (num_to_place + 1)
        chosen_indices = [int(step * (i + 1)) for i in range(num_to_place)]
        # Clamp to valid range
        chosen_indices = [min(idx, len(insertable) - 1) for idx in chosen_indices]
        # Deduplicate
        chosen_indices = list(dict.fromkeys(chosen_indices))

    # Build placeholder tags (IMAGE_2 = first inline, IMAGE_3 = second inline)
    placeholders = ['{{IMAGE_2}}', '{{IMAGE_3}}']

    # Insert from end to start (to preserve positions)
    placed = 0
    for idx in reversed(chosen_indices):
        if placed >= len(placeholders):
            break
        pos = insertable[idx]
        placeholder_idx = len(chosen_indices) - 1 - list(reversed(chosen_indices)).index(idx)
        if placeholder_idx < len(placeholders):
            tag = placeholders[placeholder_idx]
            # Insert the placeholder right before the <h2> with a newline
            html = html[:pos] + f'\n{tag}\n' + html[pos:]
            placed += 1

    print(f"  📸 Inserted {placed} inline image placeholder(s) into article body")
    return html

def replace_inline_images_in_article(article) -> bool:
    """
    Replace {{IMAGE_2}} and {{IMAGE_3}} placeholders with actual <figure> tags
    if the article has those images uploaded. Cleans up any unfulfilled placeholders.
    Saves the article if changes were made.
    """
    if not getattr(article, 'content', None):
        return False
        
    import re
    if '{{IMAGE' not in article.content:
        return False

    updated_content = article.content
    inline_replaced = 0

    for slot, field_name in [(2, 'image_2'), (3, 'image_3')]:
        placeholder = f'{{{{IMAGE_{slot}}}}}'
        if placeholder not in updated_content:
            continue
            
        img_field = getattr(article, field_name, None)
        img_url = ''
        if img_field:
            try:
                img_url = img_field.url if hasattr(img_field, 'url') and img_field.name else ''
            except ValueError:
                img_url = ''
        
        if not img_url:
            raw_val = getattr(article, field_name, '')
            if isinstance(raw_val, str) and raw_val.startswith('http'):
                img_url = raw_val

        if img_url:
            title = getattr(article, 'title', 'Image').replace('"', '&quot;')
            figure_html = (
                f'<figure class="article-inline-image">'
                f'<img src="{img_url}" alt="{title}" loading="lazy" />'
                f'</figure>'
            )
            updated_content = updated_content.replace(placeholder, figure_html)
            inline_replaced += 1
        else:
            updated_content = updated_content.replace(placeholder, '')

    # Safety-net cleanup for any residual {{IMAGE_X}} placeholders
    leftover_pattern = re.compile(r'\{\{IMAGE_\d+\}\}')
    if leftover_pattern.search(updated_content):
        updated_content = leftover_pattern.sub('', updated_content)
        updated_content = re.sub(r'<p>\s*</p>', '', updated_content)
        updated_content = re.sub(r'\n\s*\n\s*\n', '\n\n', updated_content)

    if article.content != updated_content:
        logger.info(f"📸 Replaced {inline_replaced} inline images and cleaned placeholders for article {article.id}")
        article.content = updated_content
        article.save(update_fields=['content'])
        return True
        
    return False
