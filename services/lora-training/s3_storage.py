"""
S3 storage utilities for training artifacts
"""

import boto3
import os
from pathlib import Path
from typing import Optional
import requests

class S3Storage:
    """S3 client for uploading/downloading training artifacts"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket = os.getenv('AWS_S3_BUCKET', 'content-generation-assets')

    def upload_file(self, local_path: str, s3_key: str) -> str:
        """
        Upload a file to S3

        Args:
            local_path: Local file path
            s3_key: S3 key (path in bucket)

        Returns:
            Public URL of uploaded file
        """
        try:
            # Determine content type
            content_type = 'application/octet-stream'
            if local_path.endswith('.safetensors'):
                content_type = 'application/octet-stream'
            elif local_path.endswith('.json'):
                content_type = 'application/json'
            elif local_path.endswith('.jpg') or local_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif local_path.endswith('.png'):
                content_type = 'image/png'
            elif local_path.endswith('.mp4'):
                content_type = 'video/mp4'

            self.s3_client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            # Return public URL
            return f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"

        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise

    def upload_directory(self, local_dir: str, s3_prefix: str) -> list:
        """
        Upload entire directory to S3

        Args:
            local_dir: Local directory path
            s3_prefix: S3 prefix (folder)

        Returns:
            List of uploaded file URLs
        """
        uploaded_files = []
        local_path = Path(local_dir)

        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                # Calculate relative path
                relative_path = file_path.relative_to(local_path)
                s3_key = f"{s3_prefix}/{relative_path}"

                url = self.upload_file(str(file_path), s3_key)
                uploaded_files.append(url)

        return uploaded_files

    def download_file(self, s3_key: str, local_path: str):
        """Download a file from S3"""
        try:
            self.s3_client.download_file(
                self.bucket,
                s3_key,
                local_path
            )
        except Exception as e:
            print(f"Error downloading from S3: {e}")
            raise

    def download_from_url(self, url: str, local_path: str):
        """
        Download file from URL (supports both S3 and HTTP/HTTPS)

        Args:
            url: Source URL (s3://... or https://...)
            local_path: Local destination path
        """
        if url.startswith('s3://'):
            # Parse S3 URL
            parts = url.replace('s3://', '').split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ''

            self.s3_client.download_file(bucket, key, local_path)
        else:
            # HTTP/HTTPS download
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

    def get_file_size(self, s3_key: str) -> int:
        """Get size of file in S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return response['ContentLength']
        except Exception as e:
            print(f"Error getting file size: {e}")
            return 0

# Global S3 instance
s3_storage = S3Storage()
