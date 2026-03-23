import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Count
from django.utils import timezone

from news.models import VehicleSpecs, ManualCompetitorFeedback, ArticleImage

class MLTrainerNextPairView(APIView):
    """
    Returns a random subject car and a candidate competitor for manual pairing feedback.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Staff only.'}, status=status.HTTP_403_FORBIDDEN)
            
        # 1. Get gamification stats for the user
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = ManualCompetitorFeedback.objects.filter(
            user=request.user, created_at__gte=today
        ).count()
        total_count = ManualCompetitorFeedback.objects.filter(user=request.user).count()

        # 2. Select a random subject car
        # Prefer cars that have photos (article with image) and valid specs
        subjects_qs = VehicleSpecs.objects.exclude(make='').exclude(model_name='').filter(
            article__isnull=False, article__image__isnull=False
        )
        
        count = subjects_qs.count()
        if count == 0:
            return Response({'detail': 'No vehicles found to train on.'}, status=status.HTTP_404_NOT_FOUND)
            
        subject = subjects_qs.order_by('?').first()
        
        # 3. Select a candidate competitor
        candidates_qs = VehicleSpecs.objects.exclude(make=subject.make).exclude(make='').exclude(model_name='')
        
        # Strategy: 70% chance to find a "similar" car, 30% chance for a random one
        if random.random() < 0.7:
            # Try to match body type or fuel type
            if subject.body_type:
                candidates_qs = candidates_qs.filter(body_type=subject.body_type)
        
        candidate_count = candidates_qs.count()
        if candidate_count == 0:
            # Fallback to completely random
            candidates_qs = VehicleSpecs.objects.exclude(make=subject.make).exclude(make='').exclude(model_name='')
            
        competitor = candidates_qs.order_by('?').first()
        
        if not competitor:
            return Response({'detail': 'No competitors found.'}, status=status.HTTP_404_NOT_FOUND)

        def serialize_car(car):
            image_url = ''
            article_id = None
            if car.article:
                article_id = car.article.id
                if car.article.image:
                    image_url = car.article.image.url
            
            return {
                'make': car.make,
                'model': car.model_name,
                'trim': car.trim_name,
                'photo': image_url,
                'price_usd': car.price_usd_from,
                'power_hp': car.power_hp,
                'range_km': car.range_wltp or car.range_km,
                'body_type': car.body_type,
                'fuel_type': car.fuel_type,
                'article_id': article_id,
            }

        return Response({
            'stats': {
                'daily_count': daily_count,
                'total_count': total_count,
            },
            'subject': serialize_car(subject),
            'competitor': serialize_car(competitor),
        })

class MLTrainerSubmitFeedbackView(APIView):
    """
    Accepts feedback (score and penalty reason) for a car pairing.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Staff only.'}, status=status.HTTP_403_FORBIDDEN)
            
        subject_make = request.data.get('subject_make')
        subject_model = request.data.get('subject_model')
        competitor_make = request.data.get('competitor_make')
        competitor_model = request.data.get('competitor_model')
        score = request.data.get('score')
        penalty_reason = request.data.get('penalty_reason', '')

        if score is None or not subject_make or not competitor_make:
            return Response({'detail': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            score = float(score)
        except ValueError:
            return Response({'detail': 'Invalid score.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save feedback
        ManualCompetitorFeedback.objects.create(
            subject_make=subject_make,
            subject_model=subject_model,
            competitor_make=competitor_make,
            competitor_model=competitor_model,
            score=score,
            penalty_reason=penalty_reason,
            user=request.user
        )

        return Response({'success': True})
