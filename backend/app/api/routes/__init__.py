"""Aggregazione dei router REST dell'applicazione."""

from fastapi import APIRouter

from app.api.routes import connection, env, health, logs, nodes

# Router radice che monta tutti i sotto-router tematici.
api_router = APIRouter()
api_router.include_router(nodes.router)
api_router.include_router(env.router)
api_router.include_router(logs.router)
api_router.include_router(health.router)
api_router.include_router(connection.router)

__all__ = ["api_router"]
