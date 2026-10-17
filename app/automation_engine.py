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


def send_notification(db: Session,automation: Automation,task: Task,workspace_id: int,
) -> None:
    action = automation.action

    if not isinstance(action, dict):
        return

    if action.get("type") != "send_notification":
        return

    if action.get("recipients") != "workspace_members":
        return

    memberships = (
        db.query(Membership)
        .filter(Membership.workspace_id == workspace_id)
        .all()
    )

    message = (
        f'Task "{task.title}" was completed '
        f'by automation "{automation.name}".'
    )

    for membership in memberships:
        notification = Notification(
            user_id=membership.user_id,
            workspace_id=workspace_id,
            task_id=task.id,
            message=message,
        )

        db.add(notification)


def dispatch_event(db: Session,workspace_id: int,event_name: str,task: Task,) -> None:
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

        if (
            isinstance(automation.action, dict)
            and automation.action.get("type") == "send_notification"
        ):
            send_notification(
                db=db,
                automation=automation,
                task=task,
                workspace_id=workspace_id,
            )