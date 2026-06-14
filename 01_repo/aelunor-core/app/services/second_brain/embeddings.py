"""Embedding ports for the Second Brain (semantic-recall pillar).

The store and recall logic depend only on the small ``EmbeddingPort``
protocol, so the embedder is fully swappable:

- ``DeterministicHashEmbedding`` — offline, stdlib-only, process-stable
  feature hashing. No network, no model download. Cosine similarity tracks
  shared-token overlap, which is enough to exercise and test the semantic
  path deterministically.
- ``OllamaEmbedding`` — thin optional adapter around a local embedding
  model (e.g. ``nomic-embed-text``). Constructed only when explicitly wired
  at runtime; never imported or called in tests.

Determinism note: we hash with ``hashlib`` (not the builtin ``hash()``,
which is salted per process via PYTHONHASHSEED) so vectors are stable across
runs and machines.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingPort(Protocol):
    """Maps texts to dense unit vectors of a fixed dimension."""

    dim: int

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        ...


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity. Inputs need not be normalized; safe on zeros."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class DeterministicHashEmbedding:
    """Offline feature-hashing embedder. No I/O, fully deterministic.

    Each token is hashed into a bucket with a signed contribution, then the
    vector is L2-normalized. Texts that share tokens land close in cosine
    space, which lets the semantic recall path be tested without a model.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = max(8, int(dim))

    def _hash_token(self, token: str) -> tuple[int, float]:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % self.dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        return bucket, sign

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in _tokenize(text):
                bucket, sign = self._hash_token(token)
                vec[bucket] += sign
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0.0:
                vec = [v / norm for v in vec]
            vectors.append(tuple(vec))
        return vectors


class OllamaEmbedding:
    """Thin local-Ollama embedding adapter (runtime only, optional).

    Kept dependency-light: the HTTP client is injected so this module never
    hard-imports a network library and stays offline-importable. Wire a real
    client at runtime; tests use ``DeterministicHashEmbedding`` instead.
    """

    def __init__(self, *, post_json, model: str = "nomic-embed-text", dim: int = 768) -> None:
        self._post_json = post_json
        self.model = model
        self.dim = int(dim)

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            payload = self._post_json("/api/embeddings", {"model": self.model, "prompt": text})
            raw = (payload or {}).get("embedding") or []
            vectors.append(tuple(float(x) for x in raw))
        return vectors
