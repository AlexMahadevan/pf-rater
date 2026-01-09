from typing import Any, Dict, List, Tuple, Iterable
import re
import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

from services.claim_extraction import extract_key_terms_and_claims
from retrieval.search import search_politifact_db
from utils.ratings import standardize_rating


# ----------------------------- Dynamic relevance ------------------------------

def _normalize_terms(terms: Iterable[str]) -> List[str]:
    """Lowercase, strip, and keep meaningful tokens (len>=3)."""
    out = []
    for t in terms or []:
        if not t:
            continue
        # split compound terms into words too (e.g., "For the People Act")
        parts = re.split(r"[\s/,\-\(\)\[\]:;]+", str(t).lower().strip())
        for p in parts:
            p = p.strip()
            if len(p) >= 3 and p not in out:
                out.append(p)
    return out


def _fallback_terms_from_query(query: str) -> List[str]:
    """Backup keyword list from the raw query in case extraction returns little."""
    parts = re.split(r"[\s/,\-\(\)\[\]:;]+", (query or "").lower())
    # keep words that look like entities/policies/keywords, drop common determiners
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "onto",
            "are", "was", "were", "been", "their", "they", "them", "her", "his",
            "you", "your", "about", "over", "under", "onto", "into", "via", "out",
            "not", "have", "has", "had", "but", "who", "what", "when", "where",
            "why", "how", "will", "would", "could", "should", "may", "might",
            "more", "less", "very", "also", "than", "then"}
    terms = [w for w in parts if len(w) >= 3 and w not in stop]
    # de-dup in-order
    seen, uniq = set(), []
    for w in terms:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq[:20]


def _build_dynamic_terms(query: str) -> List[str]:
    """Combine LLM-extracted claim/term tokens + fallback tokens from the query."""
    claims, terms = extract_key_terms_and_claims(query)
    extracted = _normalize_terms((terms or []) + (claims or []))
    fallback = _fallback_terms_from_query(query)
    # prioritize extracted terms but include fallback for coverage
    combined = extracted + [t for t in fallback if t not in extracted]
    # keep it modest to avoid over-filtering
    return combined[:30]


def _looks_relevant_dynamic(result: Dict[str, Any], dyn_terms: List[str]) -> bool:
    """
    Keep a Google result if any dynamic term appears in the claim text, publisher, or URL.
    If no dyn_terms are provided (edge case), don't filter (return True).
    """
    if not dyn_terms:
        return True
    hay = " ".join([
        (result.get("claim") or "").lower(),
        (result.get("publisher") or "").lower(),
        (result.get("url") or "").lower()
    ])
    return any(t in hay for t in dyn_terms)


# --------------------------- Google Fact Check API ----------------------------

