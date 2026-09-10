"""Supabase Realtime entrypoint (optional 'realtime' extra)."""
from __future__ import annotations

import logging

from ..config import Settings
from ..engine import Engine

log = logging.getLogger("personalines")


def listen(engine: Engine, settings: Settings) -> None:
    project = settings.supabase_project_id
    if not project:
        raise RuntimeError("SUPABASE_URL must be a https://<project>.supabase.co URL for realtime mode")
    try:
        from realtime.connection import Socket
    except ImportError as exc:
        raise RuntimeError("Install the 'realtime' extra: pip install '.[realtime]'") from exc

    url = f"wss://{project}.supabase.co/realtime/v1/websocket?apikey={settings.supabase_key}&vsn=1.0.0"
    socket = Socket(url)
    socket.connect()
    channel = socket.set_channel(f"realtime:public:{settings.tasks_table}")
    # Join once and register both events; the old code joined twice.
    channel.join().on("INSERT", engine.dispatcher.dispatch).on("UPDATE", engine.dispatcher.dispatch)
    engine.start()
    log.info("listening for task events on %s", settings.tasks_table)
    try:
        socket.listen()
    finally:
        engine.stop()
