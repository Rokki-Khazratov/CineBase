from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/cache", tags=["cache"])


async def get_redis_client():
    """Get Redis client."""
    import redis.asyncio as redis
    return redis.from_url(settings.redis_url)


@router.get("/test")
async def test_cache():
    """Test Redis cache functionality."""
    try:
        redis_client = await get_redis_client()
        
        # Test data
        test_key = "cinebase:test:cache"
        test_data = {
            "message": "Hello from CineBase+ cache!",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "test_id": int(time.time()),
        }
        
        # Set cache with TTL
        await redis_client.setex(
            test_key,
            60,  # 60 seconds TTL
            json.dumps(test_data)
        )
        
        # Get from cache
        cached_data = await redis_client.get(test_key)
        
        if cached_data:
            parsed_data = json.loads(cached_data)
            
            # Get cache info
            ttl = await redis_client.ttl(test_key)
            
            return {
                "status": "success",
                "message": "Cache test successful",
                "test_data": parsed_data,
                "cache_info": {
                    "key": test_key,
                    "ttl_seconds": ttl,
                    "size_bytes": len(cached_data),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve cached data")
            
    except Exception as e:
        logger.error("Cache test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Cache test failed: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()


@router.get("/stats")
async def cache_stats():
    """Get Redis cache statistics."""
    try:
        redis_client = await get_redis_client()
        
        # Get Redis info
        info = await redis_client.info()
        
        # Get memory usage
        memory_info = await redis_client.info("memory")
        
        # Get keyspace info
        keyspace_info = await redis_client.info("keyspace")
        
        # Count keys by pattern
        cinebase_keys = await redis_client.keys("cinebase:*")
        
        return {
            "status": "success",
            "redis_info": {
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": memory_info.get("used_memory_human"),
                "used_memory_peak_human": memory_info.get("used_memory_peak_human"),
                "keyspace": keyspace_info,
                "total_keys": info.get("db0", {}).get("keys", 0) if "db0" in keyspace_info else 0,
                "cinebase_keys_count": len(cinebase_keys),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("Cache stats failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Cache stats failed: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()


@router.post("/clear")
async def clear_cache():
    """Clear all CineBase cache."""
    try:
        redis_client = await get_redis_client()
        
        # Get all CineBase keys
        cinebase_keys = await redis_client.keys("cinebase:*")
        
        if cinebase_keys:
            # Delete all CineBase keys
            deleted_count = await redis_client.delete(*cinebase_keys)
            
            return {
                "status": "success",
                "message": f"Cleared {deleted_count} cache entries",
                "deleted_keys": deleted_count,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "success",
                "message": "No cache entries to clear",
                "deleted_keys": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
    except Exception as e:
        logger.error("Cache clear failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()


@router.get("/keys")
async def list_cache_keys():
    """List all CineBase cache keys."""
    try:
        redis_client = await get_redis_client()
        
        # Get all CineBase keys
        cinebase_keys = await redis_client.keys("cinebase:*")
        
        # Get TTL for each key
        keys_info = []
        for key in cinebase_keys:
            ttl = await redis_client.ttl(key)
            keys_info.append({
                "key": key.decode() if isinstance(key, bytes) else key,
                "ttl_seconds": ttl,
            })
        
        return {
            "status": "success",
            "keys": keys_info,
            "total_keys": len(keys_info),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("List cache keys failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"List cache keys failed: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()
