from uuid import uuid4


def _create_task(
    client,
    owner,
    workspace,
    project,
    *,
    title=None,
    status="todo",
    priority="high",
    deadline=None,
):
    title = title or f"Task-{uuid4().hex[:8]}"

    payload = {
        "project_id": project["id"],
        "title": title,
        "description": "Created by pytest",
        "status": status,
        "priority": priority,
    }

    if deadline is not None:
        payload["deadline"] = deadline

    headers = {
        **owner["headers"],
        "Idempotency-Key": f"task-{uuid4().hex}",
    }

    response = client.post(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, (
        f"Task creation failed: "
        f"{response.status_code} {response.text}"
    )

    return response.json()


def test_create_task(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])

    task = _create_task(client, owner, workspace, project)

    assert task["id"] is not None
    assert task["title"]
    assert task["project_id"] == project["id"]


def test_list_tasks(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    created = _create_task(
        client, owner, workspace, project
    )

    response = client.get(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert any(
        task["id"] == created["id"]
        for task in response.json()
    )


def test_get_single_task(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    created = _create_task(
        client, owner, workspace, project
    )

    response = client.get(
        f"/workspaces/{workspace['id']}"
        f"/tasks/{created['id']}",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_update_task(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    created = _create_task(
        client, owner, workspace, project
    )

    response = client.patch(
        f"/workspaces/{workspace['id']}"
        f"/tasks/{created['id']}",
        json={"title": "Updated task title"},
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated task title"


def test_delete_task(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])
    created = _create_task(
        client, owner, workspace, project
    )
    response = client.delete(
        f"/workspaces/{workspace['id']}"
        f"/tasks/{created['id']}",
        headers=owner["headers"],
    )

    assert response.status_code in (200, 204)


def test_combined_status_priority_and_search_filters(
    client,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])

    matching = _create_task(
        client,
        owner,
        workspace,
        project,
        title="pytest-match-alpha",
        status="todo",
        priority="high",
    )

    _create_task(
        client,
        owner,
        workspace,
        project,
        title="pytest-match-beta",
        status="done",
        priority="high",
    )

    _create_task(
        client,
        owner,
        workspace,
        project,
        title="pytest-match-gamma",
        status="todo",
        priority="low",
    )

    response = client.get(
        f"/workspaces/{workspace['id']}"
        f"/projects/{project['id']}/tasks",
        params={
            "status": "todo",
            "priority": "high",
            "search": "pytest-match-alpha",
        },
        headers=owner["headers"],
    )

    assert response.status_code == 200

    task_ids = [task["id"] for task in response.json()]
    assert task_ids == [matching["id"]]