from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from ..models import NewsletterSubscriber, NewsletterHistory
from ..serializers import SubscriberSerializer, NewsletterHistorySerializer
import logging

logger = logging.getLogger(__name__)


class SubscriberViewSet(viewsets.ModelViewSet):
    """
    Newsletter subscription management.
    - Anyone can subscribe (rate limited)
    - Staff can view/manage subscribers
    """
    serializer_class = SubscriberSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Show all subscribers for admins, only active for others"""
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return NewsletterSubscriber.objects.all()
        return NewsletterSubscriber.objects.filter(is_active=True)
    
    def get_permissions(self):
        if self.action in ['list', 'destroy', 'send_newsletter', 'export_csv', 'import_csv', 'bulk_delete', 'newsletter_history']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Subscribe to newsletter"""
        email = request.data.get('email', '').lower().strip()
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already subscribed
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        
        if not created and subscriber.is_active:
            return Response({'message': 'Already subscribed!'}, status=status.HTTP_200_OK)
        
        # Reactivate if previously unsubscribed
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save()
        
        # Send welcome email
        try:
            from django.core.mail import send_mail
            send_mail(
                subject='Welcome to Fresh Motors! 🚗',
                message='Thank you for subscribing to Fresh Motors newsletter!\n\nYou will receive the latest automotive news and reviews.',
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")
        
        return Response({
            'message': 'Successfully subscribed!',
            'email': email
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        """Unsubscribe from newsletter"""
        from django.utils import timezone
        
        email = request.data.get('email', '').lower().strip()
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)
            subscriber.is_active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save()
            return Response({'message': 'Successfully unsubscribed'})
        except NewsletterSubscriber.DoesNotExist:
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def send_newsletter(self, request):
        """Send newsletter to all active subscribers (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        subject = request.data.get('subject')
        message = request.data.get('message')
        
        if not subject or not message:
            return Response({'error': 'Subject and message required'}, status=status.HTTP_400_BAD_REQUEST)
        
        subscribers = NewsletterSubscriber.objects.filter(is_active=True).values_list('email', flat=True)
        
        if not subscribers:
            return Response({'error': 'No active subscribers'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.core.mail import send_mass_mail
            
            messages = [
                (subject, message, None, [email])
                for email in subscribers
            ]
            
            sent = send_mass_mail(messages, fail_silently=False)
            
            # Save to history
            NewsletterHistory.objects.create(
                subject=subject,
                message=message,
                sent_to_count=sent,
                sent_by=request.user
            )
            
            return Response({
                'message': f'Newsletter sent to {sent} subscribers',
                'count': sent
            })
        except Exception as e:
            logger.error(f"Failed to send newsletter: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        """Export all subscribers as CSV"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Status', 'Subscribed Date', 'Unsubscribed Date'])
        
        subscribers = NewsletterSubscriber.objects.all()
        for sub in subscribers:
            writer.writerow([
                sub.email,
                'Active' if sub.is_active else 'Unsubscribed',
                sub.subscribed_at.strftime('%Y-%m-%d %H:%M:%S'),
                sub.unsubscribed_at.strftime('%Y-%m-%d %H:%M:%S') if sub.unsubscribed_at else ''
            ])
        
        return response
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_csv(self, request):
        """Import subscribers from CSV file"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be CSV format'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import csv
            import io
            
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            added = 0
            skipped = 0
            
            for row in csv_data:
                email = row.get('email', '').lower().strip()
                if not email:
                    continue
                
                # Check if email is valid
                from django.core.validators import validate_email
                try:
                    validate_email(email)
                except:
                    skipped += 1
                    continue
                
                # Create or update subscriber
                _, created = NewsletterSubscriber.objects.get_or_create(
                    email=email,
                    defaults={'is_active': True}
                )
                
                if created:
                    added += 1
                else:
                    skipped += 1
            
            return Response({
                'message': f'Import complete',
                'added': added,
                'skipped': skipped
            })
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_delete(self, request):
        """Delete multiple subscribers"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count = NewsletterSubscriber.objects.filter(id__in=ids).delete()[0]
        
        return Response({
            'message': f'Deleted {deleted_count} subscribers',
            'count': deleted_count
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated],
            url_path='newsletter-auto-select')
    def newsletter_auto_select(self, request):
        """Auto-select diverse articles for newsletter using ML."""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        days = int(request.query_params.get('days', 7))
        count = int(request.query_params.get('count', 6))
        
        try:
            from ai_engine.modules.content_recommender import select_newsletter_articles, is_available
            if not is_available():
                return Response({
                    'articles': [],
                    'ml_available': False,
                    'message': 'ML model not available. Run: python manage.py train_content_model',
                })
            
            articles = select_newsletter_articles(days=days, count=count)
            return Response({
                'articles': articles,
                'ml_available': True,
                'count': len(articles),
                'days_back': days,
            })
        except Exception as e:
            logger.error(f"Newsletter auto-select failed: {e}")
            return Response({'articles': [], 'error': str(e)})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def newsletter_history(self, request):
        """Get newsletter history"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        history = NewsletterHistory.objects.all()
        serializer = NewsletterHistorySerializer(history, many=True)
        return Response(serializer.data)


@method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True), name='post')
class NewsletterSubscribeView(APIView):
    """Newsletter subscription endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from news.models import NewsletterSubscriber
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from news.email_service import email_service
        
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get IP address for tracking
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # Create or update subscriber
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'is_active': True, 'ip_address': ip_address}
        )
        
        if not created:
            if not subscriber.is_active:
                # Reactivate subscription
                subscriber.is_active = True
                subscriber.unsubscribed_at = None
                subscriber.ip_address = ip_address
                subscriber.save()
                
                # Send welcome email for resubscription
                email_service.send_newsletter_welcome(email)
                
                return Response({'message': 'Successfully resubscribed!'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Already subscribed!'}, status=status.HTTP_200_OK)
        
        # Send welcome email to new subscriber
        email_sent = email_service.send_newsletter_welcome(email)
        if email_sent:
            logger.info(f"New newsletter subscriber: {email} - welcome email sent")
        else:
            logger.warning(f"New newsletter subscriber: {email} - welcome email failed")
        
        return Response({'message': 'Successfully subscribed!'}, status=status.HTTP_201_CREATED)
