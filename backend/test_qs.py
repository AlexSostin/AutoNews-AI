import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Brand, CarSpecification
from django.db.models import Count, OuterRef, Subquery, Value, IntegerField

brand_name = 'BYD'

# 1. How CarBrandsListView calculates it:
model_count_subquery = (
    CarSpecification.objects
    .filter(
        make__iexact=OuterRef('name'),
        article__is_published=True,
    )
    .exclude(model='')
    .exclude(model='Not specified')
    .annotate(cnt=Count('model', distinct=True))
    .values('cnt')[:1]
)
article_count_subquery = (
    CarSpecification.objects
    .filter(
        make__iexact=OuterRef('name'),
        article__is_published=True,
    )
    .annotate(cnt=Count('article', distinct=True))
    .values('cnt')[:1]
)

brands = Brand.objects.filter(name=brand_name).annotate(
    _model_count=Subquery(model_count_subquery, output_field=IntegerField(), default=Value(0)),
    _article_count=Subquery(article_count_subquery, output_field=IntegerField(), default=Value(0)),
)
b = brands.first()
print(f"Subquery Method: Models={b._model_count}, Articles={b._article_count}")


# 2. How CarBrandDetailView calculates models:
models = (
    CarSpecification.objects
    .filter(make__iexact=brand_name, article__is_published=True)
    .exclude(model='')
    .exclude(model='Not specified')
    .values('model')
    .annotate(
        trim_count=Count('trim', distinct=True),
        article_count=Count('article', distinct=True),
    )
)
print(f"DetailView Method: Models={len(models)}")


# 3. Correct Subquery Approach:
correct_model_subquery = (
    CarSpecification.objects
    .filter(make__iexact=OuterRef('name'), article__is_published=True)
    .exclude(model='')
    .exclude(model='Not specified')
    .values('make')  # Group by 'make'
    .annotate(cnt=Count('model', distinct=True))
    .values('cnt')
)

brands2 = Brand.objects.filter(name=brand_name).annotate(
    _model_count=Subquery(correct_model_subquery, output_field=IntegerField(), default=Value(0)),
)
b2 = brands2.first()
print(f"Correct Subquery Method: Models={b2._model_count}")

correct_article_subquery = (
    CarSpecification.objects
    .filter(make__iexact=OuterRef('name'), article__is_published=True)
    .values('make')  # Group by 'make'
    .annotate(cnt=Count('article', distinct=True))
    .values('cnt')
)
brands3 = Brand.objects.filter(name=brand_name).annotate(
    _article_count=Subquery(correct_article_subquery, output_field=IntegerField(), default=Value(0)),
)
b3 = brands3.first()
print(f"Correct Subquery Method: Articles={b3._article_count}")


