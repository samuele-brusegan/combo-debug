"""Test del servizio di streaming on-demand dei messaggi di un topic."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.api.deps import get_topic_echo_service
from app.core.config import Settings
from app.main import create_app
from app.services.topic_echo_service import TopicEchoService, format_sse
from tests.fakes import FakeRosCommandRunner


def _collect(agen: AsyncIterator[str]) -> list[str]:
    """Consuma un generatore asincrono restituendo la lista degli elementi."""

    async def run() -> list[str]:
        return [chunk async for chunk in agen]

    return asyncio.run(run())


def _service(lines: list[str]) -> TopicEchoService:
    """Crea un service il cui runner produce in streaming `lines`."""
    runner = FakeRosCommandRunner({}, {("topic", "echo"): lines})
    return TopicEchoService(runner=runner, settings=Settings())


def test_format_sse_prefixes_each_line() -> None:
    """Un payload multiriga deve avere ogni riga prefissata con ``data: ``."""
    assert format_sse("a\nb", "message") == "event: message\ndata: a\ndata: b\n\n"


def test_format_sse_without_event() -> None:
    """Senza nome evento si emettono solo le righe ``data:``."""
    assert format_sse("x") == "data: x\n\n"


def test_stream_emits_one_event_per_message() -> None:
    """Ogni blocco separato da ``---`` diventa un evento ``message``."""
    service = _service(["data: hello", "---", "data: world", "---"])
    chunks = _collect(service.stream("/chatter"))
    joined = "".join(chunks)
    assert "event: info" in chunks[0]
    assert joined.count("event: message") == 2
    assert "data: data: hello" in joined
    assert "data: data: world" in joined
    assert "event: end" in chunks[-1]
    assert "senza messaggi" not in chunks[-1]


def test_stream_groups_multiline_messages() -> None:
    """Le righe di un messaggio multiriga restano nello stesso evento."""
    service = _service(["header:", "  frame_id: base", "data: 1", "---"])
    chunks = _collect(service.stream("/pose"))
    message_events = [c for c in chunks if c.startswith("event: message")]
    assert len(message_events) == 1
    assert "data: header:" in message_events[0]
    assert "data:   frame_id: base" in message_events[0]


def test_stream_without_messages_reports_silent_topic() -> None:
    """Se non arriva nessun messaggio l'evento finale lo segnala."""
    service = _service([])
    chunks = _collect(service.stream("/silent"))
    assert all("event: message" not in c for c in chunks)
    assert "senza messaggi" in chunks[-1]


def test_echo_stream_route_returns_event_stream() -> None:
    """L'endpoint risponde con content-type SSE ed emette gli eventi attesi."""
    app = create_app(Settings())
    service = _service(["data: ciao", "---"])
    app.dependency_overrides[get_topic_echo_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/topics/echo/stream", params={"topic": "/chatter"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in response.text
    assert "data: data: ciao" in response.text
