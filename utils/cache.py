import functools
from typing import Any, Callable
import hashlib


def stable_key(*parts: Any) -> str:
    b = "::".join(str(p) for p in parts).encode()
    return hashlib.sha256(b).hexdigest()


def memoize(func: Callable) -> Callable:
    cache = {}
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = stable_key(func.__name__, args, sorted(kwargs.items()))
        if key in cache:
            return cache[key]
        res = func(*args, **kwargs)
        cache[key] = res
        return res
    return wrapper
