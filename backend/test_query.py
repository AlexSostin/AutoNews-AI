from news.models import Article; print(Article.objects.filter(title__iregex=r'\y06\y').query)
