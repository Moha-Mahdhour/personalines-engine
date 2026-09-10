"""HTTP entrypoint for Supabase database webhooks (optional 'webhook' extra)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from ..engine import Engine


def create_app(engine: Engine):
    try:
        from fastapi import Body, FastAPI
    except ImportError as exc:
        raise RuntimeError("Install the 'webhook' extra: pip install '.[webhook]'") from exc

    @asynccontextmanager
    async def lifespan(_app):
        engine.start()
        yield
        engine.stop()

    app = FastAPI(title="Personalines Engine", lifespan=lifespan)

    @app.post("/api")
    def receive(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        return {"routed_to": engine.dispatcher.dispatch(payload)}

    @app.get("/healthz")
    def health() -> dict[str, Any]:
        workers = engine.health()
        return {"ok": all(workers.values()), "workers": workers}

    return app


def serve(engine: Engine, host: str = "0.0.0.0", port: int = 10000) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Install the 'webhook' extra: pip install '.[webhook]'") from exc
    uvicorn.run(create_app(engine), host=host, port=port)
