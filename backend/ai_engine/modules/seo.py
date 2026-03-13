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
            
            # If we couldn't find a suitable inline anchor, just skip — we still get value from inline links
            if not link_injected:
                pass  # No inline slot found for this article, that's okay

        # Read Also block removed — frontend already shows related articles with images
        
        result_html = str(soup)
        return result_html
        
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
        from news.models import ArticleTitleVariant, CarSpecification
        
        # Skip if variants already exist
        if ArticleTitleVariant.objects.filter(article=article).exists():
            print(f"📊 A/B variants already exist for article #{article.id}")
            return []
        
        # Generate alternatives using AI
        try:
            from ai_engine.modules.ai_provider import get_light_provider
        except ImportError:
            from modules.ai_provider import get_light_provider
        
        ai = get_light_provider()
        
        # Pull available spec data to enrich the headline
        spec_context = ""
        try:
            spec = CarSpecification.objects.filter(article=article).first()
            if spec:
                parts = []
                if spec.power_hp:      parts.append(f"{spec.power_hp} hp")
                if spec.range_km:      parts.append(f"{spec.range_km} km range")
                if spec.range_cltc:    parts.append(f"{spec.range_cltc} km CLTC")
                if spec.battery_kwh:   parts.append(f"{spec.battery_kwh} kWh battery")
                if spec.price_from:
                    try:
                        price_cny = float(str(spec.price_from).replace(',', ''))
                        price_usd = round(price_cny / 7.2)
                        parts.append(f"starts at ${price_usd:,}")
                    except Exception:
                        pass
                if spec.acceleration_0_100: parts.append(f"0-100 in {spec.acceleration_0_100}s")
                if parts:
                    spec_context = f"\nKey specs: {', '.join(parts)}"
        except Exception:
            pass
        
        # Extract make/model for validation
        make_name = ""
        model_name = ""
        try:
            spec = CarSpecification.objects.filter(article=article).first()
            if spec:
                make_name = (spec.make or "").strip()
                model_name = (spec.model or "").strip()
        except Exception:
            pass
        
        # Fallback: try to extract from title
        if not make_name:
            import re as _re
            m = _re.search(r'(\d{4})\s+(\w+)\s+(\w+)', article.title)
            if m:
                make_name = m.group(2)
                model_name = m.group(3)

        prompt = f"""You are a headline writer for an automotive enthusiast website.

Original title: "{article.title}"{spec_context}

Write exactly 2 alternative headlines. STRICT RULES:
- MUST include the car brand name ({make_name or 'from the title'}) and model ({model_name or 'from the title'})
- Use specific numbers from specs when available (range, price, power, 0-100)
- FORMAT: "[Year] [Brand] [Model]: [Engaging hook with best spec]"
- Max 90 characters each, minimum 40 characters
- NO clickbait without car name — every title MUST identify which car it's about
- English only

GOOD examples:
✅ "2026 BYD Seal 06 DM-i: 2,100 km Range Hybrid Starting at $14,000"
✅ "2025 Avatr 11 EREV: 1,065 km Range SUV Disrupting Premium Market"
✅ "2026 Zeekr 7X: 421 hp Electric SUV Under $30,000"

BAD examples (NEVER generate these):
❌ "Costs $13,100" (no car name!)
❌ "610km range for under $30k" (no car name!)
❌ "Under $20k beats Corolla" (no car name!)
❌ "Blows past 100km/h in 3s" (no car name!)

Reply with ONLY the two titles, one per line. No numbering, no quotes, no explanations."""

        result = ai.generate_completion(prompt, temperature=0.85, max_tokens=200)
        
        lines = [l.strip().strip('"').strip("'") for l in result.strip().split('\n') if l.strip()]
        # Filter out lines that look like numbering or explanations
        lines = [l for l in lines if len(l) > 10 and not l.startswith(('1.', '2.', '-', '*', '#'))]
        # Remove leading numbers like "1) " or "2) "
        lines = [re.sub(r'^\d+[\)\.]\s*', '', l) for l in lines]
        
        alt_titles = lines[:2]  # Max 2 alternatives
        
        # Validate: each variant MUST contain the brand or model name
        if make_name and len(make_name) > 1:
            validated_titles = []
            for t in alt_titles:
                t_lower = t.lower()
                has_brand = make_name.lower() in t_lower
                has_model = model_name.lower() in t_lower if model_name else True
                if has_brand or has_model:
                    validated_titles.append(t)
                else:
                    print(f"  ⚠️ Rejected A/B variant (no brand/model): \"{t}\"")
            alt_titles = validated_titles
        
        if not alt_titles:
            print(f"⚠️ AI returned no valid title alternatives (all rejected by brand check)")
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

