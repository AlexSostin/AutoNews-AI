from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout
from django.db.models import Q
from .models import Article, Category

def home(request):
    articles = Article.objects.filter(is_published=True).order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'news/home.html', {'articles': articles, 'categories': categories})

def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
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
    
    return render(request, 'news/article_detail.html', {
        'article': article,
        'comments': comments
    })

def category_list(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = category.articles.filter(is_published=True).order_by('-created_at')
    return render(request, 'news/home.html', {'articles': articles, 'current_category': category})

def logout_view(request):
    logout(request)
    return redirect('news:home')

def about_page(request):
    return render(request, 'news/about.html')

def privacy_page(request):
    return render(request, 'news/privacy.html')

def contact_page(request):
    return render(request, 'news/contact.html')

def search(request):
    query = request.GET.get('q', '')
    results = []
    
    if query:
        results = Article.objects.filter(
            Q(title__icontains=query) | 
            Q(summary__icontains=query) | 
            Q(content__icontains=query) |
            Q(category__name__icontains=query) |
            Q(tags__name__icontains=query),
            is_published=True
        ).distinct().order_by('-created_at')
    
    return render(request, 'news/search_results.html', {
        'query': query,
        'results': results,
        'count': results.count() if results else 0
    })

def rate_article(request, slug):
    """AJAX endpoint for rating articles"""
    from django.http import JsonResponse
    from .models import Rating
    
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug, is_published=True)
        rating_value = request.POST.get('rating')
        
        if not rating_value or not rating_value.isdigit() or int(rating_value) not in range(1, 6):
            return JsonResponse({'error': 'Invalid rating'}, status=400)
        
        # Get user IP
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
        # Check if already voted
        existing_rating = Rating.objects.filter(article=article, ip_address=ip_address).first()
        if existing_rating:
            return JsonResponse({'error': 'You have already rated this article'}, status=400)
        
        # Create rating
        Rating.objects.create(
            article=article,
            ip_address=ip_address,
            rating=int(rating_value)
        )
        
        return JsonResponse({
            'success': True,
            'average': article.average_rating(),
            'count': article.rating_count()
        })
    
    return JsonResponse({'error': 'Invalid method'}, status=405)
