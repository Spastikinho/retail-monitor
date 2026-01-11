"""
Core models - base classes and utilities.
"""
import uuid
from datetime import timedelta

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


class Artifact(BaseModel):
    """
    Model for tracking artifacts stored in object storage.

    Artifacts can be:
    - HTML snapshots from scraping
    - JSON data exports
    - Screenshots
    - Excel/CSV exports

    The actual content is stored in object storage (S3/R2/local),
    and this model stores metadata and a reference (key) to the content.
    """

    class ArtifactType(models.TextChoices):
        HTML_SNAPSHOT = 'html_snapshot', 'HTML Snapshot'
        JSON_DATA = 'json_data', 'JSON Data'
        SCREENSHOT = 'screenshot', 'Screenshot'
        EXCEL_EXPORT = 'excel_export', 'Excel Export'
        CSV_EXPORT = 'csv_export', 'CSV Export'
        RAW_RESPONSE = 'raw_response', 'Raw Response'
        OTHER = 'other', 'Other'

    # Storage reference
    storage_key = models.CharField(
        'Storage Key',
        max_length=1024,
        unique=True,
        db_index=True,
        help_text='Key/path in object storage'
    )

    # Artifact metadata
    artifact_type = models.CharField(
        'Type',
        max_length=32,
        choices=ArtifactType.choices,
        default=ArtifactType.OTHER,
        db_index=True,
    )
    content_type = models.CharField(
        'Content Type',
        max_length=128,
        default='application/octet-stream',
    )
    size = models.PositiveBigIntegerField(
        'Size (bytes)',
        default=0,
    )
    sha256 = models.CharField(
        'SHA-256 Hash',
        max_length=64,
        blank=True,
        help_text='SHA-256 hash for integrity verification'
    )

    # Optional associations
    # Using string references to avoid circular imports
    listing = models.ForeignKey(
        'products.Listing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts',
        verbose_name='Listing',
    )
    scrape_session = models.ForeignKey(
        'scraping.ScrapeSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts',
        verbose_name='Scrape Session',
    )
    manual_import = models.ForeignKey(
        'scraping.ManualImport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts',
        verbose_name='Manual Import',
    )

    # Additional metadata
    filename = models.CharField(
        'Original Filename',
        max_length=255,
        blank=True,
    )
    description = models.TextField(
        'Description',
        blank=True,
    )
    metadata = models.JSONField(
        'Metadata',
        default=dict,
        blank=True,
        help_text='Additional metadata as JSON'
    )

    # Tracking
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_artifacts',
        verbose_name='Created By',
    )
    expires_at = models.DateTimeField(
        'Expires At',
        null=True,
        blank=True,
        help_text='Optional expiration date for temporary artifacts'
    )

    class Meta:
        verbose_name = 'Artifact'
        verbose_name_plural = 'Artifacts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['artifact_type', 'created_at']),
            models.Index(fields=['listing', 'artifact_type']),
            models.Index(fields=['scrape_session', 'artifact_type']),
            models.Index(fields=['manual_import', 'artifact_type']),
        ]

    def __str__(self):
        return f"{self.artifact_type}: {self.filename or self.storage_key}"

    def get_download_url(self, expires_in: timedelta = timedelta(hours=1)) -> str:
        """
        Get a download URL for this artifact.

        For local storage, returns a Django URL.
        For object storage, returns a signed URL.
        """
        from apps.core.storage import get_storage_backend
        storage = get_storage_backend()
        return storage.get_url(self.storage_key, expires_in=expires_in)

    def download(self) -> bytes:
        """Download the artifact content."""
        from apps.core.storage import get_storage_backend
        storage = get_storage_backend()
        return storage.download(self.storage_key)

    def delete_from_storage(self) -> bool:
        """Delete the artifact from storage (but not the DB record)."""
        from apps.core.storage import get_storage_backend
        storage = get_storage_backend()
        return storage.delete(self.storage_key)

    @classmethod
    def create_from_data(
        cls,
        data: bytes,
        artifact_type: str,
        filename: str,
        content_type: str = 'application/octet-stream',
        listing=None,
        scrape_session=None,
        manual_import=None,
        created_by=None,
        metadata: dict = None,
    ) -> 'Artifact':
        """
        Create an artifact from data bytes.

        Uploads to storage and creates the database record.
        """
        from django.utils import timezone
        from apps.core.storage import get_storage_backend, StorageBackend

        storage = get_storage_backend()

        # Generate storage key
        entity_id = str(listing.id if listing else
                       scrape_session.id if scrape_session else
                       manual_import.id if manual_import else
                       uuid.uuid4())

        key = StorageBackend.generate_key(
            artifact_type=artifact_type,
            entity_id=entity_id,
            filename=filename,
            timestamp=timezone.now(),
        )

        # Upload to storage
        storage_meta = storage.upload(
            key=key,
            data=data,
            content_type=content_type,
            metadata=metadata,
        )

        # Create database record
        artifact = cls.objects.create(
            storage_key=key,
            artifact_type=artifact_type,
            content_type=content_type,
            size=storage_meta.size,
            sha256=storage_meta.sha256,
            filename=filename,
            listing=listing,
            scrape_session=scrape_session,
            manual_import=manual_import,
            created_by=created_by,
            metadata=metadata or {},
        )

        return artifact
