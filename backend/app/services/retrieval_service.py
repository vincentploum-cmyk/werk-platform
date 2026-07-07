"""Semantic retrieval over the shared document folder.

Given a task, returns the most relevant chunks of the team's documents — ranked by
embeddings when an embedding model is available (Ollama / OpenAI), else by a deterministic
TF-IDF cosine. This replaces dumping a truncated digest of every document into the prompt.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import httpx

from app.core.config import settings
from app.services import workspace_service

_CHUNK = 700  # chars per chunk


def _chunk(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    paras = re.split(r"\n\s*\n", text)
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= _CHUNK:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
            # hard-split very long paragraphs
            while len(p) > _CHUNK:
                chunks.append(p[:_CHUNK])
                p = p[_CHUNK:]
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


# ── TF-IDF fallback (pure python, deterministic) ────────────────────────────
def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _tfidf_rank(query: str, chunks: list[str]) -> list[int]:
    qt = _tokens(query)
    doc_toks = [_tokens(c) for c in chunks]
    if not chunks or not qt:
        return list(range(len(chunks)))
    n = len(chunks)
    df = Counter()
    for toks in doc_toks:
        for t in set(toks):
            df[t] += 1

    def vec(toks):
        tf = Counter(toks)
        return {t: (c / len(toks)) * (math.log((n + 1) / (df.get(t, 0) + 1)) + 1) for t, c in tf.items()}

    qv = vec(qt)
    qn = math.sqrt(sum(x * x for x in qv.values())) or 1.0
    scores = []
    for toks in doc_toks:
        dv = vec(toks)
        dn = math.sqrt(sum(x * x for x in dv.values())) or 1.0
        num = sum(qv[t] * dv.get(t, 0.0) for t in qv)
        scores.append(num / (qn * dn))
    return sorted(range(len(chunks)), key=lambda i: -scores[i])


# ── embeddings (optional) ───────────────────────────────────────────────────
async def _embed(texts: list[str]) -> list[list[float]] | None:
    """Embed texts with Ollama or OpenAI if configured; else None."""
    try:
        if settings.use_ollama:
            url = settings.ollama_base_url.rstrip("/") + "/api/embeddings"
            out = []
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=60.0)) as client:
                for t in texts:
                    r = await client.post(url, json={"model": settings.ollama_embed_model, "prompt": t})
                    r.raise_for_status()
                    emb = r.json().get("embedding")
                    if not emb:
                        return None
                    out.append(emb)
            return out
        if settings.openai_api_key:
            import openai

            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.embeddings.create(model="text-embedding-3-small", input=texts)
            return [d.embedding for d in resp.data]
    except Exception:
        return None
    return None


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return num / (na * nb)


async def _embed_rank(query: str, chunks: list[str]) -> list[int] | None:
    vecs = await _embed([query] + chunks)
    if not vecs or len(vecs) != len(chunks) + 1:
        return None
    qv, dvs = vecs[0], vecs[1:]
    scores = [_cosine(qv, d) for d in dvs]
    return sorted(range(len(chunks)), key=lambda i: -scores[i])


# ── public ──────────────────────────────────────────────────────────────────
async def retrieve_context(project_id, query: str, k: int = 4, budget: int = 4000) -> str:
    """Return the most relevant document chunks for `query`, within a char budget."""
    docs = workspace_service.list_documents(project_id)
    chunks: list[tuple[str, str]] = []
    for d in docs:
        for ch in _chunk(d["content"]):
            chunks.append((d["name"], ch))
    if not chunks:
        return ""

    order = await _embed_rank(query, [c[1] for c in chunks])
    if order is None:
        order = _tfidf_rank(query, [c[1] for c in chunks])

    out, used = [], 0
    for i in order:
        name, text = chunks[i]
        block = f"### {name}\n{text}"
        if used + len(block) > budget and out:
            break
        out.append(block)
        used += len(block)
        if len(out) >= k:
            break
    return "\n\n".join(out)
