"""
Source/Speaker tracking utilities for credibility analysis.
Detects sources in claims and provides historical fact-check statistics.
"""
import pandas as pd
import re
from typing import Dict, Optional, List


def extract_source_from_claim(claim_text: str, all_sources: List[str]) -> Optional[str]:
    """
    Extract source/speaker from claim text using pattern matching.
    
    Looks for patterns like:
    - "X said..."
    - "According to X..."
    - "X's claim..."
    - "X (@handle) on [Platform]"  (social media)
    - Person name at start of text
    
    Args:
        claim_text: The claim text to analyze
        all_sources: List of known sources to match against
        
    Returns:
        Detected source name or None
    """
    if not claim_text or not all_sources:
        return None
    
    # Common patterns for source attribution
    patterns = [
        # Social media format: "Ron DeSantis (@RonDeSantis) on X"
        r"^([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s*\(@?\w+\)\s*on\s+(?:X|Twitter|Facebook|Instagram)",
        
        # Standard attribution: "X said", "X claimed", etc.
        r"(?:^|\s)([A-Z][a-z]+(?: [A-Z][a-z]+)*) (?:said|says|stated|claims|claimed|wrote|posted)",
        
        # Quote attribution: "according to X"
        r"according to ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
        
        # Possessive: "X's claim/statement"
        r"(?:^|\s)([A-Z][a-z]+(?: [A-Z][a-z]+)*)'s (?:claim|statement|post|tweet)",
        
        # Simple format: "X said" at start
        r"^([A-Z][a-z]+(?: [A-Z][a-z]+)*) said",
        
        # Name at very beginning (for social posts)
        r"^([A-Z][a-z]+(?: [A-Z][a-z]+)*)(?:\s*\(|:|\s+on\s+|\s*-)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, claim_text, re.IGNORECASE | re.MULTILINE)
        if match:
            potential_source = match.group(1).strip()
            
            # Check if it matches a known source (exact match)
            for source in all_sources:
                if source.lower() == potential_source.lower():
                    return source
            
            # Check for partial matches (e.g., "Trump" matches "Donald Trump")
            for source in all_sources:
                if potential_source.lower() in source.lower() or source.lower() in potential_source.lower():
                    # Prefer longer match (full name over partial)
                    if len(source) > len(potential_source):
                        return source
                    
    return None


def get_source_statistics(source: str, metadata: pd.DataFrame) -> Optional[Dict]:
    """
    Get comprehensive fact-check statistics for a specific source.
    
    Args:
        source: Name of the source/speaker
        metadata: DataFrame with fact-check metadata
        
    Returns:
        Dictionary with statistics or None if source not found
    """
    # Check if source column exists
    if 'source' not in metadata.columns:
        return None
        
    source_claims = metadata[metadata['source'] == source]
    
    if len(source_claims) == 0:
        return None
    
    # Rating breakdown
    ratings = source_claims['verdict'].value_counts()
    total = len(source_claims)
    
    # Calculate false percentage (misleading/false claims)
    false_ratings = ['false', 'pants-fire', 'barely-true']
    false_count = sum(ratings.get(r, 0) for r in false_ratings)
    false_pct = (false_count / total) * 100
    
    # Calculate true percentage (accurate claims)
    true_ratings = ['true', 'mostly-true']
    true_count = sum(ratings.get(r, 0) for r in true_ratings)
    true_pct = (true_count / total) * 100
    
    # Calculate mixed percentage
    mixed_ratings = ['half-true']
    mixed_count = sum(ratings.get(r, 0) for r in mixed_ratings)
    mixed_pct = (mixed_count / total) * 100
    
    # Determine credibility indicator
    if false_pct > 50:
        indicator = "🔴 High False Rate"
        color = "red"
    elif true_pct > 50:
        indicator = "🟢 High True Rate"
        color = "green"
    else:
        indicator = "🟡 Mixed Record"
        color = "orange"
    
    return {
        'source': source,
        'total_checks': total,
        'rating_breakdown': ratings.to_dict(),
        'false_percentage': false_pct,
        'true_percentage': true_pct,
        'mixed_percentage': mixed_pct,
        'indicator': indicator,
        'indicator_color': color,
        'earliest_check': source_claims['publication_date'].min() if 'publication_date' in source_claims.columns else None,
        'latest_check': source_claims['publication_date'].max() if 'publication_date' in source_claims.columns else None,
    }


def get_top_sources(metadata: pd.DataFrame, limit: int = 50) -> List[str]:
    """
    Get most frequently fact-checked sources.
    
    Args:
        metadata: DataFrame with fact-check metadata
        limit: Maximum number of sources to return
        
    Returns:
        List of source names, sorted by frequency
    """
    # Check if source column exists
    if 'source' not in metadata.columns:
        return []
    
    return metadata['source'].value_counts().head(limit).index.tolist()


def format_rating_name(rating: str) -> str:
    """
    Format rating codes into human-readable names.
    
    Args:
        rating: Rating code (e.g., 'pants-fire', 'mostly-true')
        
    Returns:
        Formatted rating name
    """
    rating_map = {
        'true': '✅ True',
        'mostly-true': '🟢 Mostly True',
        'half-true': '🟡 Half True',
        'barely-true': '🟠 Barely True',
        'false': '🔴 False',
        'pants-fire': '🔥 Pants on Fire',
        'full-flop': '↩️ Full Flop',
        'half-flip': '↪️ Half Flip',
        'no-flip': '➡️ No Flip',
    }
    
    return rating_map.get(rating.lower(), rating.title())
