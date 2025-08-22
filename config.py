from dataclasses import dataclass
import os

@dataclass
class Flags:
    # Feature flags
    ENABLE_WEB_SEARCH: bool = bool(os.getenv("ENABLE_WEB_SEARCH", "0") == "1")
    LOGGING_ENABLED: bool = bool(os.getenv("LOGGING_ENABLED", "1") == "1")

    # Models
    OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    OPENAI_WHISPER_MODEL: str = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Retrieval
    TOP_K: int = int(os.getenv("TOP_K", 5))
    SIM_THRESHOLD: float = float(os.getenv("SIM_THRESHOLD", 0.60))  # cosine-ish

    # Consensus
    OUTLIER_DELTA: float = float(os.getenv("OUTLIER_DELTA", 1.5))

FLAGS = Flags()