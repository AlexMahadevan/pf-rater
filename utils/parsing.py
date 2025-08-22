# ===========================
# File: utils/parsing.py
# ===========================
from typing import Any, Dict, List


def extract_response_text(response: Any) -> str:
    """Works with Anthropic SDK message objects to extract text content."""
    text = ""
    content = getattr(response, "content", [])
    for item in content:
        if getattr(item, "type", None) == "text":
            text += getattr(item, "text", "")
        elif isinstance(item, dict) and item.get("type") == "text":
            text += item.get("text", "")
    return text.strip()