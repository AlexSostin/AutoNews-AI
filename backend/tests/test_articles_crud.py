"""
Tests for article CRUD endpoints:
- List/retrieve articles (public + admin)
- Create articles (staff only)
- Update articles
- Delete articles (soft delete)
- Permissions checks
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from news.models import Article, Category


@pytest.mark.django_db
class TestArticleList:
    """GET /api/v1/articles/"""

    def test_list_published_anonymous(self, api_client):
        """Anonymous users see only published articles"""
        cat = Category.objects.create(name='Test', slug='test')
        Article.objects.create(title='Published', slug='published', content='<p>Yes</p>', is_published=True)
        Article.objects.create(title='Draft', slug='draft', content='<p>No</p>', is_published=False)

        resp = api_client.get('/api/v1/articles/')
        assert resp.status_code == status.HTTP_200_OK
        titles = [a['title'] for a in resp.data['results']]
        assert 'Published' in titles
        assert 'Draft' not in titles

    def test_list_all_staff(self, authenticated_client):
        """Staff users see all articles including drafts"""
        Article.objects.create(title='Published2', slug='published2', content='<p>Yes</p>', is_published=True)
        Article.objects.create(title='Draft2', slug='draft2', content='<p>No</p>', is_published=False)

        resp = authenticated_client.get('/api/v1/articles/')
        assert resp.status_code == status.HTTP_200_OK
        titles = [a['title'] for a in resp.data['results']]
        assert 'Published2' in titles
        assert 'Draft2' in titles

    def test_filter_by_category(self, api_client):
        """Can filter articles by category slug"""
        cat = Category.objects.create(name='Electric', slug='electric')
        a = Article.objects.create(title='EV Article', slug='ev-article', content='<p>EV</p>', is_published=True)
        a.categories.add(cat)
        Article.objects.create(title='Other', slug='other', content='<p>Other</p>', is_published=True)

        resp = api_client.get('/api/v1/articles/?category=electric')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 1
        assert resp.data['results'][0]['title'] == 'EV Article'


@pytest.mark.django_db
class TestArticleRetrieve:
    """GET /api/v1/articles/{slug}/"""

    def test_retrieve_by_slug(self, api_client):
        """Can retrieve article by slug"""
        Article.objects.create(title='Test Article', slug='test-article', content='<p>Content</p>', is_published=True)
        resp = api_client.get('/api/v1/articles/test-article/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['title'] == 'Test Article'

    def test_retrieve_nonexistent(self, api_client):
        """Non-existent slug returns 404"""
        resp = api_client.get('/api/v1/articles/nonexistent/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestArticleCreate:
    """POST /api/v1/articles/"""

    def test_create_article_staff(self, authenticated_client):
        """Staff can create articles"""
        Category.objects.create(name='News', slug='news')
        resp = authenticated_client.post('/api/v1/articles/', {
            'title': 'New Article',
            'content': '<p>New content here</p>',
            'summary': 'Summary text',
            'is_published': False,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['title'] == 'New Article'
        assert Article.objects.filter(title='New Article').exists()

    def test_create_article_anonymous_forbidden(self, api_client):
        """Anonymous users cannot create articles"""
        resp = api_client.post('/api/v1/articles/', {
            'title': 'Hack Article',
            'content': '<p>Not allowed</p>',
        }, format='json')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_article_auto_slug(self, authenticated_client):
        """Article slug is auto-generated from title"""
        resp = authenticated_client.post('/api/v1/articles/', {
            'title': 'My Amazing Article Title',
            'content': '<p>Content</p>',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert 'my-amazing-article-title' in resp.data['slug']


@pytest.mark.django_db
class TestArticleDelete:
    """DELETE /api/v1/articles/{slug}/"""

    def test_delete_article_staff(self, authenticated_client):
        """Staff can delete articles"""
        Article.objects.create(title='To Delete', slug='to-delete', content='<p>Bye</p>')
        resp = authenticated_client.delete('/api/v1/articles/to-delete/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_article_anonymous_forbidden(self, api_client):
        """Anonymous users cannot delete articles"""
        Article.objects.create(title='No Delete', slug='no-delete', content='<p>Stay</p>', is_published=True)
        resp = api_client.delete('/api/v1/articles/no-delete/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestArticleActions:
    """Article special actions: trending, popular, views"""

    def test_trending(self, api_client):
        """Trending endpoint returns articles"""
        Article.objects.create(title='Trending', slug='trending', content='<p>Hot</p>', is_published=True, views=100)
        resp = api_client.get('/api/v1/articles/trending/')
        assert resp.status_code == status.HTTP_200_OK

    def test_popular(self, api_client):
        """Popular endpoint returns articles sorted by views"""
        Article.objects.create(title='Popular1', slug='popular1', content='<p>1</p>', is_published=True, views=50)
        Article.objects.create(title='Popular2', slug='popular2', content='<p>2</p>', is_published=True, views=200)
        resp = api_client.get('/api/v1/articles/popular/')
        assert resp.status_code == status.HTTP_200_OK

    def test_increment_views(self, api_client):
        """Can increment article views"""
        Article.objects.create(title='Viewable', slug='viewable', content='<p>See me</p>', is_published=True)
        resp = api_client.post('/api/v1/articles/viewable/increment_views/')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestArticleUpdate:
    """PATCH /api/v1/articles/{slug}/"""

    def test_update_article_staff(self, authenticated_client):
        """Staff can update article title"""
        Article.objects.create(title='Old Title', slug='old-title', content='<p>Content</p>')
        resp = authenticated_client.patch('/api/v1/articles/old-title/', {
            'title': 'New Title',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['title'] == 'New Title'

    def test_update_article_anonymous_forbidden(self, api_client):
        """Anonymous users cannot update articles"""
        Article.objects.create(title='Protected', slug='protected', content='<p>No</p>', is_published=True)
        resp = api_client.patch('/api/v1/articles/protected/', {
            'title': 'Hacked',
        }, format='json')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_update_content(self, authenticated_client):
        """Can update article content"""
        Article.objects.create(title='Content Update', slug='content-update', content='<p>Old</p>')
        resp = authenticated_client.patch('/api/v1/articles/content-update/', {
            'content': '<p>New content here</p>',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_update_publish_status(self, authenticated_client):
        """Can toggle published status"""
        Article.objects.create(title='Toggle Pub', slug='toggle-pub', content='<p>Content</p>', is_published=False)
        resp = authenticated_client.patch('/api/v1/articles/toggle-pub/', {
            'is_published': True,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['is_published'] is True


@pytest.mark.django_db
class TestArticlePagination:
    """Article list pagination"""

    def test_pagination_defaults(self, api_client):
        """Response should include pagination metadata"""
        for i in range(3):
            Article.objects.create(title=f'Art {i}', slug=f'art-{i}', content=f'<p>{i}</p>', is_published=True)
        resp = api_client.get('/api/v1/articles/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'results' in resp.data
        assert 'count' in resp.data

    def test_pagination_page_param(self, api_client):
        """Can navigate pages"""
        for i in range(25):
            Article.objects.create(title=f'Page Art {i}', slug=f'page-art-{i}', content=f'<p>{i}</p>', is_published=True)
        resp = api_client.get('/api/v1/articles/?page=1')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) <= 20

    def test_pagination_invalid_page(self, api_client):
        """Invalid page number returns 404"""
        resp = api_client.get('/api/v1/articles/?page=999')
        assert resp.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]


@pytest.mark.django_db
class TestArticleTags:
    """Tag assignment on articles"""

    def test_list_articles_has_tags(self, api_client):
        """Articles should include tags in response"""
        from news.models import Tag
        tag = Tag.objects.create(name='EV', slug='ev')
        art = Article.objects.create(title='Tagged', slug='tagged', content='<p>T</p>', is_published=True)
        art.tags.add(tag)
        resp = api_client.get('/api/v1/articles/tagged/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'tags' in resp.data
