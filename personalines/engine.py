"""Wire the stages, workers and dispatcher together.

Every collaborator can be injected, which is how the end-to-end test runs a
whole job in memory; by default the production adapters are built from
Settings.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .config import Settings
from .dispatch import Dispatcher
from .enrichment import Enricher, ProxycurlEnricher
from .examples import ExampleBank
from .llm import ChatClient, OpenAIChatClient
from .pipeline import CollectorStage, PersonalizerStage
from .status import TaskStatus
from .storage import SupabaseTaskStore, TaskStore
from .workers import StageWorker


@dataclass
class Engine:
    dispatcher: Dispatcher
    workers: tuple[StageWorker, ...]

    def start(self) -> "Engine":
        for w in self.workers:
            w.start()
        return self

    def stop(self) -> None:
        for w in self.workers:
            w.stop()

    def health(self) -> dict[str, bool]:
        return {w.name: w.alive for w in self.workers}


def build_engine(settings: Settings, *, store: TaskStore | None = None, enricher: Enricher | None = None,
                 chat: ChatClient | None = None, examples: ExampleBank | None = None,
                 rng: random.Random | None = None) -> Engine:
    if store is None:
        settings.require("supabase_url", "supabase_key")
        store = SupabaseTaskStore(settings.supabase_url, settings.supabase_key,
                                  settings.storage_bucket, settings.tasks_table)
    if enricher is None:
        settings.require("proxycurl_key")
        enricher = ProxycurlEnricher(settings.proxycurl_key)
    if chat is None:
        settings.require("openai_api_key")
        chat = OpenAIChatClient(settings.openai_api_key, settings.openai_model,
                                temperature=settings.openai_temperature,
                                timeout=settings.request_timeout, max_retries=settings.max_retries)
    examples = examples or ExampleBank.default()

    collector = StageWorker("collector", CollectorStage(store, enricher, settings.work_dir))
    personalizer = StageWorker("personalizer", PersonalizerStage(
        store, chat, examples, settings.work_dir, max_workers=settings.max_concurrency,
        examples_per_prompt=settings.examples_per_prompt, rng=rng))
    dispatcher = Dispatcher({TaskStatus.INIT: collector, TaskStatus.PERSONALIZING: personalizer})
    return Engine(dispatcher, (collector, personalizer))
