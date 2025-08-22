import streamlit as st
from pyairtable import Api

def log_to_airtable(query: str, ai_response: str, *_ignored) -> bool:
    """
    Write a minimal record to Airtable with just two fields:
      - Query
      - AI Response

    The signature intentionally accepts extra positional args so existing calls
    like log_to_airtable(query, text, sources_data, consensus) still work
    without changes elsewhere in the app.
    """
    try:
        api = Api(st.secrets["AIRTABLE_API_KEY"])
        table = api.table(
            st.secrets["AIRTABLE_BASE_ID"],
            st.secrets.get("AIRTABLE_TABLE_ID", "tblj5Tj4ZqxDLZsyJ"),
        )

        # Airtable long text fields handle large strings well; we trim just in case.
        record = {
            "Query": (query or "")[:100000],
            "AI Response": (ai_response or "")[:100000],
        }

        table.create(record)
        return True

    except Exception as e:
        st.error(f"Failed to log to Airtable: {e}")
        return False
