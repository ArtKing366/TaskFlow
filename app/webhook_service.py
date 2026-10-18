import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urlsplit
from app.celery_tasks import send_webhook

import httpx
from sqlalchemy.orm import Session

from app.models import Project, Task, Webhook, WebhookDelivery


def validate_webhook_url(url: str) -> None:

    parsed = urlsplit(url)

    if parsed.scheme.lower() != "https":
        raise ValueError("Webhook URL must use HTTPS")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Webhook URL must not contain credentials")

    hostname = parsed.hostname

    if not hostname:
        raise ValueError("Webhook URL must contain a hostname")

    hostname = hostname.lower().rstrip(".")

    if (
        hostname == "localhost"
        or hostname.endswith((".localhost", ".local"))
    ):
        raise ValueError("Local webhook addresses are not allowed")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ValueError("Webhook hostname could not be resolved") from exc

    resolved_ips = set()

    for address in addresses:
        raw_ip = address[4][0].split("%", 1)[0]
        resolved_ips.add(ipaddress.ip_address(raw_ip))

    if not resolved_ips:
        raise ValueError("Webhook hostname has no resolved IP addresses")

    if any(not address.is_global for address in resolved_ips):
        raise ValueError("Webhook URL must resolve to public IP addresses")


def project_payload(project: Project) -> dict:

    return {
        "project_id": project.id,
        "workspace_id": project.workspace_id,
        "title": project.title,
        "description": project.description,
    }


def task_payload(task: Task) -> dict:

    status_value = task.status
    priority_value = task.priority

    if hasattr(status_value, "value"):
        status_value = status_value.value

    if hasattr(priority_value, "value"):
        priority_value = priority_value.value

    return {
        "task_id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "status": status_value,
        "priority": priority_value,
        "deadline": (
            task.deadline.isoformat()
            if task.deadline is not None
            else None
        ),
        "assignee_id": task.assignee_id,
    }


def dispatch_webhooks(
    db: Session,
    workspace_id: int,
    event_name: str,
    data: dict,
) -> None:
    webhooks = (
        db.query(Webhook)
        .filter(
            Webhook.workspace_id == workspace_id,
            Webhook.is_active.is_(True),
        )
        .all()
    )

    matching_webhooks = [
        (webhook.id, str(webhook.url))
        for webhook in webhooks
        if isinstance(webhook.events, list)
        and event_name in webhook.events
    ]


    for webhook_id, url in matching_webhooks:
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event=event_name,
            status="pending",
            attempts=0,
        )

        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        delivery_id = delivery.id

        payload = {
            "delivery_id": delivery_id,
            "event": event_name,
            "workspace_id": workspace_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        try:
            send_webhook.delay(
                delivery_id,
                url,
                payload,
            )

        except Exception as exc:
            db.rollback()

            failed_delivery = (
                db.query(WebhookDelivery)
                .filter(WebhookDelivery.id == delivery_id)
                .first()
            )

            if failed_delivery is not None:
                failed_delivery.status = "failed"
                failed_delivery.last_error = (
                    f"Failed to enqueue Celery task: {exc}"
                )[:4000]

                db.commit()