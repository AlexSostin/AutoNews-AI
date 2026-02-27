"""
A/B title variant generation for articles.

Uses AI to generate alternative headline variants for A/B testing.
Creates 3 variants: A (original), B and C (AI-generated alternatives).
"""
import re
import logging
import traceback

logger = logging.getLogger(__name__)


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
