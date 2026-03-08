"""
Management command: send_telegram_post

Send an article to the @freshmotors_news Telegram channel.

Usage:
    # Send specific article
    python manage.py send_telegram_post --article-id 42

    # Send latest article
    python manage.py send_telegram_post --latest

    # Send test message (verify bot connection)
    python manage.py send_telegram_post --test

    # Dry-run: preview post without sending
    python manage.py send_telegram_post --article-id 42 --dry-run

    # Force send even if TELEGRAM_AUTO_POST is disabled
    python manage.py send_telegram_post --article-id 42 --force
"""
from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = 'Send an article to the FreshMotors Telegram channel'

    def add_arguments(self, parser):
        parser.add_argument('--article-id', type=int, help='Article ID to post')
        parser.add_argument('--latest', action='store_true', help='Post the latest published article')
        parser.add_argument('--test', action='store_true', help='Send a test message to verify connection')
        parser.add_argument('--dry-run', action='store_true', help='Preview the post without sending')
        parser.add_argument('--force', action='store_true', help='Send even if auto-post is disabled')

    def handle(self, *args, **options):
        from ai_engine.modules.telegram_publisher import (
            send_to_channel, send_test_message, format_telegram_post
        )

        # Test mode
        if options['test']:
            self.stdout.write('\n🧪 Sending test message to @freshmotors_news...\n')
            result = send_test_message(
                "🧪 <b>FreshMotors Bot Test</b>\n\n"
                "✅ Bot is connected and working!\n"
                "📡 Channel: @freshmotors_news\n"
                "🤖 Auto-publishing is ready."
            )
            if result.get('ok'):
                msg_id = result.get('result', {}).get('message_id', '?')
                self.stdout.write(self.style.SUCCESS(f'✅ Test message sent! (msg_id={msg_id})'))
            else:
                self.stdout.write(self.style.ERROR(
                    f"❌ Failed: {result.get('description', 'Unknown error')}"
                ))
            return

        # Get article
        article = None
        if options['article_id']:
            try:
                article = Article.objects.get(id=options['article_id'])
            except Article.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Article #{options['article_id']} not found"))
                return
        elif options['latest']:
            article = Article.objects.filter(
                is_published=True, is_deleted=False
            ).order_by('-created_at').first()
            if not article:
                self.stdout.write(self.style.ERROR('❌ No published articles found'))
                return
        else:
            self.stdout.write(self.style.ERROR(
                '❌ Specify --article-id <ID>, --latest, or --test'
            ))
            return

        self.stdout.write(f'\n📰 Article: {article.title}')
        self.stdout.write(f'   ID: {article.id} | Slug: {article.slug}')

        # Format preview
        post_text = format_telegram_post(article)
        self.stdout.write(f'\n{"─" * 50}')
        # Strip HTML for terminal preview
        import re
        preview = re.sub(r'<[^>]+>', '', post_text)
        self.stdout.write(preview)
        self.stdout.write(f'{"─" * 50}\n')

        # Dry-run mode
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('🔍 Dry-run mode — not sent'))
            return

        # Send
        self.stdout.write('📤 Sending to @freshmotors_news...')
        result = send_to_channel(article, force=options['force'])

        if result.get('ok'):
            msg_id = result.get('result', {}).get('message_id', '?')
            self.stdout.write(self.style.SUCCESS(f'✅ Posted! (msg_id={msg_id})'))
        elif result.get('reason') == 'auto_post_disabled':
            self.stdout.write(self.style.WARNING(
                '⚠️ Auto-post disabled. Use --force to send anyway, '
                'or set TELEGRAM_AUTO_POST=true'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"❌ Failed: {result.get('description', 'Unknown error')}"
            ))
