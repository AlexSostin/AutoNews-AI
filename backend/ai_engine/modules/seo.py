"""
Unified SEO module — keywords, internal linking, and A/B title variants.

Sub-modules merged:
  - seo_helpers:   generate_seo_keywords, extract_keywords_from_content
  - seo_linker:    inject_internal_links
  - ab_variants:   generate_title_variants
"""
import re
import logging
import random
import traceback
from collections import Counter
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  SEO Keywords
# ══════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════
#  Internal Link Injection
# ══════════════════════════════════════════════════════════════════

def inject_internal_links(article_html: str, tag_names: list, make: str = None) -> str:
    """
    Finds related past articles based on tags/make/model and injects contextual 
    internal <a> links into the article HTML to boost SEO.
    Also appends a "Читайте также" (Read Also) block at the bottom.
    """
    if not tag_names and not make:
        return article_html
        
    try:
        from django.db.models import Q
        from news.models import Article
        
        # 1. Find related articles
        query = Article.objects.filter(is_published=True)
        search_terms = []
        
        if make and make != 'Not specified':
            query = query.filter(title__icontains=make)
            search_terms.append(make)
        elif tag_names:
            query = query.filter(tags__name__in=tag_names).distinct()
            search_terms.extend(tag_names)
            
        # Get latest 10 related articles to pick 2 randomly
        related_articles = list(query.order_by('-created_at')[:10])
        
        if not related_articles:
            return article_html
            
        # Pick up to 2
        selected_articles = random.sample(related_articles, min(2, len(related_articles)))
        
        # 2. Parse HTML and inject inline links
        soup = BeautifulSoup(article_html, 'html.parser')
        
        # We only want to inject links into standard <p> tags
        paragraphs = soup.find_all('p')
        
        linked_articles = []
        
        for article in selected_articles:
            target_url = f"/articles/{article.slug}"
            link_injected = False
            
            # Keywords to matching
            anchor_keywords = [make] if make and make != 'Not specified' else []
            try:
                anchor_keywords.extend([t.name for t in article.tags.all()[:3]])
            except Exception:
                pass
                
            # Fallbacks
            anchor_keywords.extend(['электромобиль', 'автомобиль', 'бренд', 'новинка', 'electric vehicle', 'new model'])
            
            # Look for these keywords in text paragraphs that don't already have links
            for p in paragraphs:
                if link_injected:
                    break
                    
                if p.find('a'): # Skip paragraphs that already have links
                    continue
                    
                text_content = p.get_text()
                for keyword in anchor_keywords:
                    if not keyword or len(keyword) < 3:
                        continue
                    
                    # Exact word match (case insensitive)
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    if pattern.search(text_content):
                        # Build link HTML using the matched text
                        match_str = pattern.search(text_content).group(0)
                        link_html = f'<a href="{target_url}" title="{article.title}" data-seo-linker="true">{match_str}</a>'
                        
                        # Replace first occurrence in the paragraph's inner HTML
                        inner_html = p.decode_contents()
                        new_inner = pattern.sub(link_html, inner_html, count=1)
                        p.clear()
                        p.append(BeautifulSoup(new_inner, 'html.parser'))
                        
                        link_injected = True
                        linked_articles.append(article)
                        break
            
            # If we couldn't find a suitable inline anchor, we still want it in the "Read Also" block
            if not link_injected and article not in linked_articles:
                linked_articles.append(article)

        # 3. Append 'Read Also' block at the bottom
        if linked_articles:
            read_also_html = '<div class="seo-related-links" style="margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">'
            read_also_html += '<h3 style="margin-top: 0; font-size: 1.25rem;">Читайте также:</h3><ul style="margin-bottom: 0;">'
            for article in linked_articles:
                # Clean YouTube noise from linked titles (Walk-around, First Look, etc.)
                try:
                    from ai_engine.modules.utils import clean_video_title
                    clean_title = clean_video_title(article.title)
                except ImportError:
                    clean_title = article.title
                read_also_html += f'<li><a href="/articles/{article.slug}">{clean_title}</a></li>'
            read_also_html += '</ul></div>\n'
            
            read_also_soup = BeautifulSoup(read_also_html, 'html.parser')
            
            # Append right before the alt-texts div or source-attribution if they exist
            alt_texts_div = soup.find('div', class_='alt-texts')
            source_attr = soup.find('p', class_='source-attribution')
            
            if alt_texts_div:
                alt_texts_div.insert_before(read_also_soup)
            elif source_attr:
                source_attr.insert_before(read_also_soup)
            else:
                soup.append(read_also_soup)
                
        return str(soup)
        
    except Exception as e:
        logger.error(f"SEO Linker failed: {e}")
        print(f"⚠️ SEO Linker failed: {e}")
        return article_html


# ══════════════════════════════════════════════════════════════════
#  A/B Title Variants
# ══════════════════════════════════════════════════════════════════

def generate_title_variants(article, provider='gemini'):
    """Generate A/B title variants for an article using AI.
    Creates 3 variants: A (original), B and C (AI-generated alternatives).
    Returns the created variants or empty list on failure."""
    try:
        from news.models import ArticleTitleVariant
        
        # Skip if variants already exist
        if ArticleTitleVariant.objects.filter(article=article).exists():
            print(f"📊 A/B variants already exist for article #{article.id}")
            return []
        
        # Generate alternatives using AI
        try:
            from ai_engine.modules.ai_provider import get_ai_provider
        except ImportError:
            from modules.ai_provider import get_ai_provider
        
        ai = get_ai_provider(provider)
        
        prompt = f"""You are an SEO expert and headline writer for an automotive news website.

Given this article title: "{article.title}"

Generate exactly 2 alternative headline variants that:
- Are roughly the same length (±20%)
- Highlight different angles or benefits (performance, price, tech, etc.)
- Are engaging, click-worthy, but NOT clickbait
- Maintain factual accuracy
- Include the car make/model name

Reply with ONLY the two alternative titles, one per line. No numbering, no explanations, no quotes."""

        result = ai.generate_completion(prompt, temperature=0.9, max_tokens=200)
        
        lines = [l.strip().strip('"').strip("'") for l in result.strip().split('\n') if l.strip()]
        # Filter out lines that look like numbering or explanations
        lines = [l for l in lines if len(l) > 10 and not l.startswith(('1.', '2.', '-', '*', '#'))]
        # Remove leading numbers like "1) " or "2) "
        lines = [re.sub(r'^\d+[\)\.]\s*', '', l) for l in lines]
        
        alt_titles = lines[:2]  # Max 2 alternatives
        
        if not alt_titles:
            print(f"⚠️ AI returned no valid title alternatives")
            return []
        
        # Create variant A (original)
        variants = []
        variants.append(ArticleTitleVariant.objects.create(
            article=article,
            variant='A',
            title=article.title
        ))
        
        # Create variant B
        if len(alt_titles) >= 1:
            variants.append(ArticleTitleVariant.objects.create(
                article=article,
                variant='B',
                title=alt_titles[0][:500]
            ))
        
        # Create variant C
        if len(alt_titles) >= 2:
            variants.append(ArticleTitleVariant.objects.create(
                article=article,
                variant='C',
                title=alt_titles[1][:500]
            ))
        
        print(f"📊 Created {len(variants)} A/B title variants:")
        for v in variants:
            print(f"   [{v.variant}] {v.title}")
        
        return variants
        
    except Exception as e:
        print(f"⚠️ A/B title variant generation failed: {e}")
        traceback.print_exc()
        return []
