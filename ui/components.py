import streamlit as st
from typing import Dict, Optional
from utils.source_tracking import format_rating_name

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


def render_source_context(source_stats: Optional[Dict]):
    """
    Display source credibility context with PolitiFact track record.
    
    Args:
        source_stats: Dictionary with source statistics from get_source_statistics()
    """
    if not source_stats:
        return
    
    source = source_stats['source']
    total = source_stats['total_checks']
    false_pct = source_stats['false_percentage']
    true_pct = source_stats['true_percentage']
    mixed_pct = source_stats['mixed_percentage']
    indicator = source_stats['indicator']
    
    # Main header
    st.markdown(f"### 🔍 Source Detected: **{source}**")
    
    # Create a visually appealing info box
    st.info(f"""
**📊 PolitiFact Track Record**

✓ Fact-checked **{total}** time{"s" if total != 1 else ""} since 2007

{indicator}
- 🔴 False/Misleading: **{false_pct:.1f}%**
- 🟢 True/Mostly True: **{true_pct:.1f}%**
- 🟡 Mixed/Half True: **{mixed_pct:.1f}%**
    """)
    
    # Detailed breakdown in expander
    with st.expander("📋 View detailed rating breakdown"):
        ratings = source_stats['rating_breakdown']
        
        # Sort ratings by count (most common first)
        sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        
        for rating, count in sorted_ratings:
            pct = (count / total) * 100
            formatted_rating = format_rating_name(rating)
            
            # Create progress bar for visual representation
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{formatted_rating}**")
                st.progress(pct / 100)
            with col2:
                st.markdown(f"{count} ({pct:.1f}%)")
