import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

# Configure logging level from settings
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Production security: disable Swagger docs and debug mode in production
is_prod = settings.APP_ENV == "production"
docs_url = None if is_prod else "/docs"
redoc_url = None if is_prod else "/redoc"
openapi_url = None if is_prod else "/openapi.json"
debug_mode = False if is_prod else settings.DEBUG

app = FastAPI(
    title="CAMS API",
    description="Chess Academy Management System API",
    version=settings.APP_VERSION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    debug=debug_mode,
)

# CORS: only the configured domains (BACKEND_CORS_ORIGINS), never "*" with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

from app.api.api import api_router
from app.websocket.game_handler import router as websocket_router

@app.get("/")
async def root():
    return {"message": "Welcome to CAMS API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(websocket_router)
app.include_router(api_router, prefix="/api")

# Static files mount (avatars, etc.) using configured UPLOAD_DIR
avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
os.makedirs(avatar_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")
