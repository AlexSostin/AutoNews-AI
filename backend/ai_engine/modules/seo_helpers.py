"""
SEO helper functions for generating keywords and meta tags
"""


def generate_seo_keywords(analysis, title):
    """
    Generate SEO keywords from analysis and title.
    Returns comma-separated string of 5-7 relevant keywords.
    """
    keywords = []
    
    # Safety check: analysis must be a dict
    if not isinstance(analysis, dict):
        # Return generic keywords if analysis is invalid
        return 'car review, automotive, vehicle'
    
    # Extract make/model from analysis
    make = analysis.get('make', '').strip()
    model = analysis.get('model', '').strip()
    year = analysis.get('year', '')
    
    if make and make != 'Unknown':
        keywords.append(make)
    if model and model != 'Unknown':
        keywords.append(model)
    if year:
        keywords.append(str(year))
    
    # Add combined make+model
    if make and model and make != 'Unknown' and model != 'Unknown':
        keywords.append(f"{make} {model}")
        if year:
            keywords.append(f"{year} {make} {model}")
    
    # Extract category-related keywords
    category = analysis.get('category', '').lower()
    if 'electric' in category or 'ev' in category.lower():
        keywords.extend(['electric vehicle', 'EV'])
    elif 'hybrid' in category:
        keywords.append('hybrid car')
    elif 'performance' in category or 'sports' in category:
        keywords.extend(['performance car', 'sports car'])
    elif 'suv' in category.lower():
        keywords.append('SUV')
    
    # Add generic automotive keywords
    keywords.extend(['car review', 'automotive'])
    
    # Deduplicate and limit to 7 keywords
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen and kw:
            seen.add(kw_lower)
            unique_keywords.append(kw)
            if len(unique_keywords) >= 7:
                break
    
    return ', '.join(unique_keywords)


def extract_keywords_from_content(content, max_keywords=5):
    """
    Extract important keywords from article content.
    Simple implementation - can be enhanced with NLP.
    """
    import re
    from collections import Counter
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', content)
    
    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    # Extract words (2+ letters)
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())
    
    # Filter stop words and count frequency
    filtered_words = [w for w in words if w not in stop_words]
    word_counts = Counter(filtered_words)
    
    # Get top keywords
    top_keywords = [word for word, count in word_counts.most_common(max_keywords)]
    
    return top_keywords
