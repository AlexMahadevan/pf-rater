from typing import List, Dict

def _summarize_pf_anchor(pf_results: List[Dict]) -> str:
    """
    Build a short 'anchor' blurb from the top PolitiFact hit (if present).
    We rely on the retrieval layer to put PF results in sources_data[0].
    """
    if not pf_results:
        return ""
    top = pf_results[0]
    claim = top.get("claim", "").strip()
    rating = top.get("rating", "").strip()
    url = top.get("url", "").strip()
    sim = top.get("similarity_score", None)
    anchor = f"- Nearest PolitiFact precedent: **{rating or 'N/A'}** — {claim}"
    if url:
        anchor += f" ([link]({url}))"
    if isinstance(sim, (int, float)):
        anchor += f" (similarity ≈ {sim:.2f})"
    return anchor

def build_enhanced_prompt(query: str, sources_data: list[dict], consensus: dict, use_web: bool) -> str:
    """
    Build a prompt that asks the model to return structured, human-readable markdown
    and to ALIGN with PolitiFact precedent unless there is strong, well-cited reason to deviate.
    """
    # Assemble compact context blocks
    ctx_parts = []
    pf_results = []
    for src in sources_data:
        name = src.get("source_name", "Unknown Source")
        results = src.get("results", []) or []
        if not results:
            continue
        if "PolitiFact Database" in name:
            pf_results = results
        ctx_parts.append(f"\n--- {name} ---")
        for r in results[:3]:
            claim = r.get("claim", "No claim")
            rating = r.get("rating", "No rating")
            publisher = r.get("publisher", name)
            url = r.get("url", "")
            expl = r.get("explanation", "")
            chunk = f"Claim: {claim}\nPublisher: {publisher}\nRating: {rating}"
            if expl:
                chunk += f"\nExplanation: {expl}"
            if url:
                chunk += f"\nURL: {url}"
            ctx_parts.append(chunk)

    combined_context = "\n\n".join(ctx_parts)

    search_note = "Web search is enabled for recency.\n" if use_web else ""

    consensus_text = (
        f"\nCROSS-SOURCE CONSENSUS:\n- Agreement: {consensus.get('agreement','N/A')}\n"
        f"- Sources Considered: {consensus.get('source_count','N/A')}\n"
        f"- Average Rating (0-5): {consensus.get('average_rating','N/A')}\n"
    )
    if consensus.get("outliers"):
        consensus_text += f"- Outliers: {', '.join(consensus['outliers'])}\n"

    # PF anchor guidance
    pf_anchor = _summarize_pf_anchor(pf_results)
    pf_rule = """
Anchoring rule:
- If there is a close PolitiFact precedent among the retrieved results (high similarity or near-match),
  ALIGN your suggested rating with that PolitiFact rating **unless** multiple up-to-date, non-PolitiFact
  sources directly contradict it with strong evidence. If you deviate, explicitly explain why.
"""

    return f"""
You are an experienced PolitiFact researcher. Produce **public-facing, well-formatted markdown** (no JSON).

{search_note}
Use the structure **exactly** below:

### Suggested Rating
[Choose: True, Mostly True, Half True, Mostly False, False, Pants on Fire]

### Confidence Level
State High / Medium / Low and justify in 1–2 sentences.

### Reasoning
2–4 short paragraphs, clear plain English. Cite facts and distinguish national vs state-level evidence.

### Multi-Source Analysis
- Summarize how PolitiFact and other reputable sources rated or analyzed similar claims.
- Prefer primary sources and major fact-checkers; include links when available.

### Jurisprudence
Numbered list of the most similar past PolitiFact fact-checks with claim, rating, and link.

### Evidence Gaps
Bullet list of follow-ups to strengthen the fact-check.

Calibration:
{pf_anchor if pf_anchor else "- No clear PolitiFact anchor found."}
{pf_rule}

---
Draft to assess:
{query}

---
Relevant fact-checks:
{combined_context}

{consensus_text}
"""
