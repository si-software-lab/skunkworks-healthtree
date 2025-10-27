# fast api app
# api/main.py
from fastapi import FastAPI
from api.routers.metrics import router as metrics_router

app = FastAPI(title="Metrics Registry")

app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])

@app.get("/")
def root():
    return {"message": "Metrics Registry API is running"}