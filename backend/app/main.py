"""Punto di ingresso dell'applicazione FastAPI (Application Factory).

Costruisce e configura l'istanza FastAPI montando i router REST. L'uso di una
factory (`create_app`) rende l'applicazione facilmente istanziabile nei test
con configurazioni alternative.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.deps import get_health_monitor, get_rosout_monitor
from app.api.routes import api_router
from app.core.config import Settings, get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestisce avvio/arresto dei monitor in background.

    All'avvio vengono attivati il monitor ``/rosout`` (log live del grafo ROS)
    e il monitor di salute (misure di frequenza in background, fuori dal path
    HTTP per non saturare il threadpool). Allo spegnimento vengono fermati.

    Args:
        app: Istanza FastAPI (non usata direttamente).

    Yields:
        Il controllo all'applicazione mentre i monitor sono attivi.
    """
    rosout = get_rosout_monitor()
    health = get_health_monitor()
    rosout.start()
    health.start()
    try:
        yield
    finally:
        health.stop()
        rosout.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Crea e configura l'applicazione FastAPI.

    Args:
        settings: Impostazioni da usare; se ``None`` vengono caricate quelle di
            default dall'ambiente.

    Returns:
        L'istanza FastAPI configurata.
    """
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Backend di debugging e monitoraggio per un ecosistema ROS 2. "
            "Espone nodi, variabili d'ambiente, log e euristiche di salute."
        ),
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/healthz", tags=["meta"], summary="Liveness probe del backend")
    def healthz() -> dict[str, str]:
        """Verifica di vitalita' del backend stesso.

        Returns:
            Stato del servizio e versione applicativa.
        """
        return {"status": "ok", "version": __version__}

    return app


# Istanza usata da uvicorn (es. ``uvicorn app.main:app``).
app = create_app()
