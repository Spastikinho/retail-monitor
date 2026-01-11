"""
Secure Bootstrap Admin Management Command.

Creates an admin user only when explicitly enabled via environment variables.
This ensures no default credentials can be deployed to production.

Usage:
    ALLOW_BOOTSTRAP_ADMIN=true ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secure_password \
    python manage.py bootstrap_admin

Environment Variables Required:
    - ALLOW_BOOTSTRAP_ADMIN: Must be 'true' to enable this command
    - ADMIN_EMAIL: Email address for the admin user (also used as username)
    - ADMIN_PASSWORD: Password for the admin user (min 12 characters recommended)

Optional:
    - ADMIN_USERNAME: Custom username (defaults to email)
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Create a bootstrap admin user from environment variables (secure provisioning)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user exists (will update password)',
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check if bootstrap is allowed and credentials are valid',
        )

    def handle(self, *args, **options):
        # Step 1: Check if bootstrap is explicitly enabled
        allow_bootstrap = os.environ.get('ALLOW_BOOTSTRAP_ADMIN', '').lower() == 'true'

        if not allow_bootstrap:
            self.stderr.write(self.style.ERROR(
                'Bootstrap admin is DISABLED.\n'
                'To enable, set environment variable: ALLOW_BOOTSTRAP_ADMIN=true\n'
                'This is a security measure to prevent accidental admin creation.'
            ))
            sys.exit(1)

        # Step 2: Validate required environment variables
        admin_email = os.environ.get('ADMIN_EMAIL', '').strip()
        admin_password = os.environ.get('ADMIN_PASSWORD', '')
        admin_username = os.environ.get('ADMIN_USERNAME', '').strip() or admin_email

        if not admin_email:
            raise CommandError(
                'ADMIN_EMAIL environment variable is required.\n'
                'Set it to the admin user\'s email address.'
            )

        if not admin_password:
            raise CommandError(
                'ADMIN_PASSWORD environment variable is required.\n'
                'Set it to a secure password (minimum 12 characters recommended).'
            )

        # Step 3: Validate email format
        if '@' not in admin_email or '.' not in admin_email.split('@')[-1]:
            raise CommandError(
                f'Invalid email format: {admin_email}\n'
                'Please provide a valid email address.'
            )

        # Step 4: Validate password strength
        User = get_user_model()
        temp_user = User(username=admin_username, email=admin_email)

        try:
            validate_password(admin_password, user=temp_user)
        except ValidationError as e:
            raise CommandError(
                f'Password does not meet security requirements:\n'
                + '\n'.join(f'  - {error}' for error in e.messages) +
                '\n\nPlease use a stronger password.'
            )

        # Step 5: Check password minimum length (additional check)
        if len(admin_password) < 12:
            self.stdout.write(self.style.WARNING(
                'WARNING: Password is less than 12 characters. '
                'Consider using a longer password for production.'
            ))

        # Check-only mode
        if options['check_only']:
            self.stdout.write(self.style.SUCCESS(
                f'Bootstrap admin check PASSED:\n'
                f'  - ALLOW_BOOTSTRAP_ADMIN: enabled\n'
                f'  - ADMIN_EMAIL: {admin_email}\n'
                f'  - ADMIN_USERNAME: {admin_username}\n'
                f'  - Password: validated (meets requirements)'
            ))
            return

        # Step 6: Create or update admin user
        try:
            user = User.objects.get(username=admin_username)

            if options['force']:
                user.email = admin_email
                user.set_password(admin_password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'Updated admin user: {admin_username}'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Admin user already exists: {admin_username}\n'
                    'Use --force to update the existing user\'s password.'
                ))
                return

        except User.DoesNotExist:
            user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
            )
            self.stdout.write(self.style.SUCCESS(
                f'Created admin user: {admin_username} ({admin_email})'
            ))

        # Step 7: Security reminder
        self.stdout.write(self.style.NOTICE(
            '\nSECURITY REMINDERS:\n'
            '1. Disable ALLOW_BOOTSTRAP_ADMIN in production after initial setup\n'
            '2. Remove ADMIN_PASSWORD from environment after user creation\n'
            '3. Store credentials securely (password manager, secrets vault)\n'
            '4. Enable 2FA if supported'
        ))
