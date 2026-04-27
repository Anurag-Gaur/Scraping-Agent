"""
rag_store.py — FAISS-backed RAG store for research_bot
═══════════════════════════════════════════════════════
Persists all scraped competitor text as vector embeddings so that
every new research run can retrieve relevant knowledge from previous runs.

HOW IT WORKS
────────────
  upsert(requirement, findings)
    • Chunks each scraped page into ~800-char overlapping windows
    • Embeds every chunk with sentence-transformers (all-MiniLM-L6-v2)
    • Adds only NEW chunks to the FAISS flat-L2 index (MD5 dedup)
    • Saves index + metadata to Data/faiss_store/

  query(requirement, top_k)
    • Embeds the query string
    • Returns the top-k most similar past chunks as a formatted string
    • Ready to inject directly into the Groq prompt

  stats()
    • Returns dict with total_chunks, unique_requirements, platforms

DISK LAYOUT
───────────
  Data/faiss_store/
    index.faiss      ← FAISS flat-L2 index (384-dim, all-MiniLM-L6-v2)
    metadata.json    ← list of chunk dicts keyed by their FAISS row index

REQUIREMENTS
────────────
  pip install faiss-cpu sentence-transformers numpy
"""

import os
import json
import hashlib
import numpy as np

# ──────────────────────────── Config ──────────────────────────────── #
STORE_DIR     = "Data/faiss_store"
INDEX_PATH    = os.path.join(STORE_DIR, "index.faiss")
META_PATH     = os.path.join(STORE_DIR, "metadata.json")

EMBED_MODEL   = "all-MiniLM-L6-v2"   # 384-dim, ~90 MB, runs on CPU
EMBED_DIM     = 384

CHUNK_SIZE    = 800    # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks
TOP_K         = 6      # default number of chunks to retrieve
MIN_CHUNK_LEN = 80     # discard chunks shorter than this
# ──────────────────────────────────────────────────────────────────── #

# Module-level singletons (lazy-loaded)
_model = None
_index = None
_meta  = None          # list[dict], one entry per FAISS row


# ─────────────────────────── Internal helpers ─────────────────────── #

def _get_model():
    """Lazy-load SentenceTransformer (downloads once, cached locally)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
        print("[rag_store] Loading embedding model (first run downloads ~90 MB)...")
        _model = SentenceTransformer(EMBED_MODEL)
        print("[rag_store] Model ready.")
    return _model


def _load_index():
    """Load FAISS index + metadata from disk, or create empty ones."""
    global _index, _meta
    if _index is not None:
        return _index, _meta           # already loaded this session

    try:
        import faiss
    except ImportError:
        raise ImportError(
            "faiss-cpu not installed. Run: pip install faiss-cpu"
        )

    os.makedirs(STORE_DIR, exist_ok=True)

    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        _index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "r", encoding="utf-8") as f:
            _meta = json.load(f)
        print(f"[rag_store] Loaded index: {_index.ntotal} chunks")
    else:
        _index = faiss.IndexFlatL2(EMBED_DIM)
        _meta  = []
        print("[rag_store] Created new empty index.")

    return _index, _meta


def _save_index():
    """Persist current index + metadata to disk."""
    import faiss
    faiss.write_index(_index, INDEX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(_meta, f, ensure_ascii=False, indent=2)


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping windows, discarding very short chunks."""
    chunks = []
    start  = 0
    text   = text.strip()
    while start < len(text):
        end   = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK_LEN:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


# ──────────────────────────── Public API ──────────────────────────── #

def upsert(requirement: str, findings: dict) -> int:
    """
    Embed and index all scraped competitor findings for a requirement.

    Parameters
    ----------
    requirement : str
        The client requirement string (e.g. "accounts payable agent").
    findings : dict
        {platform_label: scraped_text_str} — output of research_requirement().

    Returns
    -------
    int  Number of new chunks added to the index.
    """
    index, meta = _load_index()
    model       = _get_model()

    existing_hashes = {m["hash"] for m in meta}

    new_texts = []
    new_metas = []

    for platform, text in findings.items():
        if not text or not isinstance(text, str):
            continue
        for chunk in _chunk_text(text):
            h = _md5(chunk)
            if h in existing_hashes:
                continue                          # already indexed
            new_texts.append(chunk)
            new_metas.append({
                "hash":        h,
                "requirement": requirement,
                "platform":    platform,
                "text":        chunk,
            })

    if not new_texts:
        print("[rag_store] No new chunks to index (all already present).")
        return 0

    print(f"[rag_store] Embedding {len(new_texts)} new chunks...")
    embeddings = model.encode(
        new_texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")

    index.add(embeddings)
    meta.extend(new_metas)
    _save_index()

    print(f"[rag_store] ✓ Indexed {len(new_texts)} chunks. "
          f"Total in store: {index.ntotal}")
    return len(new_texts)


def query(requirement: str, top_k: int = TOP_K) -> str:
    """
    Retrieve the most relevant past research chunks for a requirement.

    Parameters
    ----------
    requirement : str  The client requirement to search for.
    top_k       : int  How many chunks to return.

    Returns
    -------
    str
        Formatted context block ready to inject into an LLM prompt.
        Returns empty string if the index is empty.
    """
    index, meta = _load_index()

    if index.ntotal == 0:
        print("[rag_store] Index is empty — no past context to retrieve.")
        return ""

    model = _get_model()
    q_vec = model.encode(
        [requirement],
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")

    k = min(top_k, index.ntotal)
    distances, indices = index.search(q_vec, k)

    results = []
    seen_hashes = set()

    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        if m["hash"] in seen_hashes:
            continue                              # deduplicate
        seen_hashes.add(m["hash"])
        results.append((dist, m))

    if not results:
        return ""

    print(f"[rag_store] Retrieved {len(results)} relevant past chunks "
          f"(top L2 dist: {results[0][0]:.3f})")

    lines = [
        "=== RELEVANT PAST RESEARCH (retrieved from FAISS knowledge store) ===",
        f"(Showing {len(results)} most similar chunks for: '{requirement}')\n",
    ]
    for dist, m in results:
        lines.append(
            f"[{m['platform'].upper()} — past req: '{m['requirement']}' "
            f"| similarity score: {1/(1+dist):.2f}]\n{m['text']}"
        )
        lines.append("")                          # blank separator

    return "\n".join(lines)


def stats() -> dict:
    """Return summary statistics about the current FAISS store."""
    index, meta = _load_index()
    reqs      = {m["requirement"] for m in meta}
    platforms = {m["platform"]    for m in meta}
    return {
        "total_chunks":        index.ntotal,
        "unique_requirements": len(reqs),
        "requirements":        sorted(reqs),
        "platforms":           sorted(platforms),
        "store_dir":           os.path.abspath(STORE_DIR),
    }


# ─────────────────────── CLI convenience mode ─────────────────────── #

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        s = stats()
        print(json.dumps(s, indent=2))
    elif sys.argv[1] == "query" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        print(query(q))
    elif sys.argv[1] == "stats":
        print(json.dumps(stats(), indent=2))
    else:
        print("Usage:")
        print("  python rag_store.py                    # show stats")
        print("  python rag_store.py stats              # show stats")
        print('  python rag_store.py query "your req"   # retrieve chunks')
