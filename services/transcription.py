import streamlit as st
from config import FLAGS
from services.clients import get_openai


def transcribe_audio(uploaded_file) -> str | None:
    """Transcribe audio/video via Whisper; works with Streamlit file_uploader objects."""
    try:
        client = get_openai()
        uploaded_file.seek(0)
        # Try to preserve filename and mime; fall back if unknown
        fname = getattr(uploaded_file, "name", "upload.wav")
        mime = getattr(uploaded_file, "type", "audio/wav")
        transcript = client.audio.transcriptions.create(
            model=FLAGS.OPENAI_WHISPER_MODEL,
            file=(fname, uploaded_file, mime),
        )
        return transcript.text
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return None