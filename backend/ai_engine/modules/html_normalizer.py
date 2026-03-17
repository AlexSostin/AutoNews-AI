"""
HTML normalization for AI-generated content.

Converts markdown remnants (bold, italic, headings, lists) to proper HTML,
wraps bare text in <p> tags, and cleans up backticks.
"""
import re

try:
    from ai_engine.modules.utils import clean_html_markup
except ImportError:
    from modules.utils import clean_html_markup


def ensure_html_only(content):
    """
    Ensures the content is properly formatted HTML.
    Always cleans up markdown bold/italic remnants (**, ***, *).
    Converts markdown lists to HTML lists.
    Wraps bare text blocks in <p> tags.
    """
    if not content or not content.strip():
        return content

    # Step 1: Always clean markdown bold/italic remnants, even in otherwise-HTML content
    # Order matters: handle *** before ** before *
    content = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'(?<![\\\s<>/])\*([^*\n]+?)\*(?![\\>/])', r'<em>\1</em>', content)

    # Step 2: Convert markdown headings (## / ###) if present
    content = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^#\s+(.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # Step 3: Convert markdown lists (* item, - item) to HTML <ul><li>
    # Process line by line to properly group consecutive list items
    has_md_lists = bool(re.search(r'^\s*[\*\-]\s+', content, re.MULTILINE))
    if has_md_lists and '<li>' not in content:
        lines = content.split('\n')
        result_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            is_list_item = bool(re.match(r'^[\*\-]\s+(.+)', stripped))
            if is_list_item:
                item_text = re.sub(r'^[\*\-]\s+', '', stripped)
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{item_text}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        if in_list:
            result_lines.append('</ul>')
        content = '\n'.join(result_lines)

    # Step 4: Wrap bare text blocks in <p> tags (text not inside any HTML tag)
    if '<p>' not in content:
        blocks = content.split('\n\n')
        new_blocks = []
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            if b.startswith('<'):
                new_blocks.append(b)
            else:
                new_blocks.append(f'<p>{b}</p>')
        content = '\n\n'.join(new_blocks)

    # Step 5: Clean up backticks
    content = re.sub(r'```[a-z]*\n?', '', content)
    content = re.sub(r'```', '', content)

    return clean_html_markup(content)
