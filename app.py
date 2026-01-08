import streamlit as st
from config import FLAGS
from retrieval.index import load_index_and_meta
from services.clients import get_anthropic
from services.transcription import transcribe_audio
from services.claim_extraction import extract_claims_from_transcript
from services.fact_sources import get_multi_source_analysis
from services.logging import log_to_airtable
from prompts.assessment import build_enhanced_prompt
from utils.parsing import extract_response_text
from ui.components import consensus_badge, render_sources_block, render_source_context
from ui.custom_styles import get_custom_css
from utils.source_tracking import extract_source_from_claim, get_source_statistics, get_top_sources, format_rating_name
from retrieval.search import search_politifact_db

st.set_page_config(page_title="PolitiFact Jurisprudence Assistant", layout="wide")

# Inject custom CSS for distinctive design
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.title("PolitiFact Jurisprudence Assistant")
st.caption("Experimental assistant that compares drafts/claims against PolitiFact's archive and external fact-checks, "
           "analyzes cross-source consensus and suggests research next steps. It's powered by generative AI, so always adhere to [Poynter's AI guidance](https://docs.google.com/document/d/1yIb7QMz0IW02zbNm-qqfjFMvinYwuZmssJR01cx1iiQ/edit?tab=t.0) when using it.")

index, metadata = load_index_and_meta()

# Cache top sources for fast source detection
@st.cache_data
def get_known_sources(_metadata):
    """Get list of frequently fact-checked sources for detection."""
    return get_top_sources(_metadata, limit=500)  # Increased from 200 to cover more politicians

def render_pretty(markdown_text: str):
    if not markdown_text:
        st.warning("No analysis generated.")
        return
    st.markdown(markdown_text, unsafe_allow_html=True)

def render_pf_anchor(sources_data: list[dict]):
    # Pull top PF result and show it prominently (what editors expect)
    pf = next((s for s in sources_data if "PolitiFact Database" in s.get("source_name","")), None)
    if not pf or not pf.get("results"):
        return
    top = pf["results"][0]
    rating = format_rating_name(top.get("rating","N/A"))
    claim = top.get("claim","")
    url = top.get("url","")
    sim = top.get("similarity_score", None)
    msg = f"**Nearest PolitiFact precedent:** {rating} — {claim}"
    if url:
        msg += f" ([link]({url}))"
    if isinstance(sim, (int,float)):
        msg += f" · similarity ≈ {sim:.2f}"
    st.info(msg)

tab1, tab2, tab3 = st.tabs(["Text analysis", "Audio transcription", "Chat with Archive"])

with tab1:
    query = st.text_area("Paste your draft article or claim to fact-check:",
                         placeholder="e.g., 'The president said unemployment is at a historic low of 3.2%'",
                         height=160)
    use_web = st.checkbox("Web Search", value=True, help="Enable Google lookups")

    if query and st.button("Analyze", type="primary"):
        # Try to detect source/speaker from the claim text
        known_sources = get_known_sources(metadata)
        detected_source = extract_source_from_claim(query, known_sources)
        
        if detected_source:
            source_stats = get_source_statistics(detected_source, metadata)
            render_source_context(source_stats)
        
        with st.spinner("Analyzing across PolitiFact and other fact-checkers..."):
            sources_data, consensus = get_multi_source_analysis(query, index, metadata, st.secrets.get("GOOGLE_FACTCHECK_API_KEY",""))
            # Show the PF anchor so editors understand the baseline
            render_pf_anchor(sources_data)

            prompt = build_enhanced_prompt(query, sources_data, consensus, use_web)
            try:
                tools = None
                if use_web and FLAGS.ENABLE_WEB_SEARCH:
                    tools = [{"type": "web_search", "name": "web_search", "max_results": 5}]
                claude = get_anthropic()
                kwargs = {
                    "model": FLAGS.ANTHROPIC_OPUS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                }
                if tools:
                    kwargs["tools"] = tools
                resp = claude.messages.create(**kwargs)
                text = extract_response_text(resp)

                st.markdown("## Analysis")
                render_pretty(text)

                if FLAGS.LOGGING_ENABLED:
                    if log_to_airtable(query, text, sources_data, consensus):
                        st.success("Session logged to Airtable")
            except Exception as e:
                st.error(f"Error generating analysis: {e}")

        st.markdown("## What Other Fact-Checkers Found")
        consensus_badge(consensus)
        render_sources_block(sources_data)

