from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone
from datetime import timedelta
from .models import Article, Category, Tag, CarSpecification, SiteSettings, Comment, Rating, ArticleImage, Favorite
import sys
import os

# Add ai_engine to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ai_engine'))

# Custom admin site with stats
class CustomAdminSite(admin.AdminSite):
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get statistics
        extra_context['total_articles'] = Article.objects.count()
        extra_context['published_articles'] = Article.objects.filter(is_published=True).count()
        extra_context['total_categories'] = Category.objects.count()
        extra_context['total_tags'] = Tag.objects.count()
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        extra_context['recent_count'] = Article.objects.filter(created_at__gte=week_ago).count()
        
        return super().index(request, extra_context)

class YouTubeGenerateForm(forms.Form):
    youtube_url = forms.URLField(
        label="YouTube Video URL",
        widget=forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=...', 'size': 60})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        help_text="Leave empty to auto-create 'Reviews' category"
    )

class CarSpecificationInline(admin.StackedInline):
    model = CarSpecification
    can_delete = True
    verbose_name_plural = 'Car Specifications'
    extra = 0
    max_num = 1

class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1
    fields = ('image', 'caption', 'order')
    verbose_name = 'Gallery Image'
    verbose_name_plural = 'Image Gallery'

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'is_deleted', 'created_at', 'view_count')
    list_filter = ('is_published', 'is_deleted', 'category', 'created_at', 'updated_at')
    search_fields = ('title', 'content', 'summary', 'seo_title', 'seo_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CarSpecificationInline, ArticleImageInline]
    date_hierarchy = 'created_at'
    list_editable = ('is_published',)
    actions = ['publish_articles', 'unpublish_articles', 'soft_delete_articles', 'restore_articles']
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        """Show only non-deleted articles by default"""
        qs = super().get_queryset(request)
        if not request.GET.get('is_deleted__exact'):
            return qs.filter(is_deleted=False)
        return qs
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_youtube_button'] = True
        return super().changelist_view(request, extra_context)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'tags')
        }),
        ('Images (Screenshots from Video)', {
            'fields': ('image', 'image_2', 'image_3'),
            'description': 'Upload manually or auto-extracted from YouTube video during generation'
        }),
        ('Source', {
            'fields': ('youtube_url',),
            'description': 'YouTube URL used for AI generation (if applicable)'
        }),
        ('Content', {
            'fields': ('summary', 'content'),
            'classes': ('wide',)
        }),
        ('SEO Settings', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',)
        }),
        ('Publishing & Stats', {
            'fields': ('is_published', 'views', 'created_at', 'updated_at')
        })
    )
    
    def view_count(self, obj):
        return "N/A"  # Placeholder for future analytics
    view_count.short_description = 'Views'
    
    def _extract_spec(self, text, pattern, default):
        """Helper to extract car specifications from analysis text"""
        import re
        # Try multiple patterns for better matching
        patterns = [
            rf'{pattern}[:\s]+([0-9.,]+\s*[a-zA-Z]*)',  # Numbers with units
            rf'{pattern}[:\s]+([^,\n\.]+)',  # Any text until comma/newline/period
            rf'\b{pattern}\b[:\s]*([^\n,\.]+)',  # Word boundary version
        ]
        
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and value.lower() not in ['unknown', 'n/a', 'na', 'none']:
                    return value
        return default
    
    def publish_articles(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} article(s) published successfully.')
    publish_articles.short_description = "Publish selected articles"
    
    def unpublish_articles(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} article(s) unpublished successfully.')
    unpublish_articles.short_description = "Unpublish selected articles"
    
    def soft_delete_articles(self, request, queryset):
        """Mark articles as deleted instead of removing from database"""
        updated = queryset.update(is_deleted=True, is_published=False)
        self.message_user(request, f'{updated} article(s) marked as deleted. You can now recreate them.')
    soft_delete_articles.short_description = "Delete selected articles (soft delete)"
    
    def restore_articles(self, request, queryset):
        """Restore soft-deleted articles"""
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} article(s) restored.')
    restore_articles.short_description = "Restore deleted articles"
    
    def delete_model(self, request, obj):
        """Override delete to use soft delete"""
        obj.is_deleted = True
        obj.is_published = False
        obj.save()
    
    def delete_queryset(self, request, queryset):
        """Override bulk delete to use soft delete"""
        queryset.update(is_deleted=True, is_published=False)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate-from-youtube/', self.admin_site.admin_view(self.generate_from_youtube_view), name='news_article_generate_youtube'),
        ]
        return custom_urls + urls
    
    def generate_from_youtube_view(self, request):
        if request.method == 'POST':
            form = YouTubeGenerateForm(request.POST)
            if form.is_valid():
                youtube_url = form.cleaned_data['youtube_url']
                category = form.cleaned_data.get('category')
                
                # Generate unique task ID for WebSocket
                import uuid
                task_id = str(uuid.uuid4())
                
                try:
                    # Import AI engine modules
                    from ai_engine.modules.downloader import download_thumbnail_only
                    from ai_engine.modules.transcriber import transcribe_from_youtube
                    from ai_engine.modules.analyzer import analyze_transcript
                    from ai_engine.modules.article_generator import generate_article
                    from django.utils.text import slugify
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    import re
                    import random
                    
                    channel_layer = get_channel_layer()
                    
                    def send_progress(step, progress, message):
                        """Helper to send WebSocket progress updates"""
                        if channel_layer:
                            async_to_sync(channel_layer.group_send)(
                                f"generation_{task_id}",
                                {
                                    "type": "send_progress",
                                    "step": step,
                                    "progress": progress,
                                    "message": message
                                }
                            )
                    
                    self.message_user(request, f'⏳ Starting AI generation... Task ID: {task_id}', level='INFO')
                    
                    # Step 1: Download thumbnail
                    send_progress(1, 10, "📥 Downloading thumbnail...")
                    video_id, thumbnail_path, video_title = download_thumbnail_only(youtube_url)
                    
                    # Step 2: Get subtitles
                    send_progress(2, 30, "📝 Extracting subtitles...")
                    transcript = transcribe_from_youtube(youtube_url)
                    
                    # Step 3: Analyze with Groq
                    send_progress(3, 50, "🤖 Analyzing content with AI...")
                    analysis = analyze_transcript(transcript)
                    
                    # Step 4: Generate article with Groq
                    send_progress(4, 75, "✍️ Generating article...")
                    article_html = generate_article(analysis)
                    
                    # Step 5: Save to database
                    send_progress(5, 90, "💾 Saving to database...")
                    
                    # Extract title from generated HTML
                    match = re.search(r'<h2>(.*?)</h2>', article_html)
                    raw_title = match.group(1) if match else "Auto-Generated Article"
                    
                    # Clean up title: remove HTML tags, extra spaces, decode entities
                    import html
                    title = html.unescape(raw_title)  # Decode HTML entities like &amp;
                    title = re.sub(r'<[^>]+>', '', title)  # Remove any HTML tags
                    title = re.sub(r'\s+', ' ', title).strip()  # Normalize whitespace
                    
                    # Capitalize properly if needed
                    if title and not title[0].isupper():
                        title = title.capitalize()
                    
                    # Limit length
                    if len(title) > 200:
                        title = title[:197] + '...'
                    
                    print(f"Cleaned title: {title}")
                    
                    # Extract summary (first paragraph)
                    summary_match = re.search(r'<p>(.*?)</p>', article_html)
                    summary = summary_match.group(1) if summary_match else "AI-generated automotive content"
                    
                    # Generate unique slug
                    base_slug = slugify(title)
                    slug = base_slug
                    counter = 1
                    while Article.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    # Create article
                    cat_name = category.name if category else "Reviews"
                    article = Article.objects.create(
                        title=title,
                        slug=slug,
                        summary=summary[:300],  # Limit summary length
                        content=article_html,
                        category=category if category else Category.objects.get_or_create(name=cat_name, defaults={'slug': 'reviews'})[0],
                        is_published=False  # Save as draft
                    )
                    
                    # Add thumbnail if available
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        from django.core.files import File
                        with open(thumbnail_path, 'rb') as f:
                            article.image.save(os.path.basename(thumbnail_path), File(f), save=True)
                    
                    # Extract 3 screenshots for gallery
                    send_progress(5, 85, "📸 Extracting video screenshots...")
                    try:
                        from ai_engine.modules.downloader import extract_video_screenshots
                        from django.core.files import File
                        
                        screenshot_paths = extract_video_screenshots(youtube_url, count=3)
                        
                        for i, screenshot_path in enumerate(screenshot_paths):
                            if os.path.exists(screenshot_path):
                                with open(screenshot_path, 'rb') as f:
                                    ArticleImage.objects.create(
                                        article=article,
                                        image=File(f, name=os.path.basename(screenshot_path)),
                                        caption=f"View {i+1}",
                                        order=i
                                    )
                                print(f"✓ Gallery image {i+1} added")
                    except Exception as gallery_error:
                        print(f"⚠ Could not create gallery: {gallery_error}")
                    
                    # Extract and create Car Specifications from analysis
                    from news.models import CarSpecification
                    try:
                        # Try to extract from title first (e.g., "2026 Tesla Model 3")
                        title_parts = title.split()
                        year_from_title = next((p for p in title_parts if p.isdigit() and len(p) == 4), '2026')
                        
                        # Combine analysis and title for better extraction
                        full_text = f"{title}\n{analysis}"
                        
                        # Parse analysis for car specs with improved patterns
                        car_specs = CarSpecification.objects.create(
                            article=article,
                            make=self._extract_spec(full_text, r'(?:make|brand|manufacturer)', 'Unknown'),
                            model=self._extract_spec(full_text, r'(?:model|vehicle)', 'Unknown'),
                            year=year_from_title,
                            engine=self._extract_spec(full_text, r'(?:engine|motor|powertrain)', 'Not specified'),
                            horsepower=self._extract_spec(full_text, r'(?:horsepower|hp|power)', 'Not specified'),
                            torque=self._extract_spec(full_text, r'(?:torque|nm|lb-ft)', 'Not specified'),
                            acceleration=self._extract_spec(full_text, r'(?:0-60|0-100|acceleration)', 'Not specified'),
                            top_speed=self._extract_spec(full_text, r'(?:top speed|max speed|maximum speed)', 'Not specified'),
                            battery_capacity=self._extract_spec(full_text, r'(?:battery|kwh|kWh|capacity)', 'Not specified'),
                            range_km=self._extract_spec(full_text, r'(?:range|km|miles|distance)', 'Not specified'),
                            price_usd=self._extract_spec(full_text, r'(?:price|cost|starting|msrp|\\$)', 'Not specified')
                        )
                        print(f"✓ Car specifications created: {car_specs.make} {car_specs.model} ({car_specs.year})")
                    except Exception as spec_error:
                        print(f"⚠ Could not create car specs: {spec_error}")
                    
                    # Final progress update
                    send_progress(6, 100, f"✅ Article '{article.title}' generated!")
                    
                    self.message_user(request, f'✅ Article "{article.title}" generated successfully! Check and publish when ready.')
                    return redirect('admin:news_article_change', article.id)
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.message_user(request, f'❌ Error: {str(e)}', level='ERROR')
                    print(f"Full error:\n{error_details}")  # Log to console
        else:
            form = YouTubeGenerateForm()
            task_id = None
        
        context = {
            'form': form,
            'title': 'Generate Article from YouTube',
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
            'has_permission': True,
            'task_id': task_id if request.method == 'POST' else None,
        }
        return render(request, 'admin/news/generate_youtube.html', context)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'usage_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def usage_count(self, obj):
        return obj.article_set.count()
    usage_count.short_description = 'Used in Articles'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Prevent adding more than one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('site_name', 'site_description', 'contact_email')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'youtube_url'),
            'classes': ('collapse',)
        }),
        ('SEO & Analytics', {
            'fields': ('default_meta_description', 'google_analytics_id', 'google_adsense_id'),
            'classes': ('collapse',)
        }),
        ('Footer', {
            'fields': ('footer_text',)
        })
    )

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'article_link', 'created_at', 'approval_status', 'content_preview')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('name', 'email', 'content', 'article__title')
    actions = ['approve_comments', 'reject_comments']
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_select_related = ('article',)  # Оптимизация - загружаем статью вместе с комментарием
    
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'content', 'is_approved', 'created_at')
        }),
        ('Article', {
            'fields': ('article',)
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Comment'
    
    def approval_status(self, obj):
        """Цветной статус одобрения"""
        from django.utils.html import format_html
        if obj.is_approved:
            return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">⏳ Pending</span>')
    approval_status.short_description = 'Status'
    
    def article_link(self, obj):
        """Ссылка на статью на сайте"""
        from django.utils.html import format_html
        # Next.js использует URL без trailing slash
        url = f"http://localhost:3000/articles/{obj.article.slug}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.article.title)
    article_link.short_description = 'Article'
    
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} comment(s) approved.')
    approve_comments.short_description = '✓ Approve selected comments'
    
    def reject_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} comment(s) rejected.')
    reject_comments.short_description = '✗ Reject selected comments'

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('article', 'rating', 'ip_address', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('article__title', 'ip_address')
    readonly_fields = ('created_at', 'ip_address')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        # Ratings are created only from frontend
        return False
    
    fieldsets = (
        ('Rating Information', {
            'fields': ('article', 'rating', 'ip_address', 'created_at')
        }),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'article__title')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        # Favorites are created only from frontend
        return False
