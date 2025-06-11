import faiss
import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
import anthropic
import requests
import json
from datetime import datetime
import re
from pyairtable import Api

# Web search configuration
WEB_SEARCH_CONFIG = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 2,  # Keep low to avoid slowdown
}

# Load index + metadata
@st.cache_resource
def load_data():
    index = faiss.read_index("factcheck_index.faiss")
    metadata = pd.read_json("factcheck_metadata.json")
    return index, metadata

index, metadata = load_data()

# API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
claude_client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# Google Fact Check API Key
GOOGLE_FACTCHECK_API_KEY = st.secrets["GOOGLE_FACTCHECK_API_KEY"]

# Whisper transcription function
def transcribe_audio(audio_file):
    """Transcribe audio file using OpenAI Whisper"""
    try:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

# Extract claims from transcript
def extract_claims_from_transcript(transcript):
    """Use Claude to extract factual claims from transcript"""
    try:
        prompt = f"""
Please extract specific factual claims from this transcript that could be fact-checked. 
Focus on statements that make verifiable assertions about facts, statistics, events or policies.
Ignore opinions, predictions or subjective statements.

Format each claim as a separate line starting with "CLAIM:" 

Transcript:
{transcript}
"""
        
        response = claude_client.messages.create(
            model="claude-opus-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        
        claims_text = response.content[0].text.strip()
        # Extract individual claims
        claims = []
        for line in claims_text.split('\n'):
            if line.strip().startswith('CLAIM:'):
                claims.append(line.replace('CLAIM:', '').strip())
        
        return claims
    except Exception as e:
        st.error(f"Error extracting claims: {str(e)}")
        return []

def log_to_airtable(query, ai_response, sources_data, consensus):
    """Log fact-check session to Airtable"""
    try:
        api = Api(st.secrets["AIRTABLE_API_KEY"])
        table = api.table(st.secrets["AIRTABLE_BASE_ID"], st.secrets.get("AIRTABLE_TABLE_ID", "tblj5Tj4ZqxDLZsyJ"))
        
        # Prepare data for logging
        record = {
            "Query": query[:1000],  
            "AI Response": ai_response[:2000],  
            "Sources Count": len(sources_data),
            "Consensus Level": consensus.get('agreement', 'N/A'),
            "Average Rating": consensus.get('average_rating', 0) if consensus.get('average_rating') is not None else 0,
            "Source Names": ", ".join([s.get('source_name', '') for s in sources_data])
        }
        
        table.create(record)
        return True
        
    except Exception as e:
        st.error(f"Failed to log to Airtable: {str(e)}")
        return False

# Embed user query
@st.cache_data
def embed_text(text):
    response = openai_client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Enhanced query processing for better API results
def extract_key_terms_and_claims(text):
    """Extract key terms and factual claims from draft text for better API searches"""
    try:
        prompt = f"""
Analyze this draft text and extract:
1. Key factual claims that could be fact-checked (specific, verifiable statements)
2. Important search terms (people, organizations, statistics, policies, events)

Format your response as:
CLAIMS:
- [Specific claim 1]
- [Specific claim 2]
- [etc.]

SEARCH_TERMS:
- [key term 1]
- [key term 2]
- [etc.]

Text to analyze:
{text[:2000]}
"""
        
        response = claude_client.messages.create(
            model="claude-opus-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        
        content = response.content[0].text.strip()
        
        # Parse the response
        claims = []
        search_terms = []
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('CLAIMS:'):
                current_section = 'claims'
            elif line.startswith('SEARCH_TERMS:'):
                current_section = 'search_terms'
            elif line.startswith('- ') and current_section:
                term = line[2:].strip()
                if current_section == 'claims':
                    claims.append(term)
                elif current_section == 'search_terms':
                    search_terms.append(term)
        
        return claims, search_terms
        
    except Exception as e:
        st.warning(f"Error extracting key terms: {str(e)}")
        return [], []

# Google fact-check search with multiple queries
def enhanced_google_factcheck_search(query, max_results=5):
    """Enhanced Google Fact Check search using key terms and claims"""
    if not GOOGLE_FACTCHECK_API_KEY:
        return []
    
    all_results = []
    
    # If query is long (likely a draft), extract key terms
    if len(query) > 200:
        claims, search_terms = extract_key_terms_and_claims(query)
        
        # Search with extracted claims
        for claim in claims[:3]:  # Top 3 claims
            results = search_google_factcheck(claim, max_results=3)
            all_results.extend(results)
        
        # Search with key terms
        for term in search_terms[:3]:  # Top 3 terms
            results = search_google_factcheck(term, max_results=2)
            all_results.extend(results)
    else:
        # For short queries, use original method
        all_results = search_google_factcheck(query, max_results)
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    return unique_results[:max_results]

def search_google_factcheck(query, max_results=5):
    """Search Google's Fact Check Tools API"""
    if not GOOGLE_FACTCHECK_API_KEY:
        return []
    
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            'query': query,
            'key': GOOGLE_FACTCHECK_API_KEY,
            'pageSize': max_results
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            claims = data.get('claims', [])
            
            results = []
            for claim in claims:
                claim_reviews = claim.get('claimReview', [])
                for review in claim_reviews:
                    results.append({
                        'source': 'Multi-Source',
                        'publisher': review.get('publisher', {}).get('name', 'Unknown'),
                        'claim': claim.get('text', ''),
                        'rating': review.get('textualRating', 'No rating'),
                        'url': review.get('url', ''),
                        'review_date': review.get('reviewDate', ''),
                        'language': review.get('languageCode', 'en')
                    })
            return results[:max_results]
        else:
            st.warning(f"Google Fact Check API returned status {response.status_code}")
            return []
    except Exception as e:
        st.warning(f"Error accessing Google Fact Check API: {str(e)}")
        return []

def standardize_rating(rating, source='unknown'):
    """Convert various rating systems to a 0-5 scale"""
    rating = str(rating).lower().strip()
    
    # PolitiFact scale
    politifact_map = {
        'true': 5,
        'mostly true': 4,
        'half true': 3,
        'mostly false': 2,
        'false': 1,
        'pants on fire': 0
    }
    
    # Generic mappings for other sources
    generic_map = {
        'true': 5,
        'mostly true': 4,
        'mixture': 3,
        'mixed': 3,
        'partly false': 3,
        'mostly false': 2,
        'false': 1,
        'fake': 1,
        'misleading': 2,
        'unproven': 3,
        'correct': 5,
        'incorrect': 1,
        'accurate': 5,
        'inaccurate': 1
    }
    
    # Try PolitiFact first, then generic
    for rating_text, score in {**politifact_map, **generic_map}.items():
        if rating_text in rating:
            return score
    
    return None  # Unknown rating

def analyze_consensus(sources_data):
    """Analyze agreement between different fact-checking sources"""
    if not sources_data:
        return {
            'consensus_level': 0,
            'average_rating': None,
            'agreement': 'No data',
            'outliers': [],
            'source_count': 0
        }
    
    # Extract standardized ratings
    ratings = []
    source_ratings = {}
    
    for source_data in sources_data:
        for result in source_data.get('results', []):
            rating = standardize_rating(result.get('rating', ''))
            if rating is not None:
                ratings.append(rating)
                source_name = result.get('publisher', result.get('source', 'Unknown'))
                source_ratings[source_name] = rating
    
    if not ratings:
        return {
            'consensus_level': 0,
            'average_rating': None,
            'agreement': 'No standardizable ratings',
            'outliers': [],
            'source_count': len(sources_data)
        }
    
    # Calculate consensus metrics
    avg_rating = np.mean(ratings)
    std_rating = np.std(ratings) if len(ratings) > 1 else 0
    
    # Consensus level (higher when ratings are similar)
    consensus_level = max(0, 1 - (std_rating / 2.5))  # Normalize by max possible std
    
    # Identify outliers (ratings far from average)
    outliers = []
    for source, rating in source_ratings.items():
        if abs(rating - avg_rating) > 1.5:  # More than 1.5 points from average
            outliers.append(f"{source} ({rating})")
    
    # Agreement description
    if consensus_level > 0.8:
        agreement = "Strong consensus"
    elif consensus_level > 0.6:
        agreement = "Moderate agreement"
    elif consensus_level > 0.4:
        agreement = "Some disagreement"
    else:
        agreement = "Significant disagreement"
    
    return {
        'consensus_level': consensus_level,
        'average_rating': avg_rating,
        'agreement': agreement,
        'outliers': outliers,
        'source_count': len(set(source_ratings.keys())),
        'source_ratings': source_ratings
    }

def search_politifact_db(query):
    """Search the local PolitiFact database"""
    query_vector = np.array([embed_text(query)], dtype="float32")
    D, I = index.search(query_vector, k=5)
    top_matches = metadata.iloc[I[0]]
    
    results = []
    for _, row in top_matches.iterrows():
        results.append({
            'source': 'PolitiFact',
            'publisher': 'PolitiFact',
            'claim': row['claim'],
            'rating': row['rating'],
            'explanation': row.get('explanation', '')[:500] + "..." if len(row.get('explanation', '')) > 500 else row.get('explanation', ''),
            'url': row['url'],
            'similarity_score': float(D[0][list(top_matches.index).index(row.name)])
        })
    
    return {'source_name': 'PolitiFact Database', 'results': results}

def get_multi_source_analysis(query):
    """Get fact-checks from multiple sources and analyze consensus"""
    sources_data = []
    
    # Search PolitiFact database
    politifact_data = search_politifact_db(query)
    sources_data.append(politifact_data)
    
    # Google Fact Check API search
    google_results = enhanced_google_factcheck_search(query)
    if google_results:
        google_data = {
            'source_name': 'External Sources (via Google)',
            'results': google_results
        }
        sources_data.append(google_data)
    
    # Analyze consensus
    consensus = analyze_consensus(sources_data)
    
    return sources_data, consensus

# Helper functions for web search
def extract_response_text(response):
    """Extract text from Claude's response, handling web search structure"""
    response_text = ""
    for content in response.content:
        if hasattr(content, 'type') and content.type == "text":
            response_text += content.text
        elif isinstance(content, dict) and content.get('type') == 'text':
            response_text += content.get('text', '')
    return response_text.strip()

def should_use_web_search(query, sources_data, consensus):
    """Determine if web search should be used"""
    # Check for recent time indicators
    recent_indicators = ['yesterday', 'today', 'this week', 'current', 'latest', '2025']
    has_recent = any(indicator in query.lower() for indicator in recent_indicators)
    
    # Check if we have limited sources
    has_limited_sources = len(sources_data) < 2 or consensus['source_count'] < 2
    
    # Short claims more likely to need current info
    is_short_claim = len(query.split()) < 50
    
    return (has_recent or has_limited_sources) and is_short_claim

# Prompt building
def build_enhanced_prompt(query, sources_data, consensus, use_web_search=False):
    """Build prompt with multi-source context and consensus analysis"""
    
    # Build context from all sources
    all_contexts = []
    
    for source_data in sources_data:
        source_name = source_data.get('source_name', 'Unknown Source')
        results = source_data.get('results', [])
        
        if results:
            all_contexts.append(f"\n--- {source_name} ---")
            for i, result in enumerate(results[:3]):  # Limit to top 3 per source
                claim = result.get('claim', 'No claim text')
                rating = result.get('rating', 'No rating')
                explanation = result.get('explanation', '')
                url = result.get('url', '')
                publisher = result.get('publisher', source_name)
                
                context_text = f"Claim: {claim}\nPublisher: {publisher}\nRating: {rating}"
                if explanation:
                    context_text += f"\nExplanation: {explanation}"
                if url:
                    context_text += f"\nURL: {url}"
                
                all_contexts.append(context_text)
    
    combined_context = "\n\n".join(all_contexts)
    
    # Add consensus analysis
    consensus_text = f"""
    
CROSS-SOURCE CONSENSUS ANALYSIS:
- Agreement Level: {consensus['agreement']}
- Sources Analyzed: {consensus['source_count']}
- Average Rating Tendency: {consensus.get('average_rating', 'N/A')}
"""
    
    if consensus.get('outliers'):
        consensus_text += f"- Outlying Opinions: {', '.join(consensus['outliers'])}"
    
    # Add web search instruction if enabled
    search_instruction = ""
    if use_web_search:
        search_instruction = """
IMPORTANT: Web search is enabled. Use it to find current information if:
- The claim involves recent events or statistics
- Existing fact-checks seem outdated
- You need additional context for accuracy
"""
    
    return f"""
You are a senior research assistant helping a journalist assess the accuracy of a draft article for PolitiFact.

IMPORTANT: Format your response with proper spacing and line breaks. Use clear, readable text without run-on formatting.

{search_instruction}

Your task is to:
1. Analyze the claim(s) in the draft text.
2. Compare the evidence in the article to relevant fact-checks from MULTIPLE sources.
3. Consider both the **evidence in the article** and the **ratings and reasoning** from similar fact-checks.
4. Pay special attention to the **consensus analysis** - note areas of agreement or disagreement between sources.
5. If sources disagree significantly, explain possible reasons and which evidence seems strongest.
6. If the article's claims appear **novel** or significantly **different from precedent**, state that clearly.

Return your assessment in the following format:

**Suggested Rating:**
[Your recommendation, e.g. False, Mostly False, Half True, Mostly True, True, etc.]

**Confidence Level:**
[High/Medium/Low - based on quality and consensus of evidence]

**Reasoning:**
Explain your reasoning using both the factual evidence provided in the draft article and the past fact-checks retrieved from multiple sources. Consider the consensus analysis and any disagreements between sources.

**Multi-Source Analysis:**
Summarize how different fact-checking organizations have approached similar claims. Note areas of consensus and disagreement.

**Jurisprudence:**
List the most similar claims from past fact-checks and how they were rated by different organizations. If none are relevant, say so.

**Evidence Gaps:**
What additional reporting or verification would strengthen this fact-check?

---
Draft article to fact-check:
{query}

---
Relevant fact-checks from multiple sources:
{combined_context}

{consensus_text}
"""

# Streamlit UI
st.title("PolitiFact Rating Recommender")
st.caption("This generative AI tool compares draft articles against PolitiFact's archive and external fact-checking sources. It identifies relevant jurisprudence, analyzes cross-source consensus and provides structured recommendations to support editorial decisions. I used retrieval-augmented generation (RAG) to mostly eliminate hallucinations by tying it to fact-check databases. Note: This is a prototype based on 9,000 fact-checks, so answers will not be complete.")

# Feature info in sidebar
with st.sidebar:
    st.header("⚙️ Features")
    st.success("✅ Google Fact Check API configured")
    st.info("🔍 Claude Web Search available")
    st.markdown("**Capabilities:**")
    st.markdown("• PolitiFact database search")
    st.markdown("• Multi-source fact-check retrieval")
    st.markdown("• Real-time web search (when needed)")
    st.markdown("• Consensus analysis")
    st.markdown("• Confidence scoring")
    st.markdown("• Evidence gap identification")
    st.markdown("• **NEW:** Audio transcription & claim extraction")

# Create tabs for different input methods
tab1, tab2 = st.tabs(["📝 Text Fact-Check", "🎵 Audio Fact-Check"])

# Initialize query
query = None
use_web_search = False

with tab1:
    # Text input interface
    query = st.text_area(
        "📝 Paste your draft article or claim to fact-check:", 
        placeholder="e.g., 'The president said unemployment is at a historic low of 3.2%'",
        height=150
    )
    
    # Web search toggle - ALWAYS visible
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💡 **Tip:** Enable web search for claims about recent events or when you need current information")
    
    with col2:
        use_web_search = st.checkbox(
            "🔍 Web Search", 
            value=False,  # Default to off
            help="Enable to search for current information (adds 10-20 seconds)"
        )
    
    # Show current mode
    if use_web_search:
        st.success("✅ Web search enabled - will look for current information")
    else:
        st.info("📚 Using fact-check databases only (faster)")

with tab2:
    st.subheader("🎵 Audio/Video Fact-Checking")
    st.caption("Manual workflow: Upload → Process → Select → Fact-check")
    
    # Step 1: File Upload
    uploaded_file = st.file_uploader(
        "Step 1: Choose an audio/video file",
        type=['mp3', 'wav', 'm4a', 'mp4', 'mov', 'avi'],
        help="Upload your file first, then click Process"
    )
    
    # Step 2: Manual processing
    if uploaded_file is not None:
        st.audio(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Step 2: 🎵 Process Audio", type="primary"):
                st.session_state.processing = True
        
        with col2:
            if st.button("🗑️ Clear Results"):
                if 'audio_claims' in st.session_state:
                    del st.session_state.audio_claims
                if 'audio_transcript' in st.session_state:
                    del st.session_state.audio_transcript
                st.session_state.processing = False
                st.rerun()
    
    # Step 3: Show processing results
    if uploaded_file and st.session_state.get('processing', False):
        with st.spinner("Processing audio... This may take a moment."):
            transcript = transcribe_audio(uploaded_file)
            
            if transcript:
                st.session_state.audio_transcript = transcript
                claims = extract_claims_from_transcript(transcript)
                st.session_state.audio_claims = claims if claims else []
                st.session_state.processing = False
                st.success("✅ Processing complete!")
                st.rerun()
    
    # Step 4: Show results (only if we have them)
    if st.session_state.get('audio_transcript'):
        st.subheader("📝 Transcript")
        st.text_area("", value=st.session_state.audio_transcript, height=150, disabled=True)
        
        if st.session_state.get('audio_claims'):
            st.subheader(f"🎯 Found {len(st.session_state.audio_claims)} Claims")
            
            # Simple text input for claim selection
            claim_number = st.number_input(
                "Step 3: Enter claim number to fact-check:", 
                min_value=1, 
                max_value=len(st.session_state.audio_claims),
                value=1,
                help="Type the number of the claim you want to fact-check"
            )
            
            # Show all claims
            for i, claim in enumerate(st.session_state.audio_claims):
                if i + 1 == claim_number:
                    st.success(f"**{i+1}. {claim}** ← SELECTED")
                else:
                    st.write(f"**{i+1}.** {claim}")
            
            # Simple fact-check button
            if st.button("Step 4: 🔍 Fact-Check Selected Claim", type="primary"):
                selected_claim = st.session_state.audio_claims[claim_number - 1]
                
                # Process this specific claim
                with st.spinner("🔍 Fact-checking..."):
                    sources_data, consensus = get_multi_source_analysis(selected_claim)
                    prompt = build_enhanced_prompt(selected_claim, sources_data, consensus, use_web_search=True)
                    
                    try:
                        # Always use web search for audio claims (they're usually short)
                        response = claude_client.messages.create(
                            model="claude-opus-4-20250514",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=1500,
                            tools=[WEB_SEARCH_CONFIG]
                        )
                        
                        st.markdown("---")
                        st.markdown("## ✨ Fact-Check Results")
                        st.info(f"**Claim:** {selected_claim}")
                        
                        # Extract and display response
                        response_text = extract_response_text(response)
                        st.markdown(response_text)
                        
                        # Log to Airtable
                        if log_to_airtable(selected_claim, response_text, sources_data, consensus):
                            st.success("✅ Session logged successfully")
                        
                        # Display consensus metrics in a more readable way
                        if consensus['source_count'] > 1:
                            st.markdown("### 📊 What Other Fact-Checkers Found")
                            
                            # Create a more narrative explanation
                            agreement = consensus['agreement']
                            source_count = consensus['source_count']
                            
                            if agreement == "Strong consensus":
                                st.success(f"✅ **Strong Agreement**: {source_count} fact-checking sources mostly agree on this topic.")
                            elif agreement == "Moderate agreement":
                                st.info(f"⚖️ **Some Agreement**: {source_count} fact-checking sources have similar but not identical findings.")
                            elif agreement == "Some disagreement":
                                st.warning(f"🤔 **Mixed Findings**: {source_count} fact-checking sources have different conclusions.")
                            else:
                                st.error(f"⚠️ **Conflicting Information**: {source_count} fact-checking sources significantly disagree.")
                            
                            # Show average tendency in plain language
                            if consensus.get('average_rating') is not None:
                                avg_rating = consensus['average_rating']
                                if avg_rating >= 4:
                                    tendency = "Most sources lean toward **TRUE**"
                                elif avg_rating >= 3:
                                    tendency = "Sources are **MIXED** on this claim"
                                elif avg_rating >= 2:
                                    tendency = "Most sources lean toward **FALSE**"
                                else:
                                    tendency = "Most sources rate this **FALSE**"
                                
                                st.write(f"**Overall pattern:** {tendency}")
                            
                            # Highlight conflicts
                            if consensus.get('outliers'):
                                st.write("**⚠️ Note:** Some sources have notably different ratings:")
                                for outlier in consensus['outliers']:
                                    st.write(f"  • {outlier}")
                                st.write("*Consider investigating why sources disagree.*")
                        
                        # Display source details
                        st.markdown("### Retrieved fact-checks by source")
                        
                        for source_data in sources_data:
                            source_name = source_data.get('source_name', 'Unknown Source')
                            results = source_data.get('results', [])
                            
                            if results:
                                with st.expander(f"{source_name} ({len(results)} results)"):
                                    for i, result in enumerate(results):
                                        claim = result.get('claim', 'No claim text')
                                        rating = result.get('rating', 'No rating')
                                        publisher = result.get('publisher', 'Unknown')
                                        url = result.get('url', '')
                                        
                                        # Format the display
                                        st.markdown(f"**{i+1}. {claim[:100]}{'...' if len(claim) > 100 else ''}**")
                                        st.markdown(f"*Publisher:* {publisher} | *Rating:* {rating}")
                                        
                                        if url:
                                            st.markdown(f"[📖 Read full fact-check]({url})")
                                        
                                        # Show similarity score for PolitiFact results
                                        if 'similarity_score' in result:
                                            st.caption(f"Similarity score: {result['similarity_score']:.3f}")
                                        
                                        if i < len(results) - 1:
                                            st.markdown("---")
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.warning("No fact-checkable claims found in the audio.")

# Process the query ONLY from the text tab
if query:
    with st.spinner("🔍 Analyzing across multiple fact-checking sources..."):
        # Get multi-source analysis
        sources_data, consensus = get_multi_source_analysis(query)
        
        # Generate enhanced prompt and get Claude's analysis
        prompt = build_enhanced_prompt(query, sources_data, consensus, use_web_search)
        
        try:
            # Use web search based on toggle
            if use_web_search:
                response = claude_client.messages.create(
                    model="claude-opus-4-20250514",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    tools=[WEB_SEARCH_CONFIG]
                )
            else:
                response = claude_client.messages.create(
                    model="claude-opus-4-20250514",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500
                )
            
            # Display the main analysis
            st.markdown("## ✨ Analysis ✅")
            response_text = extract_response_text(response)
            st.markdown(response_text)
            
            # Log to Airtable
            if log_to_airtable(query, response_text, sources_data, consensus):
                st.success("✅ Session logged successfully")
            
        except Exception as e:
            st.error(f"Error generating analysis: {str(e)}")
    
    # Display consensus metrics
    if consensus['source_count'] > 1:
        st.markdown("## 📊 What Other Fact-Checkers Found")
        
        # Create a more narrative explanation
        agreement = consensus['agreement']
        source_count = consensus['source_count']
        
        if agreement == "Strong consensus":
            st.success(f"✅ **Strong Agreement**: {source_count} fact-checking sources mostly agree on this topic.")
        elif agreement == "Moderate agreement":
            st.info(f"⚖️ **Some Agreement**: {source_count} fact-checking sources have similar but not identical findings.")
        elif agreement == "Some disagreement":
            st.warning(f"🤔 **Mixed Findings**: {source_count} fact-checking sources have different conclusions.")
        else:
            st.error(f"⚠️ **Conflicting Information**: {source_count} fact-checking sources significantly disagree.")
        
        # Show average tendency
        if consensus.get('average_rating') is not None:
            avg_rating = consensus['average_rating']
            if avg_rating >= 4:
                tendency = "Most sources lean toward **TRUE**"
            elif avg_rating >= 3:
                tendency = "Sources are **MIXED** on this claim"
            elif avg_rating >= 2:
                tendency = "Most sources lean toward **FALSE**"
            else:
                tendency = "Most sources rate this **FALSE**"
            
            st.write(f"**Overall pattern:** {tendency}")
        
        # Highlight conflicts
        if consensus.get('outliers'):
            st.write("**⚠️ Note:** Some sources have notably different ratings:")
            for outlier in consensus['outliers']:
                st.write(f"  • {outlier}")
            st.write("*Consider investigating why sources disagree.*")
    
    # Display source details
    st.markdown("## Retrieved fact-checks by source")
    
    for source_data in sources_data:
        source_name = source_data.get('source_name', 'Unknown Source')
        results = source_data.get('results', [])
        
        if results:
            with st.expander(f"{source_name} ({len(results)} results)"):
                for i, result in enumerate(results):
                    claim = result.get('claim', 'No claim text')
                    rating = result.get('rating', 'No rating')
                    publisher = result.get('publisher', 'Unknown')
                    url = result.get('url', '')
                    
                    # Format the display
                    st.markdown(f"**{i+1}. {claim[:100]}{'...' if len(claim) > 100 else ''}**")
                    st.markdown(f"*Publisher:* {publisher} | *Rating:* {rating}")
                    
                    if url:
                        st.markdown(f"[📖 Read full fact-check]({url})")
                    
                    # Show similarity score for PolitiFact results
                    if 'similarity_score' in result:
                        st.caption(f"Similarity score: {result['similarity_score']:.3f}")
                    
                    if i < len(results) - 1:
                        st.markdown("---")

# Footer
st.markdown("---")
st.markdown("**Important:** This tool provides AI-powered recommendations to support human fact-checkers. Always verify claims with primary sources and apply editorial judgment.")