from django.db import migrations


def lowercase_and_deduplicate_emails(apps, schema_editor):
    """
    1. Lowercase all user emails
    2. Rename duplicate emails (keep oldest user, rename newer ones: email_dup1@domain.com)
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Step 1: Lowercase all emails
    for user in User.objects.all():
        if user.email and user.email != user.email.lower():
            User.objects.filter(pk=user.pk).update(email=user.email.lower())

    # Step 2: Handle duplicates — oldest user keeps original email
    seen = {}
    for user in User.objects.exclude(email='').order_by('date_joined', 'id'):
        email = user.email.lower()
        if email in seen:
            # Rename duplicate
            parts = email.split('@')
            count = seen[email]
            new_email = f"{parts[0]}_dup{count}@{parts[1]}"
            User.objects.filter(pk=user.pk).update(email=new_email)
            seen[email] += 1
            print(f"  ⚠️  Renamed duplicate: {email} → {new_email} (user: {user.username})")
        else:
            seen[email] = 1


def reverse_noop(apps, schema_editor):
    """Reverse is a no-op — can't reliably un-deduplicate emails."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0098_totp_device_2fa'),
    ]

    operations = [
        # Step 1: Cleanup duplicates in Python (cross-DB compatible)
        migrations.RunPython(
            lowercase_and_deduplicate_emails,
            reverse_noop,
        ),

        # Step 2: Add unique index on lower(email) at DB level
        # Using partial index (WHERE email != '') to allow multiple users without email
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique_lower
                ON auth_user (lower(email))
                WHERE email != '' AND email IS NOT NULL;
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS auth_user_email_unique_lower;
            """,
        ),
    ]
