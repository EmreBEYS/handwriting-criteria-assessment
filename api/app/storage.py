from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config

from app.config import settings


class ObjectStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...


class S3ObjectStorage:
    def __init__(self) -> None:
        self.bucket = settings.object_storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint,
            region_name=settings.object_storage_region,
            aws_access_key_id=settings.object_storage_access_key_id,
            aws_secret_access_key=settings.object_storage_secret_access_key,
            use_ssl=settings.object_storage_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


@lru_cache
def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage()
