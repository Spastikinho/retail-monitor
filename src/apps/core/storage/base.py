"""
Base storage abstraction for artifact storage.
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import BinaryIO, Optional


@dataclass
class StorageMetadata:
    """Metadata about a stored artifact."""
    key: str
    size: int
    content_type: str
    sha256: str
    created_at: datetime
    etag: Optional[str] = None


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    Implementations must provide methods for uploading, downloading,
    and managing artifacts.
    """

    @abstractmethod
    def upload(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = 'application/octet-stream',
        metadata: Optional[dict] = None,
    ) -> StorageMetadata:
        """
        Upload data to storage.

        Args:
            key: Storage key/path for the artifact
            data: Bytes or file-like object to upload
            content_type: MIME type of the content
            metadata: Optional metadata dict to store with artifact

        Returns:
            StorageMetadata with upload details
        """
        pass

    @abstractmethod
    def download(self, key: str) -> bytes:
        """
        Download artifact from storage.

        Args:
            key: Storage key/path for the artifact

        Returns:
            Artifact content as bytes

        Raises:
            FileNotFoundError: If artifact doesn't exist
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if artifact exists in storage."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete artifact from storage.

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def get_url(
        self,
        key: str,
        expires_in: timedelta = timedelta(hours=1),
        for_download: bool = True,
    ) -> str:
        """
        Get a URL to access the artifact.

        For local storage, returns a path or file:// URL.
        For object storage, returns a signed URL.

        Args:
            key: Storage key/path for the artifact
            expires_in: How long the URL should be valid
            for_download: If True, set Content-Disposition for download

        Returns:
            URL string
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str = '') -> list[str]:
        """
        List all keys with given prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of matching keys
        """
        pass

    @staticmethod
    def compute_sha256(data: bytes | BinaryIO) -> str:
        """Compute SHA-256 hash of data."""
        hasher = hashlib.sha256()
        if isinstance(data, bytes):
            hasher.update(data)
        else:
            # File-like object
            pos = data.tell()
            for chunk in iter(lambda: data.read(8192), b''):
                hasher.update(chunk)
            data.seek(pos)
        return hasher.hexdigest()

    @staticmethod
    def generate_key(
        artifact_type: str,
        entity_id: str,
        filename: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Generate a standardized storage key.

        Format: {type}/{YYYY}/{MM}/{entity_id}/{filename}

        Args:
            artifact_type: Type of artifact (snapshot, export, screenshot, etc.)
            entity_id: UUID or ID of related entity
            filename: Original or generated filename
            timestamp: Optional timestamp for path generation

        Returns:
            Storage key string
        """
        ts = timestamp or datetime.utcnow()
        return f"{artifact_type}/{ts.year}/{ts.month:02d}/{entity_id}/{filename}"


def get_storage_backend() -> StorageBackend:
    """
    Factory function to get the appropriate storage backend
    based on environment configuration.

    Returns:
        StorageBackend instance (LocalFilesystemStorage or ObjectStorage)
    """
    from django.conf import settings

    # Check for S3/R2 configuration
    storage_type = getattr(settings, 'ARTIFACT_STORAGE_BACKEND', 'local')

    if storage_type == 'local':
        from .local import LocalFilesystemStorage
        storage_path = getattr(settings, 'ARTIFACT_STORAGE_PATH', None)
        return LocalFilesystemStorage(base_path=storage_path)
    elif storage_type in ('s3', 'r2', 'object'):
        from .object_storage import ObjectStorage
        return ObjectStorage(
            endpoint_url=getattr(settings, 'ARTIFACT_S3_ENDPOINT', None),
            bucket_name=getattr(settings, 'ARTIFACT_S3_BUCKET', 'retail-monitor-artifacts'),
            access_key=getattr(settings, 'ARTIFACT_S3_ACCESS_KEY', None),
            secret_key=getattr(settings, 'ARTIFACT_S3_SECRET_KEY', None),
            region=getattr(settings, 'ARTIFACT_S3_REGION', 'auto'),
            public_url_base=getattr(settings, 'ARTIFACT_PUBLIC_URL_BASE', None),
        )
    else:
        raise ValueError(f"Unknown storage backend: {storage_type}")
