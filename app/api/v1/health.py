from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        async for db in get_db():
            # Test database connection
            result = await db.execute(sa_text("SELECT 1"))
            await result.fetchone()
            return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "message": f"Database connection failed: {str(e)}"}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        
        return {"status": "healthy", "message": "Redis connection successful"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "unhealthy", "message": f"Redis connection failed: {str(e)}"}


async def check_tmdb() -> dict[str, Any]:
    """Check TMDB API connectivity."""
    try:
        import httpx
        
        if not settings.tmdb_api_key or settings.tmdb_api_key == "your-tmdb-api-key-here":
            return {"status": "warning", "message": "TMDB API key not configured"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.tmdb_base_url}/configuration",
                params={"api_key": settings.tmdb_api_key},
                timeout=5.0
            )
            response.raise_for_status()
            
        return {"status": "healthy", "message": "TMDB API connection successful"}
    except Exception as e:
        logger.error("TMDB health check failed", error=str(e))
        return {"status": "warning", "message": f"TMDB API connection failed: {str(e)}"}


@router.get("/")
async def health_check():
    """Comprehensive health check endpoint."""
    start_time = datetime.utcnow()
    
    # Run all health checks in parallel
    db_check, redis_check, tmdb_check = await asyncio.gather(
        check_database(),
        check_redis(),
        check_tmdb(),
        return_exceptions=True
    )
    
    # Calculate response time
    response_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Determine overall health
    checks = {
        "database": db_check if not isinstance(db_check, Exception) else {"status": "unhealthy", "message": str(db_check)},
        "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "unhealthy", "message": str(redis_check)},
        "tmdb": tmdb_check if not isinstance(tmdb_check, Exception) else {"status": "unhealthy", "message": str(tmdb_check)},
    }
    
    # Overall status
    unhealthy_checks = [name for name, check in checks.items() if check["status"] == "unhealthy"]
    warning_checks = [name for name, check in checks.items() if check["status"] == "warning"]
    
    if unhealthy_checks:
        overall_status = "unhealthy"
        status_code = 503
    elif warning_checks:
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200
    
    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.app_version,
        "environment": settings.app_env,
        "response_time_ms": round(response_time * 1000, 2),
        "checks": checks,
    }
    
    if overall_status == "unhealthy":
        raise HTTPException(status_code=status_code, detail=response)
    
    return response


@router.get("/simple")
async def simple_health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.app_version,
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check if database is ready
        async for db in get_db():
            await db.execute(sa_text("SELECT 1"))
            break
        
        return {"status": "ready", "message": "Application is ready to serve requests"}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail={"status": "not_ready", "message": str(e)})


@router.get("/live")
async def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "message": "Application is alive"}
