"""Embedding providers behind one switch: EMBED_PROVIDER = local | openai | voyage | ollama.

Default is `local` (fastembed, ONNX on CPU): no API key, no network after the
first model download, multilingual. Remote providers stay available for those
who want them — but nothing in the memory system requires a key.
"""
import hashlib
import math
import threading
import warnings

import httpx

import harness_env as env

PROVIDER = env.get("EMBED_PROVIDER", "local").lower()
DIM = int(env.get("EMBED_DIM", "1024"))

_DEFAULT_MODELS = {
    "local": "intfloat/multilingual-e5-large",
    "openai": "text-embedding-3-small",
    "voyage": "voyage-3.5",
    "ollama": "nomic-embed-text",
}
MODEL = env.get("EMBED_MODEL") or _DEFAULT_MODELS.get(PROVIDER, "")

# e5 models are trained with asymmetric prefixes; using them lifts retrieval quality.
_E5 = "e5" in MODEL.lower()

_local_model = None
_local_lock = threading.Lock()


def _local(text: str, kind: str) -> list[float]:
    global _local_model
    from fastembed import TextEmbedding

    if _local_model is None:
        with _local_lock:
            if _local_model is None:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    _local_model = TextEmbedding(MODEL)
    if _E5:
        text = f"{'query' if kind == 'query' else 'passage'}: {text}"
    return list(_local_model.embed([text]))[0].tolist()


def _openai(text: str, kind: str) -> list[float]:
    key = env.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (harness.env)")
    r = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": MODEL, "input": text, "dimensions": DIM},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def _voyage(text: str, kind: str) -> list[float]:
    key = env.get("VOYAGE_API_KEY")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY is not set (harness.env)")
    r = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MODEL,
            "input": [text],
            "input_type": "query" if kind == "query" else "document",
            "output_dimension": DIM,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def _ollama(text: str, kind: str) -> list[float]:
    base = env.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    r = httpx.post(f"{base}/api/embeddings", json={"model": MODEL, "prompt": text}, timeout=60)
    r.raise_for_status()
    return r.json()["embedding"]


def _dummy(text: str, kind: str) -> list[float]:
    # Deterministic pseudo-embedding for offline tests. Never use in production.
    vec = []
    for i in range(DIM):
        h = hashlib.sha256(text.encode() + i.to_bytes(4, "big")).digest()
        vec.append(int.from_bytes(h[:4], "big") / 2**32 - 0.5)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


_PROVIDERS = {
    "local": _local,
    "openai": _openai,
    "voyage": _voyage,
    "ollama": _ollama,
    "dummy": _dummy,
}


def embed(text: str, kind: str = "passage") -> list[float]:
    """kind: 'passage' for stored memories, 'query' for searches."""
    fn = _PROVIDERS.get(PROVIDER)
    if fn is None:
        raise RuntimeError(f"Unknown EMBED_PROVIDER: {PROVIDER}")
    vec = fn(text, kind)
    if len(vec) != DIM:
        raise RuntimeError(
            f"Provider returned dim {len(vec)}, but EMBED_DIM={DIM}. "
            f"Fix EMBED_DIM in harness.env (existing memories must be re-embedded on change)."
        )
    return vec
