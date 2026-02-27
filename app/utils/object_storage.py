from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from flask import current_app


class ObjectStorageError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_client() -> BaseClient:
    endpoint = current_app.config.get("MINIO_ENDPOINT")
    access_key = current_app.config.get("MINIO_ACCESS_KEY")
    secret_key = current_app.config.get("MINIO_SECRET_KEY")
    secure = bool(current_app.config.get("MINIO_SECURE", False))
    region = current_app.config.get("MINIO_REGION", "us-east-1")

    if not endpoint or not access_key or not secret_key:
        raise ObjectStorageError("Configuração MinIO incompleta.")

    endpoint_url = endpoint
    if not endpoint_url.startswith("http://") and not endpoint_url.startswith("https://"):
        scheme = "https" if secure else "http"
        endpoint_url = f"{scheme}://{endpoint_url}"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def clear_client_cache() -> None:
    _get_client.cache_clear()


def generate_presigned_post(
    bucket: str,
    key: str,
    content_type: str,
    max_size_bytes: int,
    expires_in_seconds: int,
) -> dict[str, Any]:
    client = _get_client()
    conditions = [
        {"key": key},
        {"Content-Type": content_type},
        ["content-length-range", 1, max_size_bytes],
    ]
    fields = {
        "key": key,
        "Content-Type": content_type,
    }
    return client.generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expires_in_seconds,
    )


def head_object(bucket: str, key: str) -> dict[str, Any]:
    client = _get_client()
    return client.head_object(Bucket=bucket, Key=key)


def copy_object(src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
    client = _get_client()
    copy_source = {"Bucket": src_bucket, "Key": src_key}
    client.copy_object(Bucket=dest_bucket, Key=dest_key, CopySource=copy_source)


def delete_object(bucket: str, key: str) -> None:
    client = _get_client()
    client.delete_object(Bucket=bucket, Key=key)


def list_objects(bucket: str, prefix: str) -> list[dict[str, Any]]:
    client = _get_client()
    paginator = client.get_paginator("list_objects_v2")
    result: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            result.append(item)
    return result


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_in(seconds: int) -> datetime:
    return utc_now() + timedelta(seconds=seconds)
