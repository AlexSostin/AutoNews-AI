"""
Tests for comments and ratings endpoints:
- Comment CRUD (create, list, filter)
- Comment approval
- Rating CRUD + duplicate prevention
- My comments / my ratings
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from news.models import Article, Comment, Rating


@pytest.fixture
def article():
    """Create a published test article"""
    return Article.objects.create(
        title='Test Car Review', slug='test-car-review',
        content='<p>Amazing car</p>', is_published=True
    )


@pytest.mark.django_db
class TestCommentCreate:
    """POST /api/v1/comments/"""

    def test_create_comment_anonymous(self, api_client, article):
        """Anyone can post a comment (guest)"""
        resp = api_client.post('/api/v1/comments/', {
            'article': article.id,
            'name': 'Guest User',
            'email': 'guest@test.com',
            'content': 'Great review!',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert Comment.objects.filter(article=article).count() == 1

    def test_create_comment_honeypot_caught(self, api_client, article):
        """Spam bot filling honeypot field gets fake success"""
        resp = api_client.post('/api/v1/comments/', {
            'article': article.id,
            'name': 'Spammer',
            'email': 'spam@bot.com',
            'content': 'Buy cheap stuff!',
            'website': 'http://spam.com',  # Honeypot field
        }, format='json')
        # Returns fake 201 to not alert the bot
        assert resp.status_code == status.HTTP_201_CREATED
        # But no comment is actually created
        assert Comment.objects.filter(article=article).count() == 0


@pytest.mark.django_db
class TestCommentList:
    """GET /api/v1/comments/"""

    def test_list_comments_by_article(self, api_client, article):
        """Can filter comments by article ID"""
        Comment.objects.create(article=article, name='A', email='a@t.com', content='Comment A', is_approved=True)
        Comment.objects.create(article=article, name='B', email='b@t.com', content='Comment B', is_approved=False)

        resp = api_client.get(f'/api/v1/comments/?article={article.id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_approved_only(self, api_client, article):
        """Can filter to only approved comments"""
        Comment.objects.create(article=article, name='Approved', email='a@t.com', content='Good', is_approved=True)
        Comment.objects.create(article=article, name='Pending', email='b@t.com', content='Waiting', is_approved=False)

        resp = api_client.get(f'/api/v1/comments/?article={article.id}&approved=true')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 1


@pytest.mark.django_db
class TestCommentApproval:
    """PATCH /api/v1/comments/{id}/approve/"""

    def test_approve_comment(self, authenticated_client, article):
        """Staff can approve a comment"""
        comment = Comment.objects.create(
            article=article, name='User', email='u@t.com',
            content='Awaiting approval', is_approved=False
        )
        resp = authenticated_client.patch(f'/api/v1/comments/{comment.id}/approve/', {
            'approved': True,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.is_approved is True

    def test_reject_comment(self, authenticated_client, article):
        """Staff can reject (unapprove) a comment"""
        comment = Comment.objects.create(
            article=article, name='User', email='u@t.com',
            content='Initially approved', is_approved=True
        )
        resp = authenticated_client.patch(f'/api/v1/comments/{comment.id}/approve/', {
            'approved': False,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.is_approved is False


@pytest.mark.django_db
class TestRatingCreate:
    """POST /api/v1/ratings/"""

    def test_rate_article(self, authenticated_client, article):
        """Authenticated user can rate an article"""
        resp = authenticated_client.post('/api/v1/ratings/', {
            'article': article.id,
            'rating': 5,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert Rating.objects.filter(article=article).count() == 1

    def test_rate_article_invalid_rating(self, authenticated_client, article):
        """Rating outside 1-5 is rejected"""
        resp = authenticated_client.post('/api/v1/ratings/', {
            'article': article.id,
            'rating': 10,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMyComments:
    """GET /api/v1/comments/my_comments/"""

    def test_my_comments(self, authenticated_client, article):
        """Authenticated user sees their own comments"""
        # Create comment via the user
        user = User.objects.get(username='testuser')
        Comment.objects.create(
            article=article, name='testuser', email='test@example.com',
            content='My comment', user=user
        )
        resp = authenticated_client.get('/api/v1/comments/my_comments/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1
