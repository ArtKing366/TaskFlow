from uuid import uuid4


def test_create_workspace(client, authenticated_user):
    name = f"New-Workspace-{uuid4().hex[:8]}"

    response = client.post(
        "/workspaces",
        json={"name": name},
        headers=authenticated_user["headers"],
    )

    assert response.status_code in (200, 201)
    assert response.json()["name"] == name
    assert "id" in response.json()


def test_list_only_own_workspaces(client, owner, user_factory):
    workspace_id = owner["workspace"]["id"]

    own_response = client.get(
        "/workspaces",
        headers=owner["headers"],
    )

    assert own_response.status_code == 200
    assert any(
        item["id"] == workspace_id
        for item in own_response.json()
    )

    outsider = user_factory()

    outsider_response = client.get(
        "/workspaces",
        headers=outsider["headers"],
    )

    assert outsider_response.status_code == 200
    assert all(
        item["id"] != workspace_id
        for item in outsider_response.json()
    )


def test_non_member_cannot_open_workspace(
    client,
    owner,
    user_factory,
):
    outsider = user_factory()
    workspace_id = owner["workspace"]["id"]

    response = client.get(
        f"/workspaces/{workspace_id}",
        headers=outsider["headers"],
    )

    assert response.status_code == 403


def test_owner_can_add_member(
    client,
    owner,
    user_factory,
):
    member = user_factory()
    workspace_id = owner["workspace"]["id"]

    response = client.post(
        f"/workspaces/{workspace_id}/members",
        json={
            "user_id": member["id"],
            "role": "member",
        },
        headers=owner["headers"],
    )

    assert response.status_code in (200, 201)

    member_response = client.get(
        f"/workspaces/{workspace_id}",
        headers=member["headers"],
    )

    assert member_response.status_code == 200


def test_owner_can_change_member_role(
    client,
    owner,
    member_factory,
):
    member = member_factory("member")
    workspace_id = owner["workspace"]["id"]

    response = client.patch(
        f"/workspaces/{workspace_id}/members/"
        f"{member['id']}/role",
        json={"role": "viewer"},
        headers=owner["headers"],
    )

    assert response.status_code == 200


def test_owner_can_remove_member(
    client,
    owner,
    member_factory,
):
    member = member_factory("member")
    workspace_id = owner["workspace"]["id"]

    response = client.delete(
        f"/workspaces/{workspace_id}/members/{member['id']}",
        headers=owner["headers"],
    )

    assert response.status_code in (200, 204)

    access_response = client.get(
        f"/workspaces/{workspace_id}",
        headers=member["headers"],
    )

    assert access_response.status_code == 403