with tab2:
    st.subheader("Audio/Video transcription & claim ID")
    uploaded = st.file_uploader("Choose an audio/video file", type=["mp3","wav","m4a","mp4","mov","avi"])
    if uploaded is not None:
        st.audio(uploaded)
        if st.button("Process Audio", type="primary"):
            with st.spinner("Transcribing & extracting claims..."):
                tr = transcribe_audio(uploaded)
                if tr:
                    st.session_state.audio_transcript = tr
                    st.session_state.audio_claims = extract_claims_from_transcript(tr) or []
                    st.success("Processing complete")

    if st.session_state.get("audio_transcript"):
        st.markdown("### Transcript")
        st.text_area("", value=st.session_state.audio_transcript, height=150, disabled=True)

    claims = st.session_state.get("audio_claims") or []
    if claims:
        st.markdown(f"### Found {len(claims)} claims")
        for i, c in enumerate(claims, 1):
            cols = st.columns([0.1, 0.7, 0.2])
            cols[0].markdown(f"**{i}.**")
            cols[1].markdown(c)
            if cols[2].button("Fact-check", key=f"fc_{i}"):
                with st.spinner("Fact-checking claim..."):
                    sources_data, consensus = get_multi_source_analysis(c, index, metadata, st.secrets.get("GOOGLE_FACTCHECK_API_KEY",""))
                    render_pf_anchor(sources_data)
                    prompt = build_enhanced_prompt(c, sources_data, consensus, use_web=True)
                    try:
                        tools = None
                        if FLAGS.ENABLE_WEB_SEARCH:
                            tools = [{"type": "web_search", "name": "web_search", "max_results": 5}]
                        claude = get_anthropic()
                        kwargs = {
                            "model": FLAGS.ANTHROPIC_OPUS_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 1500,
                        }
                        if tools:
                            kwargs["tools"] = tools
                        resp = claude.messages.create(**kwargs)
                        text = extract_response_text(resp)

                        st.markdown("---")
                        st.info(f"**Claim:** {c}")
                        render_pretty(text)

                        if FLAGS.LOGGING_ENABLED:
                            if log_to_airtable(c, text, sources_data, consensus):
                                st.success("Session logged to Airtable")

                        st.markdown("### What Other Fact-Checkers Found")
                        consensus_badge(consensus)
                        render_sources_block(sources_data)
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab3:
    st.subheader("Chat with the PolitiFact Archive")
    
    # Use a container for the chat history to keep it self-contained
    chat_container = st.container(height=600)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Render history inside the container
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Ask the archive (e.g., 'What about project 2025?')"):
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Render user message immediately in container
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Searching archive..."):
                    # 1. Retrieve context
                    results = search_politifact_db(prompt, index, metadata)
                    top_results = results.get("results", [])
                    
                    context_str = ""
                    if top_results:
                        context_items = []
                        for r in top_results:
                            # Create a concise block for the LLM
                            block = (
                                f"Claim: {r.get('claim', 'N/A')}\n"
                                f"Rating: {r.get('rating', 'N/A')}\n"
                                f"Explanation: {r.get('explanation', '')}\n"
                                f"URL: {r.get('url', '')}"
                            )
                            context_items.append(block)
                        context_str = "\n\n---\n\n".join(context_items)
                    
                    # 2. Build System Prompt (Instructions)
                    system_instructions_text = (
                        "You are a helpful assistant for PolitiFact. "
                        "## Instructions\n"
                        "- You must use retrieved sources to answer the journalist's question\n"
                        "- Every claim in your answer MUST cite evidence in the retrieved articles AND include the specific URL provided in the context (formatted as markdown links).\n"
                        "- If the journalist's search request is vague, ask for clarification\n"
                        "- When answering the journalist:\n"
                        "  - IF the retrieved articles are relevant AND from varying time periods, THEN ask the journalist what time period they are interested in\n"
                        "  - IF the retrieved articles are relevant AND from a unified time period, THEN answer the journalist while citing articles\n"
                        "  - IF the retrieved articles are NOT relevant, THEN tell the journalist you could not answer their question and to reword or rephrase their question\n"
                        "- IF you cannot answer the journalist, you MUST tell them instead of guessing\n"
                        "- You should always present information chronologically\n\n"
                        "Do not generate content that might be physically or emotionally harmful.\n"
                        "Do not generate hateful, racist, sexist, lewd, or violent content.\n"
                        "Do not include any speculation or inference beyond what is provided.\n"
                        "Do not infer details like background information, the reporter's gender, ancestry, roles, or positions.\n"
                        "Do not change or assume dates and times unless specified.\n"
                        "If a reporter asks for copyrighted content (books, lyrics, recipes, news articles, etc.), politely refuse and provide a brief summary or description instead."
                    )
                    
                    # 3. Build User Message with Context (RAG)
                    # We inject the retrieved context into the *latest* user turn for the LLM's visibility.
                    rag_user_content = (
                        f"Please answer the question based on the following context:\n\n"
                        f"### Retrieved Fact-Checks:\n{context_str}\n\n"
                        f"### Question:\n{prompt}"
                    )
                    
                    # 4. Prepare History
                    # We take all previous messages, but replace the *last* user message (which is just 'prompt' in UI state)
                    # with our 'rag_user_content' for the LLM.
                    api_messages = []
                    # Copy history excluding the just-added prompt
                    for m in st.session_state.messages[:-1]:
                        api_messages.append({"role": m["role"], "content": m["content"]})
                    
                    # Append our context-enriched current prompt
                    api_messages.append({"role": "user", "content": rag_user_content})

                    # 5. Call Claude
                    try:
                        claude = get_anthropic()
                        resp = claude.messages.create(
                            model=FLAGS.ANTHROPIC_OPUS_MODEL,
                            max_tokens=1000,
                            system=system_instructions_text,
                            messages=api_messages
                        )
                        answer = extract_response_text(resp)
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        
                    except Exception as e:
                        st.error(f"Error generating response: {e}")

st.markdown("---")
st.markdown("**Important:** This tool supports human judgment. It will only augment — never replace a real fact-checker:).")
