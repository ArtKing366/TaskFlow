from uuid import uuid4

from app.models import Task


def _task_payload(project, title):
    return {
        "project_id": project["id"],
        "title": title,
        "description": "Idempotency test",
        "status": "todo",
        "priority": "high",
    }


def _post_task(
    client,
    owner,
    workspace,
    project,
    payload,
    key,
):
    return client.post(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        json=payload,
        headers={
            **owner["headers"],
            "Idempotency-Key": key,
        },
    )


def test_same_key_and_same_body_create_one_task(
    client,
    db,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    key = f"pytest-{uuid4().hex}"
    title = f"Idempotent-{uuid4().hex[:8]}"
    payload = _task_payload(project, title)

    first = _post_task(
        client, owner, workspace, project, payload, key
    )
    second = _post_task(
        client, owner, workspace, project, payload, key
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    count = (
        db.query(Task)
        .filter(
            Task.project_id == project["id"],
            Task.title == title,
        )
        .count()
    )

    assert count == 1


def test_same_key_different_body_returns_409(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    key = f"pytest-{uuid4().hex}"

    first = _post_task(
        client,
        owner,
        workspace,
        project,
        _task_payload(project, "First task"),
        key,
    )

    second = _post_task(
        client,
        owner,
        workspace,
        project,
        _task_payload(project, "Different task"),
        key,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409


def test_missing_idempotency_key_is_rejected(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])

    response = client.post(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        json=_task_payload(project, "Missing key test"),
        headers=owner["headers"],
    )

    assert response.status_code == 422


def test_different_keys_can_create_separate_tasks(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    payload = _task_payload(project, "Two separate operations")

    first = _post_task(
        client,
        owner,
        workspace,
        project,
        payload,
        f"first-{uuid4().hex}",
    )

    second = _post_task(
        client,
        owner,
        workspace,
        project,
        payload,
        f"second-{uuid4().hex}",
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]