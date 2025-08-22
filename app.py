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
from ui.components import consensus_badge, render_sources_block

st.set_page_config(page_title="PolitiFact Jurisprudence Assistant", layout="wide")

st.title("PolitiFact Jurisprudence Assistant")
st.caption("Experimental assistant that compares drafts/claims against PolitiFact's archive and external fact-checks, "
           "analyzes cross-source consensus and suggests research next steps. It's powered by generative AI, so always adhere to [Poynter's AI guidance](https://docs.google.com/document/d/1yIb7QMz0IW02zbNm-qqfjFMvinYwuZmssJR01cx1iiQ/edit?tab=t.0) when using it.")

index, metadata = load_index_and_meta()

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
    rating = top.get("rating","N/A")
    claim = top.get("claim","")
    url = top.get("url","")
    sim = top.get("similarity_score", None)
    msg = f"**Nearest PolitiFact precedent:** {rating} — {claim}"
    if url:
        msg += f" ([link]({url}))"
    if isinstance(sim, (int,float)):
        msg += f" · similarity ≈ {sim:.2f}"
    st.info(msg)

tab1, tab2 = st.tabs(["📝 Text analysis", "🎵 Audio transcription"])

with tab1:
    query = st.text_area("📝 Paste your draft article or claim to fact-check:",
                         placeholder="e.g., 'The president said unemployment is at a historic low of 3.2%'",
                         height=160)
    use_web = st.checkbox("🔍 Web Search", value=True, help="Enable Google lookups")

    if query and st.button("Analyze", type="primary"):
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
                    "model": FLAGS.ANTHROPIC_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                }
                if tools:
                    kwargs["tools"] = tools
                resp = claude.messages.create(**kwargs)
                text = extract_response_text(resp)

                st.markdown("## ✨ Analysis ✅")
                render_pretty(text)

                if FLAGS.LOGGING_ENABLED:
                    if log_to_airtable(query, text, sources_data, consensus):
                        st.success("✅ Session logged to Airtable")
            except Exception as e:
                st.error(f"Error generating analysis: {e}")

        st.markdown("## 📊 What Other Fact-Checkers Found")
        consensus_badge(consensus)
        render_sources_block(sources_data)

with tab2:
    st.subheader("🎵 Audio/Video transcription & claim ID")
    uploaded = st.file_uploader("Choose an audio/video file", type=["mp3","wav","m4a","mp4","mov","avi"])
    if uploaded is not None:
        st.audio(uploaded)
        if st.button("🎵 Process Audio", type="primary"):
            with st.spinner("Transcribing & extracting claims..."):
                tr = transcribe_audio(uploaded)
                if tr:
                    st.session_state.audio_transcript = tr
                    st.session_state.audio_claims = extract_claims_from_transcript(tr) or []
                    st.success("✅ Processing complete")

    if st.session_state.get("audio_transcript"):
        st.markdown("### 📝 Transcript")
        st.text_area("", value=st.session_state.audio_transcript, height=150, disabled=True)

    claims = st.session_state.get("audio_claims") or []
    if claims:
        st.markdown(f"### 🎯 Found {len(claims)} claims")
        for i, c in enumerate(claims, 1):
            cols = st.columns([0.1, 0.7, 0.2])
            cols[0].markdown(f"**{i}.**")
            cols[1].markdown(c)
            if cols[2].button("🔍 Fact-check", key=f"fc_{i}"):
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
                            "model": FLAGS.ANTHROPIC_MODEL,
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
                                st.success("✅ Session logged to Airtable")

                        st.markdown("### 📊 What Other Fact-Checkers Found")
                        consensus_badge(consensus)
                        render_sources_block(sources_data)
                    except Exception as e:
                        st.error(f"Error: {e}")

st.markdown("---")
st.markdown("**Important:** This tool supports human judgment. It was always augment — never replace a real fact-checker:).")
