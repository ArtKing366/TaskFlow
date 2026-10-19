import pytest

from app.webhook_service import validate_webhook_url
from app.celery_tasks import send_webhook


def test_webhook_rejects_loopback_url():
    with pytest.raises(ValueError):
        validate_webhook_url("https://127.0.0.1:8000/callback")


def test_webhook_rejects_private_network_url():
    with pytest.raises(ValueError):
        validate_webhook_url("https://192.168.1.10/callback")


def test_webhook_rejects_non_https_url():
    with pytest.raises(ValueError, match="HTTPS"):
        validate_webhook_url("http://example.com/callback")


def test_webhook_task_has_retry_limit():
    assert send_webhook.max_retries == 2
