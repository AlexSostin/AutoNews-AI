from django.shortcuts import get_object_or_404, redirect
from .models import Article


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True, is_deleted=False)
    comments = article.comments.filter(is_approved=True).order_by('-created_at')

    # Handle comment submission
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        content = request.POST.get('content')

        if name and email and content:
            from .models import Comment
            Comment.objects.create(
                article=article,
                name=name,
                email=email,
                content=content,
                is_approved=False  # Requires moderation
            )
            from django.contrib import messages
            messages.success(request, '✅ Comment submitted! It will appear after moderation.')
            return redirect('news:article_detail', slug=slug)

    from django.shortcuts import render
    return render(request, 'news/article_detail.html', {
        'article': article,
        'comments': comments
    })




def serve_media_with_cors(request, path):
    """Serve media files with CORS headers for cross-origin access"""
    from django.conf import settings
    from django.http import FileResponse, Http404
    import os
    
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if not os.path.exists(file_path):
        raise Http404("Media file not found")
    
    response = FileResponse(open(file_path, 'rb'))
    
    # Add CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Set content type based on file extension
    ext = os.path.splitext(path)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
    }
    if ext in content_types:
        response['Content-Type'] = content_types[ext]
    
    return response


from django.views.decorators.cache import cache_page

@cache_page(86400)  # Cache for 24 hours — content is static
def robots_txt(request):
    """Serve robots.txt for search engine crawlers"""
    from django.http import HttpResponse
    
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "# Disallow admin and private areas",
        "Disallow: /admin/",
        "Disallow: /api/v1/admin/",
        "",
        "# Allow public content",
        "Allow: /articles/",
        "Allow: /categories/",
        "Allow: /feed/",
        "",
        "# Sitemap",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    
    return HttpResponse("\n".join(lines), content_type="text/plain")
