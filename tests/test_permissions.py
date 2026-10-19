def test_viewer_can_read_projects_but_cannot_create(
    client,
    owner,
    workspace,
    member_factory,
    project_factory,
    project_headers,
    project_payload,
):
    project_factory(owner, workspace["id"])

    viewer = member_factory("viewer")

    read_response = client.get(
        f"/workspaces/{workspace['id']}/projects/",
        headers=viewer["headers"],
    )

    assert read_response.status_code == 200

    create_response = client.post(
        f"/workspaces/{workspace['id']}/projects/",
        json=project_payload(workspace["id"]),
        headers=project_headers(viewer),
    )

    assert create_response.status_code == 403


def test_member_can_create_project(
    client,
    workspace,
    member_factory,
    project_factory,
):
    member = member_factory("member")

    project = project_factory(member, workspace["id"])

    assert project["id"] is not None


def test_member_cannot_add_another_member(
    client,
    owner,
    workspace,
    member_factory,
    user_factory,
):
    member = member_factory("member")
    target_user = user_factory()

    response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={
            "user_id": target_user["id"],
            "role": "member",
        },
        headers=member["headers"],
    )

    assert response.status_code == 403


def test_admin_can_add_member(
    client,
    owner,
    workspace,
    member_factory,
    user_factory,
):
    admin = member_factory("admin")
    target_user = user_factory()

    response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={
            "user_id": target_user["id"],
            "role": "member",
        },
        headers=admin["headers"],
    )

    assert response.status_code in (200, 201)


def test_non_member_cannot_read_projects(
    client,
    owner,
    workspace,
    user_factory,
):
    outsider = user_factory()

    response = client.get(
        f"/workspaces/{workspace['id']}/projects/",
        headers=outsider["headers"],
    )

    assert response.status_code == 403