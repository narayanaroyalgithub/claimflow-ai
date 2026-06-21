"""Top-k similarity search over the pgvector-backed knowledge store.

Pipeline: query -> embedding -> vector search -> top-k retrieval ->
returned as context for the Summary Agent's GPT-4o prompt.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeDocument
from app.vector_store.embeddings import Embedder, cosine_similarity


class Retriever:
    def __init__(self) -> None:
        self.embedder = Embedder()

    def search(self, db: Session, query: str, limit: int = 3) -> list[dict[str, str]]:
        documents = db.scalars(select(KnowledgeDocument)).all()
        if not documents:
            return []
        query_vector = self.embedder.embedding(query)
        scored = []
        for document in documents:
            vector = (
                json.loads(document.embedding_json)
                if document.embedding_json
                else self.embedder.embedding(document.content)
            )
            scored.append((cosine_similarity(query_vector, vector), document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "title": document.title,
                "source": document.source,
                "content": document.content,
                "score": f"{score:.4f}",
            }
            for score, document in scored[:limit]
        ]
