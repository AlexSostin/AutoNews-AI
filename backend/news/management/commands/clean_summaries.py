"""
Management command to clean AI artifact phrases from article summaries.

3-tier approach:
  Tier 1 (AI Regen)   — Gemini regenerates summary from article content
  Tier 2 (Smart Extract) — Picks first data-rich paragraph from content
  Tier 3 (Regex)       — Removes sentences with worst offender phrases

Usage:
  python manage.py clean_summaries --dry-run          # preview all changes
  python manage.py clean_summaries                     # apply with AI (tier 1)
  python manage.py clean_summaries --tier 2            # smart extraction only
  python manage.py clean_summaries --tier 3            # regex only
  python manage.py clean_summaries --article-id 42     # single article
"""
import re
import time
from django.core.management.base import BaseCommand
from news.models import Article


# Phrases that signal AI-generated-from-video content
AI_LEAK_PHRASES = [
    'transcript', 'provided text', 'video source', 'source video',
    'based on the video', 'from the video', 'in the video',
    'the narrator', 'the host mentions', 'the presenter',
    'this video', 'the video showcases', 'the video provides',
    'the video is a', 'this is a walk-around',
]

# Only these are safe to regex-delete (Tier 3)
SAFE_DELETE_PHRASES = [
    'transcript', 'provided text', 'the narrator', 'the presenter',
    'the host mentions', 'source video', 'video source',
    'the video is a', 'the video provides', 'the video showcases',
    'this video is a', 'this video provides', 'this video showcases',
    'this is a walk-around', 'this is a walkaround',
    'the video presents', 'the video introduces',
    'this video presents', 'this video introduces',
]


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text).strip()


def _is_affected(text: str) -> bool:
    """Check if text contains any AI leak phrases."""
    if not text:
        return False
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in AI_LEAK_PHRASES)


def _has_html_tags(text: str) -> bool:
    """Check if text contains HTML tags (another bug)."""
    if not text:
        return False
    return bool(re.search(r'<[a-z][^>]*>', text, re.IGNORECASE))


# ── Tier 1: AI Regeneration ─────────────────────────────────────────────────

def _regenerate_with_ai(article, ai_provider) -> str:
    """Use AI to generate a fresh summary from article content."""
    # Get first 2000 chars of clean text from content
    content_text = _strip_html(article.content[:4000])[:2000]
    if len(content_text) < 100:
        return ''

    car_name = article.title or ''

    prompt = f"""Write a compelling 2-sentence summary (140-160 characters total) for this automotive article.

ARTICLE TITLE: {car_name}

ARTICLE CONTENT (excerpt):
{content_text}

STRICT RULES:
1. Write as ORIGINAL JOURNALISM — you are the author, this is YOUR article
2. NEVER use words: "video", "transcript", "footage", "presenter", "narrator", "walk-around", "showcases"
3. Start with the car name + most compelling fact (price, range, power, or unique feature)
4. Include 1-2 key specs that car buyers search for (range, price, horsepower)
5. Use active voice, present tense
6. No HTML tags, no quotes, no markdown
7. Be SPECIFIC — use real numbers from the content
8. Write like a Google meta description that makes people click

GOOD EXAMPLES:
- "The 2026 BYD TANG 1240 delivers 1,240 km combined range in a 7-seater PHEV SUV starting at CNY 199,800 ($27,500). Its CATL Blade battery and dual-motor AWD make it a serious family hauler."
- "Zeekr's 007GT combines 421 hp with shooting brake styling and a 680 km range. Starting at CNY 209,900, it targets buyers who want performance without the SUV compromise."

Write ONLY the summary, nothing else:"""

    try:
        result = ai_provider.generate_completion(
            prompt=prompt,
            system_prompt="You are an expert automotive SEO copywriter. Write meta descriptions that drive clicks.",
            temperature=0.4,
            max_tokens=256,
        )
        if result:
            # Clean up: remove quotes, HTML, extra whitespace
            result = result.strip().strip('"\'')
            result = _strip_html(result)
            result = re.sub(r'\s+', ' ', result).strip()
            # Validate: not too short, no banned phrases
            if len(result) >= 50 and not _is_affected(result):
                return result
    except Exception as e:
        print(f"    ⚠️ AI generation failed: {e}")

    return ''


# ── Tier 2: Smart Extraction ────────────────────────────────────────────────

def _smart_extract(content: str) -> str:
    """Extract a data-rich paragraph from article content, skipping video-reference intros."""
    if not content:
        return ''

    # Remove headings
    cleaned = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', content, flags=re.DOTALL)
    # Find all paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', cleaned, re.DOTALL)

    for i, p_html in enumerate(paragraphs):
        text = _strip_html(p_html).strip()
        # Skip short
        if len(text) < 40:
            continue
        # Skip junk labels
        if text.rstrip(':') in ('Pros', 'Cons', 'Summary', 'Verdict', 'Review', 'Pricing'):
            continue
        # Skip first 2 paragraphs (often contain video references)
        if i < 2:
            text_lower = text.lower()
            if any(p in text_lower for p in AI_LEAK_PHRASES):
                continue
        # Check this paragraph is data-rich (contains numbers)
        has_numbers = bool(re.search(r'\d', text))
        if has_numbers or i >= 2:
            return text

    # Fallback: first paragraph that's not tiny
    for p_html in paragraphs:
        text = _strip_html(p_html).strip()
        if len(text) >= 40:
            return text

    return ''


