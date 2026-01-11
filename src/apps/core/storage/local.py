"""
Local filesystem storage backend for development.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO, Optional

from django.conf import settings

from .base import StorageBackend, StorageMetadata


class LocalFilesystemStorage(StorageBackend):
    """
    Local filesystem storage backend.
    Used for development and testing.
    """

    def __init__(self, base_path: Optional[str | Path] = None):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for storing artifacts.
                      Defaults to settings.DATA_DIR / 'artifacts'
        """
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = getattr(settings, 'DATA_DIR', Path.cwd() / 'data') / 'artifacts'

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, key: str) -> Path:
        """Get full filesystem path for a key."""
        # Sanitize key to prevent path traversal
        safe_key = key.lstrip('/').replace('..', '')
        return self.base_path / safe_key

    def _get_metadata_path(self, key: str) -> Path:
        """Get path for metadata file."""
        return self._get_full_path(key + '.meta.json')

    def upload(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = 'application/octet-stream',
        metadata: Optional[dict] = None,
    ) -> StorageMetadata:
        """Upload data to local filesystem."""
        file_path = self._get_full_path(key)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Get data as bytes
        if isinstance(data, bytes):
            content = data
        else:
            content = data.read()

        # Compute hash and size
        sha256 = self.compute_sha256(content)
        size = len(content)
        created_at = datetime.utcnow()

        # Write content
        with open(file_path, 'wb') as f:
            f.write(content)

        # Write metadata
        meta = {
            'key': key,
            'size': size,
            'content_type': content_type,
            'sha256': sha256,
            'created_at': created_at.isoformat(),
            'custom_metadata': metadata or {},
        }
        with open(self._get_metadata_path(key), 'w') as f:
            json.dump(meta, f, indent=2)

        return StorageMetadata(
            key=key,
            size=size,
            content_type=content_type,
            sha256=sha256,
            created_at=created_at,
        )

    def download(self, key: str) -> bytes:
        """Download artifact from local filesystem."""
        file_path = self._get_full_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {key}")

        with open(file_path, 'rb') as f:
            return f.read()

    def exists(self, key: str) -> bool:
        """Check if artifact exists."""
        return self._get_full_path(key).exists()

    def delete(self, key: str) -> bool:
        """Delete artifact and its metadata."""
        file_path = self._get_full_path(key)
        meta_path = self._get_metadata_path(key)

        deleted = False

        if file_path.exists():
            file_path.unlink()
            deleted = True

        if meta_path.exists():
            meta_path.unlink()

        return deleted

    def get_url(
        self,
        key: str,
        expires_in: timedelta = timedelta(hours=1),
        for_download: bool = True,
    ) -> str:
        """
        Get URL for local artifact.

        For local storage, returns a file:// URL.
        In a web context, this should be served via a Django view.
        """
        file_path = self._get_full_path(key)
        return f"file://{file_path.absolute()}"

    def list_keys(self, prefix: str = '') -> list[str]:
        """List all keys with given prefix."""
        search_path = self._get_full_path(prefix) if prefix else self.base_path
        keys = []

        if not search_path.exists():
            return keys

        # If prefix points to a file, just check that file
        if search_path.is_file():
            return [prefix]

        # Walk directory tree
        for root, dirs, files in os.walk(search_path):
            root_path = Path(root)
            for filename in files:
                if filename.endswith('.meta.json'):
                    continue
                full_path = root_path / filename
                rel_path = full_path.relative_to(self.base_path)
                keys.append(str(rel_path))

        return sorted(keys)

    def get_metadata(self, key: str) -> Optional[dict]:
        """Get stored metadata for an artifact."""
        meta_path = self._get_metadata_path(key)
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                return json.load(f)
        return None
