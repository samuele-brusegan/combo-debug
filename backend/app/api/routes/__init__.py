"""Aggregazione dei router REST dell'applicazione."""

from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.api.routes import (
    auth,
    connection,
    diagnostics,
    env,
    graph,
    logs,
    nodes,
    params,
    tf,
    topics,
)

# Router radice che monta tutti i sotto-router tematici.
api_router = APIRouter()

# Le route di autenticazione sono pubbliche (servono a ottenere il token).
api_router.include_router(auth.router)

# Tutte le altre route sono protette da `require_auth`, che e' un no-op quando
# l'autenticazione e' disabilitata da configurazione (default).
_protected = [
    nodes.router,
    env.router,
    logs.router,
    graph.router,
    connection.router,
    params.router,
    topics.router,
    diagnostics.router,
    tf.router,
]
for _router in _protected:
    api_router.include_router(_router, dependencies=[Depends(require_auth)])

__all__ = ["api_router"]