# ── Tier 3: Regex Cleanup ───────────────────────────────────────────────────

def _regex_cleanup(text: str) -> str:
    """Remove sentences containing the worst AI artifact phrases."""
    if not text:
        return text

    text_lower = text.lower()
    for phrase in SAFE_DELETE_PHRASES:
        if phrase not in text_lower:
            continue
        sentences = re.split(r'(?<=[.!?])\s+', text)
        text = ' '.join(s for s in sentences if phrase not in s.lower())
        text_lower = text.lower()

    return re.sub(r'\s+', ' ', text).strip()


# ── Post-processing ─────────────────────────────────────────────────────────

def _finalize_summary(summary: str) -> tuple:
    """Clean, trim, and derive seo_description from summary."""
    # Strip any remaining HTML tags
    summary = _strip_html(summary)
    # Clean whitespace
    summary = re.sub(r'\s+', ' ', summary).strip()
    # Trim to 300 chars
    if len(summary) > 300:
        summary = summary[:297] + "..."
    # SEO description is first 160 chars
    seo_description = summary[:160]
    return summary, seo_description


class Command(BaseCommand):
    help = 'Clean AI artifact phrases from article summaries using AI regeneration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving',
        )
        parser.add_argument(
            '--tier',
            type=int,
            choices=[1, 2, 3],
            default=1,
            help='Force specific tier (1=AI, 2=extract, 3=regex). Default: 1',
        )
        parser.add_argument(
            '--article-id',
            type=int,
            help='Process single article by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tier = options['tier']
        article_id = options.get('article_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN (no changes will be saved) ===\n'))

        # Initialize AI provider for Tier 1
        ai_provider = None
        if tier == 1:
            try:
                from ai_engine.modules.ai_provider import get_ai_provider
                ai_provider = get_ai_provider('gemini')
                self.stdout.write(self.style.SUCCESS('✓ Gemini AI provider initialized\n'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Could not initialize AI provider: {e}\n'
                    f'   Falling back to Tier 2 (smart extraction)\n'
                ))
                tier = 2

        # Get articles
        qs = Article.objects.filter(is_published=True)
        if article_id:
            qs = qs.filter(id=article_id)

        articles = list(qs)
        total = len(articles)
        fixed_count = 0
        tier_stats = {1: 0, 2: 0, 3: 0}

        for article in articles:
            needs_fix = (
                _is_affected(article.summary) or
                _is_affected(article.seo_description) or
                _has_html_tags(article.summary) or
                _has_html_tags(article.seo_description)
            )

            if not needs_fix:
                continue

            old_summary = article.summary or ''
            new_summary = ''
            used_tier = tier

            # Tier 1: AI Regeneration
            if tier <= 1 and ai_provider:
                new_summary = _regenerate_with_ai(article, ai_provider)
                if new_summary:
                    used_tier = 1
                else:
                    used_tier = 2  # fallback

            # Tier 2: Smart Extraction
            if not new_summary and tier <= 2:
                new_summary = _smart_extract(article.content)
                if new_summary:
                    used_tier = 2
                else:
                    used_tier = 3  # fallback

            # Tier 3: Regex Cleanup
            if not new_summary:
                new_summary = _regex_cleanup(old_summary)
                used_tier = 3

            # If regex cleanup left it too short or still contains AI phrases,
            # try smart extract from article content
            if (len(new_summary) < 50 or _is_affected(new_summary)) and article.content:
                extracted = _smart_extract(article.content)
                if extracted and len(extracted) > len(new_summary):
                    new_summary = extracted
                    used_tier = 2

            # Finalize
            new_summary, new_seo = _finalize_summary(new_summary)

            if new_summary == _strip_html(old_summary).strip():
                continue  # No change after all processing

            fixed_count += 1
            tier_stats[used_tier] = tier_stats.get(used_tier, 0) + 1

            # Display
            tier_label = {1: '🤖 AI', 2: '📝 Extract', 3: '🔧 Regex'}[used_tier]
            self.stdout.write(f'\n{"─" * 60}')
            self.stdout.write(self.style.SUCCESS(f'  [{tier_label}] {article.title[:55]}'))
            self.stdout.write(self.style.ERROR(f'    OLD: {old_summary[:100]}'))
            self.stdout.write(self.style.SUCCESS(f'    NEW: {new_summary[:100]}'))
            if len(new_summary) < 80:
                self.stdout.write(self.style.WARNING(f'    ⚠️  Short ({len(new_summary)} chars)'))

            if not dry_run:
                article.summary = new_summary
                article.seo_description = new_seo
                article.save(update_fields=['summary', 'seo_description'])

            # Rate limit for AI calls
            if used_tier == 1:
                time.sleep(1)

        # Summary
        self.stdout.write(f'\n{"═" * 60}')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Would fix {fixed_count} of {total} articles.\n'
                f'  Tier 1 (AI): {tier_stats.get(1, 0)} | '
                f'Tier 2 (Extract): {tier_stats.get(2, 0)} | '
                f'Tier 3 (Regex): {tier_stats.get(3, 0)}\n'
                f'Run without --dry-run to apply.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Fixed {fixed_count} of {total} articles.\n'
                f'  Tier 1 (AI): {tier_stats.get(1, 0)} | '
                f'Tier 2 (Extract): {tier_stats.get(2, 0)} | '
                f'Tier 3 (Regex): {tier_stats.get(3, 0)}'
            ))
