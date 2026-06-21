"""Embedding generation for the knowledge retrieval pipeline.

Uses OpenAI's ``text-embedding-3-small`` model when an API key is
configured, and falls back to a deterministic local hashing scheme
otherwise (e.g. in tests or offline development) so retrieval keeps
working without external calls.
"""

import hashlib
import math

from openai import OpenAI

from app.config import settings


class Embedder:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def embedding(self, text: str) -> list[float]:
        if self.client:
            response = self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text,
            )
            return response.data[0].embedding
        return self._local_embedding(text)

    @staticmethod
    def _local_embedding(text: str, dimensions: int = 256) -> list[float]:
        vector = [0.0] * dimensions
        for token in text.casefold().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    numerator = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
