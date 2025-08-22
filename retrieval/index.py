import streamlit as st
import faiss
import pandas as pd
import os
from typing import Tuple

@st.cache_resource(show_spinner=False)
def load_index_and_meta() -> Tuple[faiss.Index, pd.DataFrame]:
    """Load FAISS index and metadata from the local data directory.
    Looks for files at: ./data/factcheck_index.faiss and ./data/factcheck_metadata.json
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(base_dir, "..", "data"))

    index_path = os.path.join(data_dir, "factcheck_index.faiss")
    meta_path = os.path.join(data_dir, "factcheck_metadata.json")

    index = faiss.read_index(index_path)
    metadata = pd.read_json(meta_path)
    return index, metadata
