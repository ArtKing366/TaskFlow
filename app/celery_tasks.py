import httpx

from celery import Task as CeleryTask

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import (
    WebhookDelivery,
    Notification,
    Membership,
    Task,
    Project,
)
from app.webhook_service import validate_webhook_url


def _retry_or_fail(
    task: CeleryTask,
    db,
    delivery: WebhookDelivery,
    error: Exception,
):

    error_message = str(error)[:4000]

    if task.request.retries < task.max_retries:
        delivery.status = "pending"
        delivery.last_error = error_message
        db.commit()

        raise task.retry(
            exc=error,
            countdown=2 ** task.request.retries,
        )

    delivery.status = "failed"
    delivery.last_error = error_message
    db.commit()

    return {
        "delivery_id": delivery.id,
        "status": "failed",
        "attempts": delivery.attempts,
    }


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.celery_tasks.send_webhook",
)
def send_webhook(
    self,
    delivery_id: int,
    url: str,
    payload: dict,
):

    db = SessionLocal()

    try:
        delivery = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.id == delivery_id)
            .first()
        )

        if delivery is None:
            return {
                "delivery_id": delivery_id,
                "status": "not_found",
            }

        if delivery.status == "success":
            return {
                "delivery_id": delivery.id,
                "status": "success",
            }

        delivery.attempts += 1
        delivery.status = "pending"
        db.commit()

        try:
            validate_webhook_url(url)
        except (ValueError, OSError) as exc:
            delivery.status = "failed"
            delivery.last_error = str(exc)[:4000]
            db.commit()

            return {
                "delivery_id": delivery.id,
                "status": "failed",
                "attempts": delivery.attempts,
            }

        try:
            response = httpx.post(
                url,
                json=payload,
                headers={
                    "X-TaskFlow-Event": delivery.event,
                    "X-TaskFlow-Delivery": str(delivery.id),
                },
                timeout=10.0,
                follow_redirects=False,
            )

        except httpx.TransportError as exc:
            return _retry_or_fail(
                self,
                db,
                delivery,
                exc,
            )

        status_code = response.status_code

        if 200 <= status_code < 300:
            delivery.status = "success"
            delivery.last_error = None
            db.commit()

            return {
                "delivery_id": delivery.id,
                "status": "success",
                "attempts": delivery.attempts,
            }

        error = RuntimeError(
            f"Webhook endpoint returned HTTP {status_code}"
        )

        if status_code == 429 or 500 <= status_code <= 599:
            return _retry_or_fail(
                self,
                db,
                delivery,
                error,
            )

        delivery.status = "failed"
        delivery.last_error = str(error)
        db.commit()

        return {
            "delivery_id": delivery.id,
            "status": "failed",
            "attempts": delivery.attempts,
        }

    finally:
        db.close()


@celery_app.task(
    name="app.celery_tasks.create_notifications",
)
def create_notifications(
    workspace_id: int,
    task_id: int,
    automation_name: str,
    recipients: str,
):

    if recipients != "workspace_members":
        return {
            "status": "skipped",
            "reason": "Unsupported recipients",
        }

    db = SessionLocal()

    try:
        task = (
            db.query(Task)
            .join(Project, Task.project_id == Project.id)
            .filter(
                Task.id == task_id,
                Project.workspace_id == workspace_id,
            )
            .first()
        )

        if task is None:
            return {
                "status": "skipped",
                "reason": "Task not found",
            }

        memberships = (
            db.query(Membership)
            .filter(
                Membership.workspace_id == workspace_id,
            )
            .all()
        )

        message = (
            f'Task "{task.title}" was completed '
            f'by automation "{automation_name}".'
        )

        for membership in memberships:
            notification = Notification(
                user_id=membership.user_id,
                workspace_id=workspace_id,
                task_id=task.id,
                message=message,
            )

            db.add(notification)

        db.commit()

        return {
            "status": "success",
            "created": len(memberships),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()