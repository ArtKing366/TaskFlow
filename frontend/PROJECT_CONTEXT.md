# TaskFlow project context for future work

## Goal

TaskFlow is a production-style FastAPI backend for workspace/project/task management, with workflow automation, audit logs, Redis caching, Celery background jobs, webhooks and idempotency. The current work is a separate React/TypeScript frontend; deployment is intentionally deferred until the integrated app and visual experience are ready.

## Backend files received and reviewed for the frontend

- `app/main.py`: creates FastAPI app titled `TaskFlow API` v1.0.0 and includes auth, workspaces, projects, tasks, audit-log, automation, notification and webhook routers.
- `app/auth.py`: password hashing/verification via pwdlib `PasswordHash.recommended()`, JWT HS256 with `sub` user ID and 30-minute expiry; `get_current_user` reads `Authorization: Bearer <token>` and loads the SQLAlchemy User.
- `app/database.py`: SQLAlchemy engine from `DATABASE_URL`, `get_db`, `SessionLocal`.
- `app/models.py`: User; Workspace; Membership; Project; Task; Tag/TaskTag; AuditLog; Automation; Notification; Webhook; WebhookDelivery; IdempotencyRecord. Roles: owner/admin/member/viewer. Task status: todo/in_progress/done. Priority: low/medium/high.
- `app/schemas.py`: request/response schemas. Task create requires title, description, status, priority and project_id, optional deadline and assignee_id. ProjectCreate requires workspace_id/title/description. Automation only supports trigger `task.completed`, optional condition `{field: priority, operator: eq, value: low|medium|high}`, and `send_notification` to `workspace_members`. Webhook events: task.created, task.updated, task.completed, project.created.
- `app/permissions.py`: workspace membership and admin/owner/editor access guards; `require_editor` rejects viewers, while owner/admin/member may edit.
- `app/crud.py`: project/task CRUD; task-completion automation/webhook dispatch; audit event creation; automation, notification and webhook database operations.
- `app/idempotency.py`: `execute_idempotent` hashes the JSON request body, scopes keys to user+endpoint+key and replays a stored response for repeated successful requests; reused key with different body and in-progress key return 409.
- `app/redis_cache.py`: cache URL is `REDIS_CACHE_URL` (default `redis://localhost:6379/1`), JSON helpers and cache invalidation.
- `app/celery_app.py`: Celery instance import path `app.celery_app:celery_app`; broker env `CELERY_BROKER_URL`, result backend env `CELERY_RESULT_BACKEND`; includes `app.celery_tasks`.
- `app/automation_engine.py`: dispatches active automation rules matching workspace and event; condition handles priority eq; action enqueues `create_notifications.delay`.
- `app/celery_tasks.py`: webhook send task with max_retries=2 and notification creation task.
- `app/webhook_service.py`: payload builders; validates HTTPS/public DNS destination; queues matching webhook deliveries via Celery.

## API routes seen in actual router files

- Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`. Register returns UserResponse, not a token; login returns `{access_token, token_type}` and accepts `{email,password}`.
- Workspaces: `POST /workspaces`, `GET /workspaces`, `GET /workspaces/{workspace_id}`, `POST /workspaces/{workspace_id}/members`, `PATCH /workspaces/{workspace_id}/members/{user_id}/role`, `DELETE /workspaces/{workspace_id}/members/{user_id}`.
- Projects: `GET|POST /workspaces/{workspace_id}/projects/`, `GET|PATCH|DELETE /workspaces/{workspace_id}/projects/{project_id}`. Project POST requires `Idempotency-Key`; request body includes matching workspace_id.
- Tasks: `GET|POST /workspaces/{workspace_id}/projects/{project_id}/tasks`, `GET|PATCH|DELETE /workspaces/{workspace_id}/tasks/{task_id}`, `PATCH /workspaces/{workspace_id}/tasks/{task_id}/complete`, `PATCH /workspaces/{workspace_id}/tasks/{task_id}/assign/{assign_id}`. Task POST requires `Idempotency-Key`; body includes matching project_id. Task GET supports status, priority, assignee_id, search query parameters.
- Audit log: `GET /workspaces/{workspace_id}/audit-logs/`.
- Automations: CRUD under `/workspaces/{workspace_id}/automations/`; creation requires `Idempotency-Key`.
- Notifications: `GET /workspaces/{workspace_id}/notifications/` (current user only).
- Webhooks: CRUD under `/workspaces/{workspace_id}/webhooks/`.

## Current API gaps (do not fake in the frontend)

- There is no endpoint to list workspace members, despite add/change/remove endpoints.
- There is no endpoint to mark a notification read.
- There is no endpoint to list webhook delivery attempts.
- Although Tag/TaskTag models and schemas exist, no tag router is wired in `app/main.py`.

## Frontend structure

React + TypeScript + Vite lives in `frontend/`. During local development, Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, so no backend CORS changes are necessary. Keep deployment separate until user requests it.
