from fastapi import APIRouter
from app.api.endpoints import (
    ai_tutor,
    assignments,
    auth,
    centers,
    classes,
    fee_plans,
    files,
    invoices,
    leaderboard,
    payments,
    progress,
    puzzles,
    scan,
    settings,
    tournaments,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(centers.router, prefix="/centers", tags=["centers"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(scan.router, prefix="/scan", tags=["scan"])
api_router.include_router(puzzles.router, prefix="/puzzles", tags=["puzzles"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])
api_router.include_router(fee_plans.router, prefix="/fee-plans", tags=["fee-plans"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(settings.settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(settings.catalogs_router, prefix="/catalogs", tags=["catalogs"])
api_router.include_router(ai_tutor.router, prefix="/ai-tutor", tags=["ai-tutor"])

