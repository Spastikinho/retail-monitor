"""
S3-compatible object storage backend (AWS S3, Cloudflare R2, etc.)
"""

import logging
from datetime import datetime, timedelta
from typing import BinaryIO, Optional

from .base import StorageBackend, StorageMetadata

logger = logging.getLogger(__name__)


class ObjectStorage(StorageBackend):
    """
    S3-compatible object storage backend.
    Works with AWS S3, Cloudflare R2, MinIO, etc.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        bucket_name: str = 'retail-monitor-artifacts',
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = 'auto',
        public_url_base: Optional[str] = None,
    ):
        """
        Initialize S3-compatible storage.

        Args:
            endpoint_url: S3 endpoint URL (required for R2, optional for AWS)
            bucket_name: S3 bucket name
            access_key: AWS/R2 access key
            secret_key: AWS/R2 secret key
            region: AWS region or 'auto' for R2
            public_url_base: Base URL for public access (if bucket is public)
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region = region
        self.public_url_base = public_url_base

        # Lazy import boto3 to avoid dependency in local dev
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for object storage. "
                "Install it with: pip install boto3"
            )

        # Configure client
        config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
        )

        client_kwargs = {
            'service_name': 's3',
            'config': config,
        }

        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url

        if access_key and secret_key:
            client_kwargs['aws_access_key_id'] = access_key
            client_kwargs['aws_secret_access_key'] = secret_key

        if region and region != 'auto':
            client_kwargs['region_name'] = region

        self.client = boto3.client(**client_kwargs)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            try:
                create_params = {'Bucket': self.bucket_name}
                # Only add LocationConstraint for non-us-east-1 regions
                if self.region and self.region not in ('auto', 'us-east-1'):
                    create_params['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.region
                    }
                self.client.create_bucket(**create_params)
                logger.info(f"Created bucket: {self.bucket_name}")
            except Exception as e:
                logger.warning(f"Could not create bucket {self.bucket_name}: {e}")

    def upload(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = 'application/octet-stream',
        metadata: Optional[dict] = None,
    ) -> StorageMetadata:
        """Upload data to S3."""
        from io import BytesIO

        # Get data as bytes and compute hash
        if isinstance(data, bytes):
            content = data
            body = BytesIO(content)
        else:
            content = data.read()
            body = BytesIO(content)

        sha256 = self.compute_sha256(content)
        size = len(content)
        created_at = datetime.utcnow()

        # Prepare metadata
        s3_metadata = {
            'sha256': sha256,
            'created-at': created_at.isoformat(),
        }
        if metadata:
            # S3 metadata values must be strings
            for k, v in metadata.items():
                s3_metadata[str(k)] = str(v)

        # Upload
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            ContentType=content_type,
            Metadata=s3_metadata,
        )

        # Get ETag from response
        head = self.client.head_object(Bucket=self.bucket_name, Key=key)
        etag = head.get('ETag', '').strip('"')

        return StorageMetadata(
            key=key,
            size=size,
            content_type=content_type,
            sha256=sha256,
            created_at=created_at,
            etag=etag,
        )

    def download(self, key: str) -> bytes:
        """Download artifact from S3."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return response['Body'].read()
        except self.client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"Artifact not found: {key}")
        except Exception as e:
            if 'NoSuchKey' in str(e) or '404' in str(e):
                raise FileNotFoundError(f"Artifact not found: {key}")
            raise

    def exists(self, key: str) -> bool:
        """Check if artifact exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete artifact from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_url(
        self,
        key: str,
        expires_in: timedelta = timedelta(hours=1),
        for_download: bool = True,
    ) -> str:
        """
        Generate a presigned URL for the artifact.

        Args:
            key: Storage key
            expires_in: URL expiration time
            for_download: If True, includes Content-Disposition header

        Returns:
            Presigned URL string
        """
        params = {
            'Bucket': self.bucket_name,
            'Key': key,
        }

        if for_download:
            # Extract filename from key
            filename = key.split('/')[-1]
            params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

        url = self.client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=int(expires_in.total_seconds()),
        )

        return url

    def list_keys(self, prefix: str = '') -> list[str]:
        """List all keys with given prefix."""
        keys = []
        paginator = self.client.get_paginator('list_objects_v2')

        params = {'Bucket': self.bucket_name}
        if prefix:
            params['Prefix'] = prefix

        for page in paginator.paginate(**params):
            for obj in page.get('Contents', []):
                keys.append(obj['Key'])

        return sorted(keys)

    def get_object_info(self, key: str) -> Optional[dict]:
        """Get object metadata from S3."""
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return {
                'key': key,
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'etag': response.get('ETag', '').strip('"'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {}),
            }
        except Exception:
            return None

    def copy(self, source_key: str, dest_key: str) -> bool:
        """Copy an object within the same bucket."""
        try:
            self.client.copy_object(
                Bucket=self.bucket_name,
                Key=dest_key,
                CopySource={'Bucket': self.bucket_name, 'Key': source_key},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to copy {source_key} to {dest_key}: {e}")
            return False
