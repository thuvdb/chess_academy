from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CAMS API",
    description="Chess Academy Management System API",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
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

from fastapi.staticfiles import StaticFiles
from app.services.pdf_service import SCAN_STORAGE_PATH
SCAN_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
app.mount("/scans", StaticFiles(directory=str(SCAN_STORAGE_PATH)), name="scans")

