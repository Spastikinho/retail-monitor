"""
Pytest configuration and fixtures.
"""
import os
import sys

import django
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def db_access_without_rollback_and_truncate(request, django_db_setup, django_db_blocker):
    """Provide database access without rollback."""
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)
