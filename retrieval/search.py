import numpy as np
import pandas as pd
from typing import Dict, Any
from config import FLAGS
from services.clients import get_openai


def embed_text(text: str) -> list[float]:
    client = get_openai()
    resp = client.embeddings.create(input=[text], model=FLAGS.OPENAI_EMBED_MODEL)
    return resp.data[0].embedding


def _cosine_from_ip(raw_ip: float) -> float:
    # If your index is IP over normalized vectors, inner product == cosine in [-1,1]. Map to [0,1]
    return (raw_ip + 1.0) / 2.0


def _sim_from_l2(distance: float) -> float:
    # Convert L2 distance to a [0,1] similarity heuristic
    return 1.0 / (1.0 + max(distance, 0.0))


def search_politifact_db(query: str, index, metadata: pd.DataFrame) -> Dict[str, Any]:
    q = np.array([embed_text(query)], dtype="float32")
    # If you normalized vectors at build time for IP, do so for the query as well
    try:
        q /= (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
    except Exception:
        pass

    D, I = index.search(q, k=FLAGS.TOP_K)
    rows = metadata.iloc[I[0]].copy()

    # Decide similarity mapping based on index type name
    idx_name = type(index).__name__
    use_ip = "IP" in idx_name or "Inner" in idx_name

    results = []
    for pos, (_, row) in enumerate(rows.iterrows()):
        raw = float(D[0][pos])
        sim = _cosine_from_ip(raw) if use_ip else _sim_from_l2(raw)
        explanation = (row.get("explanation") or "")
        if len(explanation) > 500:
            explanation = explanation[:500] + "..."
        results.append({
            "source": "PolitiFact",
            "publisher": "PolitiFact",
            "claim": row.get("claim", ""),
            "rating": row.get("verdict", ""),
            "explanation": explanation,
            "url": row.get("url", ""),
            "similarity_score": sim,
        })

    # De-dup by URL (mirrors, repeats)
    dedup = []
    seen = set()
    
    # ---------------------------------------------------------
    # HYBRID SEARCH: Keyword Boost
    # ---------------------------------------------------------
    # If the user mentions specific entities (capitalized words), ensure we scan for them
    # and inject them into the results if missed by vector search.
    import re
    # Extract potential proper nouns (simple heuristic: capitalized words > 3 chars, ignore common starters)
    ignore = {"What", "When", "Where", "Which", "This", "That", "There", "Here", "Does", "Is", "Are", "Can", "Could", "Should", "Would"}
    tokens = [w.strip("?,.!\"'") for w in query.split()]
    keywords = [w for w in tokens if w and w[0].isupper() and len(w) > 3 and w not in ignore]
    
    if keywords:
        # Search for rows containing ALL keywords (AND logic) to be specific
        # We search primarily in the claim and tags/people if available, or just claim/explanation
        # Construct a mask
        try:
            # We use the existing metadata (pandas df)
            # Create a combined text column for searching on the fly (fast enough for <50k rows)
            search_col = (metadata["claim"].fillna("") + " " + metadata.get("explanation", "").fillna("")).str.lower()
            
            mask = np.ones(len(metadata), dtype=bool)
            for k in keywords:
                mask &= search_col.str.contains(k.lower(), regex=False)
            
            # Get matches
            boost_rows = metadata[mask]
            
            # Add up to 10 keyword matches to the TOP of the results
            # We give them a fake high similarity score to ensure they are seen
            for _, row in boost_rows.head(10).iterrows():
                # Format like a result
                explanation = (row.get("explanation") or "")
                if len(explanation) > 500:
                    explanation = explanation[:500] + "..."
                    
                entry = {
                    "source": "PolitiFact (Keyword Match)",
                    "publisher": "PolitiFact",
                    "claim": row.get("claim", ""),
                    "rating": row.get("verdict", ""),
                    "explanation": explanation,
                    "url": row.get("url", ""),
                    "similarity_score": 0.99, # Fake high score
                }
                # Insert at start
                results.insert(0, entry)
        except Exception:
            # Fallback if pandas ops fail (shouldn't happen but be safe)
            pass

    # ---------------------------------------------------------

    for r in results:
        u = r.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        dedup.append(r)

    return {"source_name": "PolitiFact Database", "results": dedup}