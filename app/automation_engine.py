from sqlalchemy.orm import Session

from app.models import Automation, Membership, Notification, Task


def condition_matches(task: Task,condition: dict | None,) -> bool:

    if condition is None:
        return True

    if condition.get("field") != "priority":
        return False

    if condition.get("operator") != "eq":
        return False

    expected_value = condition.get("value")
    actual_value = task.priority

    if hasattr(actual_value, "value"):
        actual_value = actual_value.value

    if hasattr(expected_value, "value"):
        expected_value = expected_value.value

    return actual_value == expected_value


def send_notification(
    db: Session,
    automation: Automation,
    task: Task,
    workspace_id: int,
) -> None:

    action = automation.action

    if not isinstance(action, dict):
        return

    if action.get("type") != "send_notification":
        return

    recipients = action.get("recipients")

    if recipients != "workspace_members":
        return

    from app.celery_tasks import create_notifications

    create_notifications.delay(
        workspace_id,
        task.id,
        automation.name,
        recipients,
    )


def dispatch_event(
    db: Session,
    workspace_id: int,
    event_name: str,
    task: Task,
) -> None:

    automations = (
        db.query(Automation)
        .filter(
            Automation.workspace_id == workspace_id,
            Automation.trigger == event_name,
            Automation.is_active.is_(True),
        )
        .all()
    )

    for automation in automations:
        if not condition_matches(task, automation.condition):
            continue

        send_notification(
            db=db,
            automation=automation,
            task=task,
            workspace_id=workspace_id,
        )