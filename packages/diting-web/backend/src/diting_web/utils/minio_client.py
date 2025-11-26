"""MinIO client for object storage.

Handles file upload, download, and deletion operations.
"""

import io
from datetime import timedelta
from typing import BinaryIO, Optional
from uuid import uuid4

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from diting_web.common.exceptions import ValidationError
from diting_web.common.logging import get_logger
logger = get_logger(__name__)


class MinIOClient:
    """MinIO client for object storage operations."""

    def __init__(self):
        """Initialize MinIO client."""
        from diting_web.config.settings import get_settings
        
        settings = get_settings()
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info("MinIO bucket created", bucket=self.bucket_name)
            else:
                logger.info("MinIO bucket exists", bucket=self.bucket_name)
        except S3Error as e:
            logger.error("Failed to check/create bucket", error=str(e))
            raise ValidationError(f"MinIO bucket error: {str(e)}")

    async def upload_file(
        self,
        file: UploadFile,
        object_name: Optional[str] = None,
    ) -> str:
        """Upload file to MinIO.

        Args:
            file: File to upload
            object_name: Optional object name, auto-generated if not provided

        Returns:
            Object name in MinIO

        Raises:
            ValidationError: If upload fails
        """
        if object_name is None:
            # Generate unique object name
            ext = self._get_file_extension(file.filename or "file")
            object_name = f"datasets/{uuid4()}{ext}"

        try:
            # Reset file position
            await file.seek(0)
            content = await file.read()
            file_size = len(content)

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(content),
                length=file_size,
                content_type=file.content_type or "application/octet-stream",
            )

            logger.info(
                "File uploaded to MinIO",
                object_name=object_name,
                size=file_size,
                content_type=file.content_type,
            )

            return object_name

        except S3Error as e:
            logger.error("Failed to upload file to MinIO", error=str(e))
            raise ValidationError(f"File upload failed: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error uploading file", error=str(e))
            raise ValidationError(f"File upload failed: {str(e)}")

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """Generate presigned URL for file download.

        Args:
            object_name: Object name in MinIO
            expires: URL expiration time (default 1 hour)

        Returns:
            Presigned URL

        Raises:
            ValidationError: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires,
            )
            logger.info("Generated presigned URL", object_name=object_name)
            return url

        except S3Error as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise ValidationError(f"URL generation failed: {str(e)}")

    def delete_file(self, object_name: str) -> None:
        """Delete file from MinIO.

        Args:
            object_name: Object name in MinIO

        Raises:
            ValidationError: If deletion fails
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            logger.info("File deleted from MinIO", object_name=object_name)

        except S3Error as e:
            logger.error("Failed to delete file from MinIO", error=str(e))
            raise ValidationError(f"File deletion failed: {str(e)}")

    def download_file(self, object_name: str) -> bytes:
        """Download file from MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            File content as bytes

        Raises:
            ValidationError: If download fails
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            content = response.read()
            response.close()
            response.release_conn()
            
            logger.info("File downloaded from MinIO", object_name=object_name, size=len(content))
            return content

        except S3Error as e:
            logger.error("Failed to download file from MinIO", error=str(e))
            raise ValidationError(f"File download failed: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error downloading file", error=str(e))
            raise ValidationError(f"File download failed: {str(e)}")

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            return True
        except S3Error:
            return False

    def get_file_info(self, object_name: str) -> dict:
        """Get file metadata from MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            Dictionary with file metadata

        Raises:
            ValidationError: If file not found
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            return {
                "object_name": object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }

        except S3Error as e:
            logger.error("Failed to get file info", error=str(e))
            raise ValidationError(f"File not found: {object_name}")

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Get file extension from filename.

        Args:
            filename: Filename with extension

        Returns:
            File extension with dot (e.g., '.csv')
        """
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()


# Singleton instance
_minio_client: Optional[MinIOClient] = None


def get_minio_client() -> MinIOClient:
    """Get MinIO client singleton instance.

    Returns:
        MinIOClient instance
    """
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client

