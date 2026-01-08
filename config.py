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
    ANTHROPIC_OPUS_MODEL: str = os.getenv("ANTHROPIC_OPUS_MODEL", "claude-opus-4-5-20251101")
    ANTHROPIC_SONNET_MODEL: str = os.getenv("ANTHROPIC_SONNET_MODEL", "claude-sonnet-4-5-20250929")
    ANTHROPIC_MODEL: str = ANTHROPIC_SONNET_MODEL # Legacy default

    # Retrieval
    TOP_K: int = int(os.getenv("TOP_K", 25))
    SIM_THRESHOLD: float = float(os.getenv("SIM_THRESHOLD", 0.60))  # cosine-ish

    # Consensus
    OUTLIER_DELTA: float = float(os.getenv("OUTLIER_DELTA", 1.5))

FLAGS = Flags()