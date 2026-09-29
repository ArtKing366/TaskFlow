from fastapi import FastAPI
from app.routers.auth import router as auth_router
from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.workspaces import router as workspaces_router

app = FastAPI(
    title="TaskFlow API",
    description="REST API for project and task management",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"message": "TaskFlow API is running"}

app.include_router(auth_router)
app.include_router(auth_router)
app.include_router(workspaces_router)

