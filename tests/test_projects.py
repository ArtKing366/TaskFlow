def test_create_project(
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])

    assert project["id"] is not None
    assert project["title"]


def test_get_projects_list(
    client,
    owner,
    workspace,
    project_factory,
):
    created = project_factory(owner, workspace["id"])

    response = client.get(
        f"/workspaces/{workspace['id']}/projects/",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert any(
        project["id"] == created["id"]
        for project in response.json()
    )


def test_get_single_project(
    client,
    owner,
    workspace,
    project_factory,
):
    created = project_factory(owner, workspace["id"])

    response = client.get(
        f"/workspaces/{workspace['id']}/projects/{created['id']}",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_update_project(
    client,
    owner,
    workspace,
    project_factory,
):
    created = project_factory(owner, workspace["id"])

    response = client.patch(
        f"/workspaces/{workspace['id']}/projects/{created['id']}",
        json={
            "title": "Updated Project Title",
            "description": "Updated by Pytest",
        },
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Project Title"


def test_delete_project(
    client,
    owner,
    workspace,
    project_factory,
):
    created = project_factory(owner, workspace["id"])

    response = client.delete(
        f"/workspaces/{workspace['id']}/projects/{created['id']}",
        headers=owner["headers"],
    )

    assert response.status_code in (200, 204)

    read_response = client.get(
        f"/workspaces/{workspace['id']}/projects/{created['id']}",
        headers=owner["headers"],
    )

    assert read_response.status_code == 404


def test_create_project_requires_idempotency_key(
    client,
    owner,
    workspace,
    project_payload,
):
    response = client.post(
        f"/workspaces/{workspace['id']}/projects/",
        json=project_payload(workspace["id"]),
        headers=owner["headers"],
    )

    # В текущем endpoint заголовок обязателен.
    assert response.status_code == 422


def test_get_nonexistent_project_returns_404(
    client,
    owner,
    workspace,
):
    response = client.get(
        f"/workspaces/{workspace['id']}/projects/999999999",
        headers=owner["headers"],
    )

    assert response.status_code == 404


def test_project_access_denied_to_other_user(
    client,
    owner,
    workspace,
    project_factory,
    user_factory,
):
    created = project_factory(owner, workspace["id"])
    outsider = user_factory()

    response = client.get(
        f"/workspaces/{workspace['id']}/projects/{created['id']}",
        headers=outsider["headers"],
    )

    assert response.status_code == 403