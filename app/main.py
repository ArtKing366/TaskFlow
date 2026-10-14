from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.workspaces import router as workspaces_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router
from app.routers.audit_logs import router as audit_logs_router


app = FastAPI(
    title="TaskFlow API",
    description="REST API for project and task management",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"message": "TaskFlow API is running"}


app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(audit_logs_router)