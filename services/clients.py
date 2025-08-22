import streamlit as st
from openai import OpenAI
import anthropic

_openai_client = None
_anthropic_client = None


def get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])  # raises if missing
    return _openai_client


def get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])  # raises if missing
    return _anthropic_client