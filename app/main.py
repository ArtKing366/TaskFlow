from fastapi import FastAPI
from app.routers.auth import router as auth_router

app = FastAPI(
    title="TaskFlow API",
    description="REST API for project and task management",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"message": "TaskFlow API is running"}



app.include_router(auth_router)

