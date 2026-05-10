"""
Яндекс Object Storage (S3-совместимый).
Все файлы хранятся по ключу: {order_id}/{filename}
"""

import asyncio
import logging
from functools import partial

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def upload_bytes(key: str, data: bytes) -> str:
    """Загружает файл в S3, возвращает ключ."""
    content_type = _CONTENT_TYPES.get(_ext(key), "application/octet-stream")
    loop = asyncio.get_running_loop()
    client = _client()
    await loop.run_in_executor(
        None,
        partial(
            client.put_object,
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        ),
    )
    logger.info("Uploaded %s to S3 (%d bytes)", key, len(data))
    return key


async def download_bytes(key: str) -> bytes:
    """Скачивает файл из S3, возвращает bytes."""
    loop = asyncio.get_running_loop()
    client = _client()
    response = await loop.run_in_executor(
        None,
        partial(client.get_object, Bucket=settings.S3_BUCKET, Key=key),
    )
    return response["Body"].read()


async def get_presigned_url(key: str, expires: int = 300) -> str:
    """Возвращает временную ссылку на скачивание (по умолчанию 5 минут)."""
    loop = asyncio.get_running_loop()
    client = _client()
    url = await loop.run_in_executor(
        None,
        partial(
            client.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires,
        ),
    )
    return url
