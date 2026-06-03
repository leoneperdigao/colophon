"""Composition root — wires adapters to services by profile.

The HTTP app and the worker share these services; only the adapter wiring differs
per environment. The `in_memory` profile keeps the system runnable with no infra.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.adapters.llm.stub import StubLLM
from app.adapters.outbound.blob.memory import InMemoryBlobStore
from app.adapters.outbound.messaging.memory import InMemoryMessaging
from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.adapters.parsing.stub import StubParser
from app.application.ports.annotation_store import AnnotationStore
from app.config import settings
from app.application.ports.blob_store import BlobStore
from app.application.ports.document_parser import DocumentParser
from app.application.ports.llm_client import LLMClient
from app.application.ports.messaging import Messaging
from app.application.services.get_annotation import GetAnnotation
from app.application.services.ingest_document import IngestDocument
from app.application.services.process_pipeline import ProcessPipeline


@dataclass
class Container:
    token_map: dict[str, str]
    blob: BlobStore
    store: AnnotationStore
    messaging: Messaging
    parser: DocumentParser
    llm: LLMClient

    @classmethod
    def in_memory(cls, *, token_map: dict[str, str]) -> "Container":
        return cls(
            token_map=token_map,
            blob=InMemoryBlobStore(),
            store=InMemoryAnnotationStore(),
            messaging=InMemoryMessaging(),
            parser=StubParser(),
            llm=StubLLM(),
        )

    @classmethod
    def from_env(cls) -> "Container":
        """Build the container for the configured profile (APP_PROFILE).

        'memory' wires the in-memory fakes (no infra, no optional imports — the
        CI/skeleton path). 'local' wires the real adapters; their infra libraries
        are imported lazily by the builders below, so this module stays importable
        without the `infra`/`llm` extras.
        """
        token_map = settings.load_token_map()
        profile = settings.app_profile()
        if profile == "memory":
            return cls.in_memory(token_map=token_map)
        if profile == "local":
            return cls(
                token_map=token_map,
                blob=cls._build_blob(),
                store=cls._build_store(),
                messaging=cls._build_messaging(),
                parser=cls._build_parser(),
                llm=cls._build_llm(),
            )
        raise ValueError(f"unknown APP_PROFILE {profile!r} (expected 'memory' or 'local')")

    # --- local-profile builders (infra imports are confined here) ---------------

    @staticmethod
    def _build_blob() -> BlobStore:
        from app.adapters.outbound.blob.minio_blob import MinioBlobStore

        return MinioBlobStore(**settings.minio_config())  # type: ignore[arg-type]

    @staticmethod
    def _build_store() -> AnnotationStore:
        from app.adapters.outbound.store.postgres_store import PostgresAnnotationStore

        return PostgresAnnotationStore(dsn=settings.postgres_dsn())

    @staticmethod
    def _build_messaging() -> Messaging:
        from app.adapters.outbound.messaging.rabbitmq import RabbitMqMessaging

        return RabbitMqMessaging(url=settings.rabbitmq_url())

    @staticmethod
    def _build_parser() -> DocumentParser:
        from app.adapters.parsing.factory import build_document_parser

        return build_document_parser()

    @staticmethod
    def _build_llm() -> LLMClient:
        from app.adapters.llm.factory import build_annotator

        return build_annotator()

    @property
    def ingest(self) -> IngestDocument:
        return IngestDocument(blob=self.blob, store=self.store, messaging=self.messaging)

    @property
    def process(self) -> ProcessPipeline:
        return ProcessPipeline(blob=self.blob, store=self.store, parser=self.parser, llm=self.llm)

    @property
    def get_annotation(self) -> GetAnnotation:
        return GetAnnotation(store=self.store)
