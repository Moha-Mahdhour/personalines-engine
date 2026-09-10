"""Command line: python -m personalines {webhook,realtime,check}"""
from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .config import ConfigError, Settings


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="personalines", description="Personalines lead enrichment and personalization engine")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="command", required=True)
    w = sub.add_parser("webhook", help="serve POST /api for Supabase database webhooks")
    w.add_argument("--host", default="0.0.0.0")
    w.add_argument("--port", type=int, default=None, help="defaults to $PORT or 10000")
    sub.add_parser("realtime", help="listen to Supabase Realtime for task changes")
    sub.add_parser("check", help="validate configuration and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(threadName)s %(message)s")
    try:
        settings = Settings.from_env()
        if args.command == "check":
            settings.require("supabase_url", "supabase_key", "proxycurl_key", "openai_api_key")
            print(f"config ok: model={settings.openai_model} concurrency={settings.max_concurrency} "
                  f"bucket={settings.storage_bucket} table={settings.tasks_table}")
            return 0
        from .engine import build_engine
        engine = build_engine(settings)
        if args.command == "webhook":
            from .entrypoints.webhook import serve
            serve(engine, args.host, args.port or settings.webhook_port)
        else:
            from .entrypoints.realtime import listen
            listen(engine, settings)
        return 0
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
