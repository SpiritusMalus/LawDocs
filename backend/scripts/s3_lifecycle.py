"""Применяет S3 lifecycle к бакету документов (Yandex Object Storage).

Назначение (system-design §6, DR): backstop для объектов, которые retention-loop
не удалил активно (осиротевшие блобы после сбоев/иных путей удаления). Окно — чуть
больше окна retention (1095 дней = 3 года), чтобы loop удалял первым, а lifecycle
лишь подчищал остатки. Идемпотентно: повторный запуск перезаписывает правило.

Запуск (на хосте с доступом к S3-кредам, зона User):
    python -m scripts.s3_lifecycle           # применить
    python -m scripts.s3_lifecycle --show    # показать текущее правило
"""

import sys

import boto3

from app.core.config import settings

# 1095 (retention в коде) + 5 дней буфера: loop удаляет первым, lifecycle — backstop.
_EXPIRE_DAYS = 1100
_RULE_ID = "lawdocs-documents-expiry"


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def _lifecycle_config() -> dict:
    return {
        "Rules": [
            {
                "ID": _RULE_ID,
                "Status": "Enabled",
                "Filter": {"Prefix": ""},  # все объекты бакета — это бакет только документов
                "Expiration": {"Days": _EXPIRE_DAYS},
                # Подчистка незавершённых multipart-загрузок (мусор от сбоев аплоада).
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
            }
        ]
    }


def show() -> None:
    client = _client()
    try:
        resp = client.get_bucket_lifecycle_configuration(Bucket=settings.S3_BUCKET)
        print(resp.get("Rules"))
    except client.exceptions.ClientError as e:
        print(f"no lifecycle / error: {e}")


def apply() -> None:
    if not settings.S3_BUCKET:
        sys.exit("S3_BUCKET не задан")
    client = _client()
    client.put_bucket_lifecycle_configuration(
        Bucket=settings.S3_BUCKET,
        LifecycleConfiguration=_lifecycle_config(),
    )
    print(f"lifecycle applied to {settings.S3_BUCKET}: expire after {_EXPIRE_DAYS} days")


if __name__ == "__main__":
    show() if "--show" in sys.argv else apply()
