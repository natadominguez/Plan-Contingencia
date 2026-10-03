"""RAG sobre el corpus legal argentino.

MVP: embeddings de OpenAI + indice vectorial en memoria persistido a JSON.
El corpus vive en backend/corpus/argentina/ con un manifest.json que registra
la version de cada ley (el agente monitor lo usa para detectar cambios).
"""
import json
import hashlib
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

from app.config import settings

CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus" / "argentina"
INDEX_PATH = Path(__file__).resolve().parents[2] / "corpus" / "index.json"

_client: AsyncOpenAI | None = None
_index: list[dict] = []


def _client_or_none() -> AsyncOpenAI | None:
    global _client
    if _client is None and settings.openai_api_key:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def load_manifest() -> dict:
    manifest_path = CORPUS_DIR / "manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _iter_chunks() -> list[dict]:
    manifest = load_manifest()
    chunks = []
    for law in manifest["laws"]:
        path = CORPUS_DIR / law["file"]
        if not path.exists():
            continue
        for i, block in enumerate(path.read_text(encoding="utf-8").split("\n\n")):
            block = block.strip()
            if not block:
                continue
            chunks.append(
                {
                    "law_id": law["id"],
                    "law_title": law["title"],
                    "version": law["version"],
                    "tags": law.get("tags", []),
                    "chunk_id": f"{law['id']}#{i}",
                    "text": block,
                }
            )
    return chunks


async def build_index() -> int:
    """Genera embeddings de todo el corpus y persiste el indice."""
    global _index
    client = _client_or_none()
    chunks = _iter_chunks()

    if client is None:
        # Fallback sin API key: indice de texto plano (busqueda por tags).
        _index = [{**c, "embedding": None} for c in chunks]
    else:
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=[c["text"] for c in chunks],
        )
        _index = [
            {**c, "embedding": d.embedding} for c, d in zip(chunks, resp.data)
        ]

    INDEX_PATH.write_text(
        json.dumps(_index, ensure_ascii=False), encoding="utf-8"
    )
    return len(_index)


def load_index() -> list[dict]:
    global _index
    if not _index and INDEX_PATH.exists():
        _index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return _index


async def retrieve(query: str, tags: list[str] | None = None, k: int = 6) -> list[dict]:
    index = load_index()
    if not index:
        return []

    if tags:
        tagged = [c for c in index if set(tags) & set(c["tags"])]
    else:
        tagged = index

    client = _client_or_none()
    if client is None or not all(c["embedding"] for c in tagged):
        return tagged[:k]

    resp = await client.embeddings.create(model=settings.embedding_model, input=[query])
    q = np.array(resp.data[0].embedding)

    scored = []
    for c in tagged:
        v = np.array(c["embedding"])
        score = float(q @ v / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
        scored.append((score, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _, c in scored[:k]]


def corpus_fingerprint() -> str:
    """Hash del manifest: cambia si se versiona alguna ley."""
    return hashlib.sha256(
        json.dumps(load_manifest(), sort_keys=True).encode()
    ).hexdigest()
