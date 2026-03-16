"""
Tests for YouTube Video Inbox feature.
Covers: list, scan, approve, dismiss, bulk actions, filters, stats.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from news.models import YouTubeChannel, YouTubeVideoCandidate, Article


@pytest.fixture
def youtube_channel(db):
    """Create an enabled YouTube channel."""
    return YouTubeChannel.objects.create(
        name='BMW Official',
        channel_url='https://www.youtube.com/@BMW',
        is_enabled=True,
    )


@pytest.fixture
def video_candidates(youtube_channel):
    """Create a set of video candidates across statuses."""
    now = timezone.now()
    vids = []
    for i, (st, title) in enumerate([
        ('new', '2026 BMW X5 Electric SUV Review'),
        ('new', '2026 BMW iX Hybrid Walk-around'),
        ('new', 'BMW M4 GT3 Price Breakdown'),
        ('approved', '2026 BMW i7 EV Test Drive'),
        ('dismissed', '2025 BMW X1 Interior Tour'),
    ]):
        vids.append(YouTubeVideoCandidate.objects.create(
            channel=youtube_channel,
            video_id=f'vid_{i}',
            title=title,
            thumbnail_url=f'https://i.ytimg.com/vi/vid_{i}/hqdefault.jpg',
            duration_seconds=300 + i * 60,
            view_count=10000 * (i + 1),
            published_at=now - timedelta(days=i),
            status=st,
        ))
    return vids


@pytest.mark.django_db
class TestVideoInboxList:
    """GET /api/v1/video-inbox/"""

    def test_list_default_shows_new(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data['results']
        assert all(v['status'] == 'new' for v in results)
        assert len(results) == 3

    def test_list_filter_approved(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/?status=approved')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 1

    def test_list_filter_all(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/?status=all')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 5

    def test_search_filter(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/?status=all&search=iX')
        assert resp.status_code == status.HTTP_200_OK
        assert any('iX' in v['title'] for v in resp.data['results'])

    def test_capsule_filter_ev(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/?status=all&capsule=ev')
        assert resp.status_code == status.HTTP_200_OK
        for v in resp.data['results']:
            title_lower = v['title'].lower()
            assert any(kw in title_lower for kw in ['ev', 'electric', 'bev', 'battery'])

    def test_ordering_by_views(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/?status=all&ordering=-view_count')
        assert resp.status_code == status.HTTP_200_OK
        views = [v['view_count'] for v in resp.data['results']]
        assert views == sorted(views, reverse=True)

    def test_anonymous_forbidden(self, api_client, video_candidates):
        resp = api_client.get('/api/v1/video-inbox/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_old_videos_excluded(self, authenticated_client, youtube_channel):
        """Videos older than 30 days should be excluded."""
        old = timezone.now() - timedelta(days=35)
        YouTubeVideoCandidate.objects.create(
            channel=youtube_channel, video_id='old_vid', title='Old Video',
            published_at=old, status='new',
        )
        resp = authenticated_client.get('/api/v1/video-inbox/')
        assert resp.status_code == status.HTTP_200_OK
        assert not any(v['video_id'] == 'old_vid' for v in resp.data['results'])

    def test_serializer_has_article_fields(self, authenticated_client, video_candidates):
        """Serializer should include article existence fields."""
        resp = authenticated_client.get('/api/v1/video-inbox/?status=all')
        assert resp.status_code == status.HTTP_200_OK
        first = resp.data['results'][0]
        assert 'has_article' in first
        assert 'article_status' in first
        assert 'article_slug' in first
        assert 'similar_articles_count' in first

    def test_channel_filter(self, authenticated_client, video_candidates, youtube_channel):
        resp = authenticated_client.get(f'/api/v1/video-inbox/?status=all&channel_id={youtube_channel.id}')
        assert resp.status_code == status.HTTP_200_OK
        assert all(v['channel'] == youtube_channel.id for v in resp.data['results'])


@pytest.mark.django_db
class TestVideoInboxApprove:
    """POST /api/v1/video-inbox/{id}/approve/"""

    def test_approve_video(self, authenticated_client, video_candidates):
        vid = video_candidates[0]  # status='new'
        resp = authenticated_client.post(f'/api/v1/video-inbox/{vid.id}/approve/')
        assert resp.status_code == status.HTTP_200_OK
        vid.refresh_from_db()
        assert vid.status == 'approved'

    def test_approve_already_approved(self, authenticated_client, video_candidates):
        vid = video_candidates[3]  # status='approved'
        # Must use the ID directly — try approving an already-approved video
        resp = authenticated_client.post(f'/api/v1/video-inbox/{vid.id}/approve/?status=all')
        assert resp.status_code == status.HTTP_200_OK
        assert 'Already approved' in resp.data['message']


@pytest.mark.django_db
class TestVideoInboxDismiss:
    """POST /api/v1/video-inbox/{id}/dismiss/"""

    def test_dismiss_video(self, authenticated_client, video_candidates):
        vid = video_candidates[0]
        resp = authenticated_client.post(f'/api/v1/video-inbox/{vid.id}/dismiss/')
        assert resp.status_code == status.HTTP_200_OK
        vid.refresh_from_db()
        assert vid.status == 'dismissed'


@pytest.mark.django_db
class TestVideoInboxBulkActions:
    """Bulk approve/dismiss"""

    def test_bulk_approve(self, authenticated_client, video_candidates):
        ids = [v.id for v in video_candidates if v.status == 'new']
        resp = authenticated_client.post('/api/v1/video-inbox/bulk_approve/', {'ids': ids}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 3
        for vid_id in ids:
            assert YouTubeVideoCandidate.objects.get(id=vid_id).status == 'approved'

    def test_bulk_dismiss(self, authenticated_client, video_candidates):
        ids = [v.id for v in video_candidates[:2]]
        resp = authenticated_client.post('/api/v1/video-inbox/bulk_dismiss/', {'ids': ids}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        for vid_id in ids:
            assert YouTubeVideoCandidate.objects.get(id=vid_id).status == 'dismissed'

    def test_bulk_approve_empty(self, authenticated_client, video_candidates):
        resp = authenticated_client.post('/api/v1/video-inbox/bulk_approve/', {'ids': []}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestVideoInboxStats:
    """GET /api/v1/video-inbox/stats/"""

    def test_stats(self, authenticated_client, video_candidates):
        resp = authenticated_client.get('/api/v1/video-inbox/stats/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['new_count'] == 3
        assert resp.data['approved_count'] == 1
        assert resp.data['dismissed_count'] == 1
        assert 'channels' in resp.data

    def test_stats_anonymous_forbidden(self, api_client, video_candidates):
        resp = api_client.get('/api/v1/video-inbox/stats/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestVideoInboxCleanup:
    """POST /api/v1/video-inbox/cleanup_old/"""

    def test_cleanup_old(self, authenticated_client, youtube_channel):
        old = timezone.now() - timedelta(days=35)
        recent = timezone.now() - timedelta(days=5)
        YouTubeVideoCandidate.objects.create(
            channel=youtube_channel, video_id='old1', title='Old', published_at=old, status='new',
        )
        YouTubeVideoCandidate.objects.create(
            channel=youtube_channel, video_id='recent1', title='Recent', published_at=recent, status='new',
        )
        resp = authenticated_client.post('/api/v1/video-inbox/cleanup_old/')
        assert resp.status_code == status.HTTP_200_OK
        assert not YouTubeVideoCandidate.objects.filter(video_id='old1').exists()
        assert YouTubeVideoCandidate.objects.filter(video_id='recent1').exists()


@pytest.mark.django_db
class TestVideoInboxArticleExistence:
    """Test has_article / similar_articles_count serializer fields."""

    def test_has_article_when_article_exists(self, authenticated_client, youtube_channel):
        """Video with matching article should show has_article=True."""
        article = Article.objects.create(
            title='BMW X5 Electric Review',
            slug='bmw-x5-electric-review',
            content='<p>Content</p>',
            youtube_url='https://www.youtube.com/watch?v=vid_match',
            is_published=True,
        )
        YouTubeVideoCandidate.objects.create(
            channel=youtube_channel,
            video_id='vid_match',
            title='BMW X5 Electric Review',
            published_at=timezone.now(),
            status='new',
        )
        resp = authenticated_client.get('/api/v1/video-inbox/')
        assert resp.status_code == status.HTTP_200_OK
        match = [v for v in resp.data['results'] if v['video_id'] == 'vid_match']
        assert len(match) == 1
        assert match[0]['has_article'] is True
        assert match[0]['article_status'] == 'published'

    def test_no_article(self, authenticated_client, youtube_channel):
        """Video without matching article should show has_article=False."""
        YouTubeVideoCandidate.objects.create(
            channel=youtube_channel,
            video_id='vid_no_art',
            title='Unique Title That Has No Match',
            published_at=timezone.now(),
            status='new',
        )
        resp = authenticated_client.get('/api/v1/video-inbox/')
        assert resp.status_code == status.HTTP_200_OK
        match = [v for v in resp.data['results'] if v['video_id'] == 'vid_no_art']
        assert len(match) == 1
        assert match[0]['has_article'] is False
