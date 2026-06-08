"""Тесты batch-удаления объектов S3 (DR / retention)."""

import asyncio

import pytest

from app.services import storage


class _FakeS3:
    def __init__(self):
        self.deleted_batches = []

    def delete_objects(self, Bucket, Delete):  # noqa: N803 — сигнатура boto3
        keys = [o["Key"] for o in Delete["Objects"]]
        self.deleted_batches.append(keys)
        return {"Errors": []}


@pytest.fixture
def fake_s3(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(storage, "_client", lambda: fake)
    return fake


def test_delete_objects_skips_empty(fake_s3):
    assert asyncio.run(storage.delete_objects([])) == 0
    assert asyncio.run(storage.delete_objects([None, "", None])) == 0
    assert fake_s3.deleted_batches == []


def test_delete_objects_counts_and_filters(fake_s3):
    n = asyncio.run(storage.delete_objects(["a/1.pdf", "", "a/2.docx", None]))
    assert n == 2
    assert fake_s3.deleted_batches == [["a/1.pdf", "a/2.docx"]]


def test_delete_objects_batches_over_1000(fake_s3):
    keys = [f"k/{i}" for i in range(2300)]
    n = asyncio.run(storage.delete_objects(keys))
    assert n == 2300
    assert [len(b) for b in fake_s3.deleted_batches] == [1000, 1000, 300]


def test_delete_objects_reports_partial_errors(fake_s3, monkeypatch):
    def with_error(Bucket, Delete):  # noqa: N803
        return {"Errors": [{"Key": Delete["Objects"][0]["Key"], "Message": "denied"}]}

    monkeypatch.setattr(fake_s3, "delete_objects", with_error)
    n = asyncio.run(storage.delete_objects(["x", "y", "z"]))
    assert n == 2  # 3 запрошено, 1 ошибка