def _search_google_factcheck_raw(query: str, api_key: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Thin wrapper around Google's Fact Check Tools API."""
    if not api_key:
        return []
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {"query": query, "key": api_key, "pageSize": max_results}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            st.warning(f"Google Fact Check API status {r.status_code}")
            return []
        data = r.json()
        claims = data.get("claims", []) or []
        out: List[Dict[str, Any]] = []
        for claim in claims:
            claim_txt = claim.get("text", "") or ""
            lang = claim.get("languageCode") or "en"
            for review in claim.get("claimReview", []) or []:
                out.append({
                    "source": "Multi-Source",
                    "publisher": (review.get("publisher", {}) or {}).get("name", "Unknown"),
                    "claim": claim_txt,
                    "rating": review.get("textualRating", "No rating"),
                    "url": review.get("url", ""),
                    "review_date": review.get("reviewDate", ""),
                    "language": lang,
                })
        return out[:max_results]
    except Exception as e:
        st.warning(f"Google Fact Check API error: {e}")
        return []


def enhanced_google_factcheck_search(query: str, api_key: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Strategy:
    - Build dynamic relevance terms from the query (LLM-extracted + fallback tokens).
    - Run claim/term searches + raw query.
    - De-dup by URL.
    - Keep only results that match at least one dynamic term.
    """
    if not api_key:
        return []

    dyn_terms = _build_dynamic_terms(query)

    all_results: List[Dict[str, Any]] = []

    # Claim/term extraction helps even for long inputs
    claims, terms = extract_key_terms_and_claims(query)
    for c in (claims or [])[:3]:
        all_results.extend(_search_google_factcheck_raw(c, api_key, max_results=3))
    for t in (terms or [])[:3]:
        all_results.extend(_search_google_factcheck_raw(t, api_key, max_results=2))

    # Raw query as well
    all_results.extend(_search_google_factcheck_raw(query, api_key, max_results))

    # De-dup by URL and apply dynamic relevance
    seen = set()
    filtered: List[Dict[str, Any]] = []
    for r in all_results:
        u = r.get("url")
        if not u or u in seen:
            continue
        if _looks_relevant_dynamic(r, dyn_terms):
            seen.add(u)
            filtered.append(r)

    return filtered[:max_results]


# ------------------------------ Consensus math -------------------------------

def analyze_consensus(sources_data: List[Dict[str, Any]], outlier_delta: float = 1.5) -> Dict[str, Any]:
    if not sources_data:
        return {"consensus_level": 0, "average_rating": None, "agreement": "No data", "outliers": [], "source_count": 0}

    ratings: List[int] = []
    source_ratings: Dict[str, int] = {}

    for source_data in sources_data:
        for res in source_data.get("results", []) or []:
            score = standardize_rating(res.get("rating"))
            if score is not None:
                ratings.append(score)
                name = res.get("publisher") or res.get("source") or "Unknown"
                source_ratings[name] = score

    if not ratings:
        return {"consensus_level": 0, "average_rating": None, "agreement": "No standardizable ratings", "outliers": [], "source_count": len(sources_data)}

    import numpy as np
    arr = np.array(ratings, dtype=float)
    avg = float(arr.mean())
    std = float(arr.std()) if len(arr) > 1 else 0.0

    consensus_level = max(0.0, 1.0 - (std / 2.5))

    outliers = []
    for src, r in source_ratings.items():
        if abs(r - avg) > outlier_delta:
            outliers.append(f"{src} ({r})")

    if consensus_level > 0.8:
        agreement = "Strong consensus"
    elif consensus_level > 0.6:
        agreement = "Moderate agreement"
    elif consensus_level > 0.4:
        agreement = "Some disagreement"
    else:
        agreement = "Significant disagreement"

    return {
        "consensus_level": consensus_level,
        "average_rating": avg,
        "agreement": agreement,
        "outliers": outliers,
        "source_count": len(set(source_ratings.keys())),
        "source_ratings": source_ratings,
    }


# -------------------------------- Public API ---------------------------------

def _split_google_by_publisher(results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    pf, other = [], []
    for r in results:
        pub = (r.get("publisher") or "").strip().lower()
        if pub == "politifact":
            pf.append(r)
        else:
            other.append(r)
    return pf, other


def get_multi_source_analysis(query: str, index, metadata, google_api_key: str) -> tuple[list[dict], dict]:
    """
    Returns:
      - sources_data: [
            {"source_name": "PolitiFact Database", "results": [...]},
            {"source_name": "Recent PolitiFact (via Google)", "results": [...]},  # if any
            {"source_name": "External Sources (via Google)", "results": [...]},   # if any
        ]
      - consensus: {...}
    """
    sources: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        # 1) Kick off PolitiFact DB search and Google search in parallel
        pf_future = executor.submit(search_politifact_db, query, index, metadata)
        google_future = executor.submit(enhanced_google_factcheck_search, query, google_api_key)

        # 2) Gather results
        pf_data = pf_future.result()
        g_results = google_future.result()

    sources.append(pf_data)

    if g_results:
        pf_external, non_pf = _split_google_by_publisher(g_results)
        if pf_external:
            sources.append({"source_name": "Recent PolitiFact (via Google)", "results": pf_external})
        if non_pf:
            sources.append({"source_name": "External Sources (via Google)", "results": non_pf})

    # 3) Consensus across all sources
    consensus = analyze_consensus(sources)

    return sources, consensus
