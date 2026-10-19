from uuid import uuid4

from app.celery_tasks import create_notifications


def _create_automation(client, owner, workspace, priority):
    payload = {
        "name": f"pytest-{uuid4().hex[:8]}",
        "trigger": "task.completed",
        "condition": {
            "field": "priority",
            "operator": "eq",
            "value": priority,
        },
        "action": {
            "type": "send_notification",
            "recipients": "workspace_members",
        },
        "is_active": True,
    }

    response = client.post(
        f"/workspaces/{workspace['id']}/automations/",
        json=payload,
        headers={
            **owner["headers"],
            "Idempotency-Key": f"automation-{uuid4().hex}",
        },
    )

    assert response.status_code == 201, (
        f"Automation creation failed: "
        f"{response.status_code} {response.text}"
    )

    return response.json()


def _create_task(client, owner, workspace, project, priority):
    response = client.post(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        json={
            "project_id": project["id"],
            "title": f"pytest-{priority}-{uuid4().hex[:8]}",
            "description": "Automation test",
            "priority": priority,
            "status": "todo",
        },
        headers={
            **owner["headers"],
            "Idempotency-Key": f"task-{uuid4().hex}",
        },
    )

    assert response.status_code == 201, (
        f"Task creation failed: {response.status_code} {response.text}"
    )

    return response.json()


def _complete_task(client, owner, workspace, task):
    response = client.patch(
        f"/workspaces/{workspace['id']}"
        f"/tasks/{task['id']}/complete",
        headers=owner["headers"],
    )

    assert response.status_code == 200, (
        f"Task completion failed: {response.status_code} {response.text}"
    )

    return response.json()


def test_create_automation(client, owner, workspace):
    automation = _create_automation(
        client,
        owner,
        workspace,
        "high",
    )

    assert automation["id"] is not None
    assert automation["name"]


def test_matching_condition_triggers_notification(
    client,
    owner,
    workspace,
    project_factory,
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        create_notifications,
        "delay",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    _create_automation(client, owner, workspace, "high")

    project = project_factory(owner, workspace["id"])

    task = _create_task(
        client,
        owner,
        workspace,
        project,
        "high",
    )

    _complete_task(client, owner, workspace, task)

    assert calls, (
        "Matching automation did not schedule a notification"
    )


def test_non_matching_condition_does_not_trigger_notification(
    client,
    owner,
    workspace,
    project_factory,
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        create_notifications,
        "delay",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    _create_automation(client, owner, workspace, "high")

    project = project_factory(owner, workspace["id"])

    task = _create_task(
        client,
        owner,
        workspace,
        project,
        "low",
    )

    _complete_task(client, owner, workspace, task)

    assert calls == [], (
        "Notification was scheduled although the condition did not match"
    )