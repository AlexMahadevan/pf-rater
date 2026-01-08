import streamlit as st
from typing import Dict, Optional
from utils.source_tracking import format_rating_name

def consensus_badge(consensus: dict):
    """Display consensus level with custom styled badge."""
    level = consensus.get("agreement", "Unknown")
    count = consensus.get("source_count", 0)
    
    # Custom HTML badges with distinctive styling
    badge_styles = {
        "Strong consensus": {
            "title": "Strong Agreement",
            "color": "#06D6A0",
            "bg": "rgba(6, 214, 160, 0.15)",
            "border": "#06D6A0"
        },
        "Moderate agreement": {
            "title": "Moderate Agreement",
            "color": "#FFB627",
            "bg": "rgba(255, 182, 39, 0.15)",
            "border": "#FFB627"
        },
        "Some disagreement": {
            "title": "Mixed Findings",
            "color": "#FF8C42",
            "bg": "rgba(255, 140, 66, 0.15)",
            "border": "#FF8C42"
        },
        "Unknown": {
            "title": "Conflicting Information",
            "color": "#E63946",
            "bg": "rgba(230, 57, 70, 0.15)",
            "border": "#E63946"
        }
    }
    
    style = badge_styles.get(level, badge_styles["Unknown"])
    
    html = f"""
    <div style="
        background: {style['bg']};
        border-left: 4px solid {style['border']};
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(12px);
        animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    ">
        <div style="
            font-family: 'Crimson Pro', serif;
            font-size: 1.4rem;
            font-weight: 700;
            color: {style['color']};
            margin-bottom: 0.25rem;
        ">{style['title']}</div>
        <div style="
            font-family: 'Source Serif 4', serif;
            color: #7D8590;
            font-size: 1rem;
        ">Across {count} fact-checking source{'s' if count != 1 else ''}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_sources_block(sources_data: list[dict]):
    """Display fact-check results with enhanced card styling."""
    st.markdown("### Retrieved fact-checks by source")
    for src in sources_data:
        name = src.get("source_name", "Unknown Source")
        results = src.get("results", []) or []
        if not results:
            continue
        with st.expander(f"{name} ({len(results)} results)"):
            for i, r in enumerate(results):
                claim = r.get("claim", "No claim text")
                rating = format_rating_name(r.get("rating", "No rating"))
                publisher = r.get("publisher", "Unknown")
                url = r.get("url", "")
                similarity = r.get("similarity_score")
                
                # Build URL link if available
                url_link = ""
                if url:
                    url_link = f'<a href="{url}" target="_blank" style="font-family: \'Crimson Pro\', serif; color: #E63946; text-decoration: none; border-bottom: 1px solid transparent; transition: all 0.3s ease;">Read full fact-check →</a>'
                
                # Build similarity text if available
                similarity_text = ""
                if similarity is not None:
                    similarity_text = f'<div style="font-family: \'Source Serif 4\', serif; color: #484F58; font-size: 0.9rem; margin-top: 0.5rem; font-style: italic;">Similarity: {similarity:.3f}</div>'
                
                # Custom styled card for each result - single HTML block
                card_html = f"""
<div class="result-card">
    <div style="font-family: 'Crimson Pro', serif; font-size: 1.1rem; font-weight: 600; color: #E6EDF3; margin-bottom: 0.75rem; line-height: 1.5;">{i+1}. {claim[:150]}{'...' if len(claim) > 150 else ''}</div>
    <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
        <span style="font-family: 'Source Serif 4', serif; color: #7D8590;"><strong style="color: #E6EDF3;">Publisher:</strong> {publisher}</span>
        <span style="font-family: 'Source Serif 4', serif; color: #7D8590;"><strong style="color: #E6EDF3;">Rating:</strong> <span style="color: #FFB627;">{rating}</span></span>
    </div>
    {url_link}
    {similarity_text}
</div>
"""
                st.markdown(card_html, unsafe_allow_html=True)


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
    
    # Custom styled source context box

    # Pre-process ratings to reflect 2011 change: Barely True -> Mostly False
    # We consolidate both keys into 'mostly-false' for display
    ratings = source_stats.get('rating_breakdown', {}).copy()
    ratings['mostly-false'] = ratings.get('mostly-false', 0) + ratings.get('barely-true', 0)
    
    # Define standard PolitiFact ratings with colors
    # Updated 'barely-true' slot to 'mostly-false' with reddish-orange color
    rating_configs = [
        ('true', 'True', '#06D6A0'),
        ('mostly-true', 'Mostly True', '#A7C957'),
        ('half-true', 'Half True', '#FFCA3A'),
        ('mostly-false', 'Mostly False', '#FF7518'), # Reddish-Orange
        ('false', 'False', '#FF595E'),
        ('pants-fire', 'Pants on Fire', '#D62828')
    ]
    
    # Generate rows for breakdown
    rows_html = ""
    for key, label, color in rating_configs:
        count = ratings.get(key, 0)
        pct = (count / total * 100) if total > 0 else 0
        rows_html += f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; padding-bottom: 0.2rem; border-bottom: 1px solid rgba(255,255,255,0.03);"><span style="font-family: \'Source Serif 4\', serif; color: #E6EDF3; font-size: 0.95rem;">{label}</span><div style="display: flex; align-items: center; gap: 0.75rem;"><div style="width: 80px; height: 4px; background: rgba(48, 54, 61, 0.5); border-radius: 2px;"><div style="width: {pct}%; height: 100%; background: {color}; border-radius: 2px;"></div></div><span style="font-family: \'Source Serif 4\', serif; color: {color}; font-weight: 600; font-size: 0.95rem; min-width: 2.5rem; text-align: right;">{pct:.0f}%</span></div></div>'

    # Custom styled source context box - Single line to prevent Markdown rendering issues
    context_html = f"""<div class="source-context-card"><div style="font-family: 'Crimson Pro', serif; font-size: 1.6rem; font-weight: 700; color: #E6EDF3; margin-bottom: 0.5rem;">Source Detected: <span style="color: #E63946;">{source}</span></div><div style="font-family: 'Source Serif 4', serif; color: #7D8590; margin-bottom: 1rem; font-size: 1rem;">Fact-checked <strong style="color: #E6EDF3;">{total}</strong> times since 2007</div><div class="stats-box"><div style="font-family: 'Crimson Pro', serif; color: #E6EDF3; margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600;">{indicator}</div><div style="display: flex; flex-direction: column;">{rows_html}</div></div></div>"""
    
    st.markdown(context_html, unsafe_allow_html=True)
