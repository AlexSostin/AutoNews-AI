from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class IsSuperUser(BasePermission):
    """Only allow superusers."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class AdminUserManagementViewSet(viewsets.ViewSet):
    """
    Admin-only ViewSet for managing users and their permissions.
    Only superusers can access these endpoints.
    """
    permission_classes = [IsSuperUser]

    def list(self, request):
        """List all users with optional search, filters, and pagination."""
        users = User.objects.all().annotate(
            role_order=Case(
                When(is_superuser=True, then=Value(0)),
                When(is_staff=True, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('role_order', '-date_joined')

        # Search by username or email
        search = request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        # Filter by role
        role = request.query_params.get('role', '').strip()
        if role == 'superuser':
            users = users.filter(is_superuser=True)
        elif role == 'staff':
            users = users.filter(is_staff=True, is_superuser=False)
        elif role == 'user':
            users = users.filter(is_staff=False, is_superuser=False)

        # Filter by active status
        is_active = request.query_params.get('is_active', '').strip()
        if is_active == 'true':
            users = users.filter(is_active=True)
        elif is_active == 'false':
            users = users.filter(is_active=False)

        # Pagination
        total_filtered = users.count()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 25))))
        except (ValueError, TypeError):
            page = 1
            page_size = 25

        import math
        total_pages = max(1, math.ceil(total_filtered / page_size))
        page = min(page, total_pages)
        offset = (page - 1) * page_size
        paginated_users = users[offset:offset + page_size]

        # Build response
        user_list = []
        for u in paginated_users:
            role_label = 'Superuser' if u.is_superuser else ('Staff' if u.is_staff else 'User')
            user_list.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'role': role_label,
                'is_superuser': u.is_superuser,
                'is_staff': u.is_staff,
                'is_active': u.is_active,
                'date_joined': u.date_joined.isoformat(),
                'last_login': u.last_login.isoformat() if u.last_login else None,
            })

        # Stats (always over all users, not filtered)
        all_users = User.objects.all()
        stats = {
            'total': all_users.count(),
            'active': all_users.filter(is_active=True).count(),
            'staff': all_users.filter(is_staff=True).count(),
            'superusers': all_users.filter(is_superuser=True).count(),
        }

        return Response({
            'results': user_list,
            'stats': stats,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_filtered,
                'total_pages': total_pages,
            }
        })

    def create(self, request):
        """Create a new user."""
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()
        role = request.data.get('role', 'user').strip()
        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()

        # Validation
        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password or len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        if email and User.objects.filter(email=email).exists():
            return Response({'error': 'Email already in use.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Set role
        if role == 'superuser':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'staff':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        user.save()

        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': role_label,
            'message': f'User "{username}" created successfully.',
        }, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """Get a single user's details."""
        user = get_object_or_404(User, pk=pk)
        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role_label,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        })

    def partial_update(self, request, pk=None):
        """Update a user's role, active status, or profile info."""
        user = get_object_or_404(User, pk=pk)

        # Self-protection: cannot demote or deactivate yourself
        if user.id == request.user.id:
            changing_role = 'is_superuser' in request.data or 'is_staff' in request.data or 'role' in request.data
            changing_active = 'is_active' in request.data and not request.data['is_active']
            if changing_role or changing_active:
                return Response(
                    {'detail': 'You cannot change your own role or deactivate yourself.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Handle role changes via 'role' field
        role = request.data.get('role')
        if role:
            if role == 'superuser':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'staff':
                user.is_superuser = False
                user.is_staff = True
            elif role == 'user':
                user.is_superuser = False
                user.is_staff = False

        # Handle direct field updates
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            new_email = request.data['email'].strip().lower()
            # Check uniqueness
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                return Response(
                    {'detail': 'A user with this email already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.email = new_email

        user.save()
        logger.info(f"Admin {request.user.username} updated user {user.username} (id={user.id})")

        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role_label,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        })

    def destroy(self, request, pk=None):
        """Delete a user. Cannot delete yourself."""
        user = get_object_or_404(User, pk=pk)

        if user.id == request.user.id:
            return Response(
                {'detail': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = user.username
        user.delete()
        logger.info(f"Admin {request.user.username} deleted user {username} (id={pk})")
        return Response({'detail': f'User {username} has been deleted.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset a user's password to a random one. Returns the new password once."""
        import secrets
        import string

        user = get_object_or_404(User, pk=pk)

        # Generate a secure random password
        alphabet = string.ascii_letters + string.digits + '!@#$%'
        new_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        user.set_password(new_password)
        user.save()
        logger.info(f"Admin {request.user.username} reset password for user {user.username} (id={pk})")

        return Response({
            'detail': f'Password for {user.username} has been reset.',
            'new_password': new_password,
        })
