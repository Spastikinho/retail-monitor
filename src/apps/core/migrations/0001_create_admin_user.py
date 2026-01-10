"""
Migration to create initial admin user from environment variables.
"""
import os
from django.db import migrations


def create_admin_user(apps, schema_editor):
    """Create admin user if ADMIN_USERNAME and ADMIN_PASSWORD are set."""
    User = apps.get_model('auth', 'User')

    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')
    email = os.environ.get('ADMIN_EMAIL', '')

    if not username or not password:
        print('ADMIN_USERNAME or ADMIN_PASSWORD not set, skipping admin user creation')
        return

    if User.objects.filter(username=username).exists():
        print(f'User {username} already exists, skipping')
        return

    # Create superuser
    user = User.objects.create(
        username=username,
        email=email,
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    user.set_password(password)
    user.save()
    print(f'Created admin user: {username}')


def reverse_admin_user(apps, schema_editor):
    """Remove admin user if it was created by this migration."""
    User = apps.get_model('auth', 'User')
    username = os.environ.get('ADMIN_USERNAME')
    if username:
        User.objects.filter(username=username).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_admin_user, reverse_admin_user),
    ]
