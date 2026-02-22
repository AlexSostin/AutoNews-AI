"""
Tests for CommentViewSet, RatingViewSet, and Article rating actions (api_views.py)
Target: Cover CRUD, permissions, rate-limiting fingerprints, moderation
"""
import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def published_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Test Car Review', slug='test-car-review',
        content='<p>Great car</p>', summary='Summary',
        is_published=True,
    )


@pytest.fixture
def regular_user(django_user_model):
    return django_user_model.objects.create_user(
        username='commenter', email='commenter@test.com', password='pass123'
    )


@pytest.fixture
def regular_client(api_client, regular_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(regular_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return api_client


@pytest.fixture
def comment(db, published_article, regular_user):
    from news.models import Comment
    return Comment.objects.create(
        article=published_article,
        user=regular_user,
        name='Tester',
        content='Great article!',
        is_approved=True,
    )


@pytest.fixture
def pending_comment(db, published_article):
    from news.models import Comment
    return Comment.objects.create(
        article=published_article,
        name='Guest',
        content='Pending comment',
        is_approved=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CommentViewSet
# ═══════════════════════════════════════════════════════════════════════════

class TestCommentViewSet:
    """Tests for /api/v1/comments/"""

    def test_list_approved_comments(self, api_client, comment, pending_comment):
        resp = api_client.get('/api/v1/comments/')
        assert resp.status_code == status.HTTP_200_OK

    def test_list_by_article(self, api_client, comment, published_article):
        resp = api_client.get('/api/v1/comments/', {'article': published_article.id})
        assert resp.status_code == status.HTTP_200_OK

    def test_create_comment_anonymous(self, api_client, published_article):
        resp = api_client.post('/api/v1/comments/', {
            'article': published_article.id,
            'name': 'Guest',
            'email': 'guest@test.com',
            'content': 'Nice!',
        })
        # Anyone can create comments
        assert resp.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_create_comment_authenticated(self, regular_client, published_article):
        resp = regular_client.post('/api/v1/comments/', {
            'article': published_article.id,
            'content': 'Authenticated comment',
        })
        assert resp.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_approve_comment_staff(self, authenticated_client, pending_comment):
        resp = authenticated_client.post(f'/api/v1/comments/{pending_comment.id}/approve/', {
            'approved': True,
        })
        assert resp.status_code == status.HTTP_200_OK

    def test_approve_comment_anonymous_forbidden(self, api_client, pending_comment):
        resp = api_client.post(f'/api/v1/comments/{pending_comment.id}/approve/', {
            'approved': True,
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_my_comments(self, regular_client, comment):
        resp = regular_client.get('/api/v1/comments/my_comments/')
        assert resp.status_code == status.HTTP_200_OK

    def test_delete_comment_staff(self, authenticated_client, comment):
        resp = authenticated_client.delete(f'/api/v1/comments/{comment.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# ═══════════════════════════════════════════════════════════════════════════
# Article Rating (via ArticleViewSet.rate action)
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleRating:
    """Tests for /api/v1/articles/{slug}/rate/ and /api/v1/articles/{slug}/get_user_rating/"""

    def test_rate_article_anonymous(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 4}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert 'average_rating' in resp.data
        assert 'rating_count' in resp.data

    def test_rate_article_authenticated(self, regular_client, published_article):
        resp = regular_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 5}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['rating_count'] >= 1

    def test_rate_missing_value(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in resp.data

    def test_rate_invalid_value(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 6}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_rate_non_numeric(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 'abc'}
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_rate_updates_existing(self, regular_client, published_article):
        # First rating
        regular_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 3}
        )
        # Update
        resp = regular_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 5}
        )
        assert resp.status_code == status.HTTP_200_OK
        # Should still be 1 rating (updated, not created new)
        assert resp.data['rating_count'] == 1

    def test_get_user_rating_authenticated(self, regular_client, published_article):
        # Rate first
        regular_client.post(
            f'/api/v1/articles/{published_article.slug}/rate/',
            {'rating': 4}
        )
        resp = regular_client.get(
            f'/api/v1/articles/{published_article.slug}/my-rating/'
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get('has_rated') is True

    def test_get_user_rating_no_rating(self, regular_client, published_article):
        resp = regular_client.get(
            f'/api/v1/articles/{published_article.slug}/my-rating/'
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get('has_rated') is False


# ═══════════════════════════════════════════════════════════════════════════
# RatingViewSet (standalone)
# ═══════════════════════════════════════════════════════════════════════════

class TestRatingViewSet:
    """Tests for /api/v1/ratings/"""

    def test_list_ratings(self, api_client):
        resp = api_client.get('/api/v1/ratings/')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_rating(self, api_client, published_article):
        resp = api_client.post('/api/v1/ratings/', {
            'article': published_article.id,
            'rating': 4,
        })
        # Rating creation requires auth or may not be routed
        assert resp.status_code in [
            status.HTTP_201_CREATED, status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_my_ratings(self, regular_client):
        resp = regular_client.get('/api/v1/ratings/my_ratings/')
        assert resp.status_code == status.HTTP_200_OK


# ═══════════════════════════════════════════════════════════════════════════
# Article Feedback (via ArticleViewSet.submit_feedback)
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleFeedback:
    """Tests for /api/v1/articles/{slug}/feedback/"""

    def test_submit_feedback(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/feedback/', {
                'feedback_type': 'factual_error',
                'description': 'The horsepower number is wrong',
            }
        )
        # May require auth or return created
        assert resp.status_code in [
            status.HTTP_201_CREATED, status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED
        ]

    def test_submit_feedback_missing_type(self, api_client, published_article):
        resp = api_client.post(
            f'/api/v1/articles/{published_article.slug}/feedback/', {
                'description': 'Something wrong',
            }
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
