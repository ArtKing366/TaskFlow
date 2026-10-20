# TaskFlow Frontend

A React + TypeScript + Vite frontend for the existing TaskFlow FastAPI backend. It uses the real API contracts found in `app/routers`, `app/schemas.py` and `app/models.py`.

## Requirements

- Node.js 20+ (Node 22 is fine)
- The existing TaskFlow FastAPI backend running on `http://127.0.0.1:8000`
- The backend's configured PostgreSQL/Redis/Celery services where needed

## Run on Windows

Keep your backend running in one CMD window from the TaskFlow backend root:

```bat
.venv\Scripts\activate.bat
py -m uvicorn app.main:app --reload
```

Open a second CMD window and run:

```bat
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

Vite forwards browser requests from `/api/...` to `http://127.0.0.1:8000/...` and removes the `/api` prefix. This avoids requiring a CORS change in the FastAPI app during local development.

## Features wired to the current backend

- Register, login and current-user session using `/auth/register`, `/auth/login`, `/auth/me`
- Create/select workspaces
- Project CRUD
- Task creation, editing, deletion, filtering and status board; task creation includes the `Idempotency-Key` header
- Automation CRUD for the currently supported `task.completed` trigger, optional priority condition and workspace notifications
- Webhook CRUD for the supported event types
- Workspace audit log and current-user notifications
- Add/change/remove workspace members by numeric user ID

## API constraints the UI does not invent around

The backend currently does **not** expose a workspace-member listing endpoint, a mark-notification-as-read endpoint, or a webhook-delivery history endpoint. Therefore, the Team page manages known user IDs rather than showing a roster; Notifications are read-only in the UI; webhook delivery attempts cannot be shown yet. These features need backend endpoints before the UI can offer those operations.

The existing API uses bearer JWT tokens that expire after 30 minutes. The frontend keeps the token in `localStorage`, sends it as `Authorization: Bearer ...`, and returns to the sign-in screen when the API rejects the session.

## Build

```bat
npm run build
```

For a future deployment, configure `VITE_API_BASE` / the reverse proxy to point the frontend at the deployed API. Deployment is intentionally not included here.
