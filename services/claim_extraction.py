
# ===========================
# File: services/claim_extraction.py
# ===========================
import streamlit as st
from services.clients import get_anthropic
from config import FLAGS


CLAIM_PROMPT = (
    "Please extract specific factual claims from this transcript that could be fact-checked.\n"
    "Focus on verifiable assertions (facts, statistics, events, policies).\n"
    "Ignore opinions, predictions or subjective statements.\n\n"
    "Return each claim on its own line prefixed by 'CLAIM: '.\n\nTranscript:\n{transcript}"
)

TERMS_PROMPT = (
    "Analyze this text and extract:\n"
    "1) Key factual claims (specific, verifiable)\n"
    "2) Important search terms (people, orgs, stats, policies, events)\n\n"
    "Format:\nCLAIMS:\n- ...\nSEARCH_TERMS:\n- ...\n\nText:\n{text}"
)


def extract_claims_from_transcript(transcript: str) -> list[str]:
    try:
        client = get_anthropic()
        prompt = CLAIM_PROMPT.format(transcript=transcript)
        resp = client.messages.create(
            model=FLAGS.ANTHROPIC_SONNET_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        content = resp.content[0].text if resp.content else ""
        claims = []
        for line in content.splitlines():
            if line.strip().lower().startswith("claim:"):
                claims.append(line.split(":", 1)[1].strip())
        return claims
    except Exception as e:
        st.error(f"Error extracting claims: {e}")
        return []


def extract_key_terms_and_claims(text: str) -> tuple[list[str], list[str]]:
    try:
        client = get_anthropic()
        resp = client.messages.create(
            model=FLAGS.ANTHROPIC_SONNET_MODEL,
            messages=[{"role": "user", "content": TERMS_PROMPT.format(text=text[:2000])}],
            max_tokens=600,
        )
        content = resp.content[0].text.strip() if resp.content else ""
        claims, terms = [], []
        section = None
        for line in content.splitlines():
            t = line.strip()
            if t.startswith("CLAIMS:"):
                section = "c"
            elif t.startswith("SEARCH_TERMS:"):
                section = "t"
            elif t.startswith("- "):
                val = t[2:].strip()
                if section == "c":
                    claims.append(val)
                elif section == "t":
                    terms.append(val)
        return claims, terms
    except Exception as e:
        st.warning(f"Error extracting key terms: {e}")
        return [], []