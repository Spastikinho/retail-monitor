"""
Storage abstraction for Retail Monitor.
Provides unified interface for local and object storage (S3/R2).
"""

from .base import StorageBackend, get_storage_backend
from .local import LocalFilesystemStorage
from .object_storage import ObjectStorage

__all__ = [
    'StorageBackend',
    'LocalFilesystemStorage',
    'ObjectStorage',
    'get_storage_backend',
]
