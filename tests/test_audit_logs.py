from app.models import AuditLog


def test_project_creation_writes_audit_log(
    db,
    owner,
    workspace,
    project_factory,
):
    project = project_factory(owner, workspace["id"])

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.workspace_id == workspace["id"])
        .all()
    )

    matching_logs = [
        log
        for log in logs
        if str(log.entity_id) == str(project["id"])
        and "project" in log.entity_type.lower()
    ]

    assert matching_logs, (
        "Project creation did not produce an audit log entry"
    )


def test_workspace_member_can_read_audit_logs(
    client,
    owner,
    workspace,
    project_factory,
):
    project_factory(owner, workspace["id"])

    response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs/",
        headers=owner["headers"],
    )

    assert response.status_code == 200


def test_non_member_cannot_read_audit_logs(
    client,
    owner,
    workspace,
    user_factory,
):
    outsider = user_factory()

    response = client.get(
        f"/workspaces/{workspace['id']}/audit-logs/",
        headers=outsider["headers"],
    )

    assert response.status_code == 403