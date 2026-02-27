import logging
import re
import random
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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
        related_articles = list(query.order_by('-published_at')[:10])
        
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
                        # Extract the exact matched casing
                        match_str = pattern.search(text_content).group(0)
                        
                        p_html = str(p)
                        # Avoid matching inside existing HTML attributes by simple replace on text
                        # Since we checked p.find('a') is None, it should be safe.
                        new_p_html = pattern.sub(f'<a href="{target_url}" title="{article.title}" data-seo-linker="true">\g<0></a>', p_html, count=1)
                        
                        new_p_soup = BeautifulSoup(new_p_html, 'html.parser')
                        p.replace_with(new_p_soup)
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
                read_also_html += f'<li><a href="/articles/{article.slug}">{article.title}</a></li>'
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
