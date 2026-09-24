from fastapi import FastAPI

app = FastAPI(
    title="TaskFlow API",
    description="REST API for project and task management",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {"message": "TaskFlow API is running"}