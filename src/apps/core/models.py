"""
Core models - base classes and utilities.
"""
import uuid

from django.db import models


class BaseModel(models.Model):
    """Abstract base model with common fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract model with only timestamps (no UUID)."""

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        abstract = True
