import streamlit as st

def consensus_badge(consensus: dict):
    level = consensus.get("agreement", "Unknown")
    count = consensus.get("source_count", 0)
    if level == "Strong consensus":
        st.success(f"✅ Strong Agreement across {count} sources")
    elif level == "Moderate agreement":
        st.info(f"⚖️ Moderate Agreement across {count} sources")
    elif level == "Some disagreement":
        st.warning(f"🤔 Mixed Findings across {count} sources")
    else:
        st.error(f"⚠️ Conflicting Information across {count} sources")


def render_sources_block(sources_data: list[dict]):
    st.markdown("### Retrieved fact-checks by source")
    for src in sources_data:
        name = src.get("source_name", "Unknown Source")
        results = src.get("results", []) or []
        if not results:
            continue
        with st.expander(f"{name} ({len(results)} results)"):
            for i, r in enumerate(results):
                claim = r.get("claim", "No claim text")
                rating = r.get("rating", "No rating")
                publisher = r.get("publisher", "Unknown")
                url = r.get("url", "")
                st.markdown(f"**{i+1}. {claim[:100]}{'...' if len(claim)>100 else ''}**")
                st.markdown(f"*Publisher:* {publisher} | *Rating:* {rating}")
                if url:
                    st.markdown(f"[📖 Read full fact-check]({url})")
                if "similarity_score" in r:
                    st.caption(f"Similarity: {r['similarity_score']:.3f}")
                if i < len(results) - 1:
                    st.markdown("---")
