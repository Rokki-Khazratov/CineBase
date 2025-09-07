from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import cache, health

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(health.router)
api_router.include_router(cache.router)
