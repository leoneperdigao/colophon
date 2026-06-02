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

    @property
    def ingest(self) -> IngestDocument:
        return IngestDocument(blob=self.blob, store=self.store, messaging=self.messaging)

    @property
    def process(self) -> ProcessPipeline:
        return ProcessPipeline(blob=self.blob, store=self.store, parser=self.parser, llm=self.llm)

    @property
    def get_annotation(self) -> GetAnnotation:
        return GetAnnotation(store=self.store)
