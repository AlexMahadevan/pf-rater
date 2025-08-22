import re

POLITIFACT_MAP = {
    "true": 5,
    "mostly true": 4,
    "half true": 3,
    "half-true": 3,
    "mostly false": 2,
    "false": 1,
    "pants on fire": 0,
}

GENERIC_MAP = {
    "accurate": 5,
    "correct": 5,
    "supported": 4,
    "mixture": 3,
    "mixed": 3,
    "partly false": 3,
    "unproven": 3,
    "missing context": 3,
    "misleading": 2,
    "incorrect": 1,
    "unsupported": 1,
    "no evidence": 1,
    "fake": 1,
}

PUBLISHER_WEIGHTS = {
    # simple, transparent weights you can tune per outlet
    "PolitiFact": 1.2,
}


def normalize_rating_text(rating: str) -> str:
    if rating is None:
        return ""
    rating = rating.lower().strip()
    rating = re.sub(r"[!?.]", "", rating)
    return rating


def standardize_rating(rating: str) -> int | None:
    r = normalize_rating_text(rating)
    for k, v in {**POLITIFACT_MAP, **GENERIC_MAP}.items():
        if k in r:
            return v
    return None


