from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CAMS API",
    description="Chess Academy Management System API",
    version="1.0.0"
)

from app.core.config import settings

# CORS: only the configured domains (CORS_ORIGINS env), never "*" with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

from app.api.api import api_router

@app.get("/")
async def root():
    return {"message": "Welcome to CAMS API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

from app.websocket.game_handler import router as websocket_router
app.include_router(websocket_router)
app.include_router(api_router, prefix="/api")

# NOTE: no public static mount for scan files. Files are private and served
# via short-lived signed URLs (MinIO presigned or /api/files/...).

