from fastapi import APIRouter
from app.api.endpoints import assignments, auth, classes, leaderboard, progress, puzzles, scan

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(scan.router, prefix="/scan", tags=["scan"])
api_router.include_router(puzzles.router, prefix="/puzzles", tags=["puzzles"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])

