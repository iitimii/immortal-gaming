from __future__ import annotations

from inspect import signature, Parameter
from typing import Callable, Mapping, Any


def filter_kwargs_for_callable(func: Callable[..., Any], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """
    Filter kwargs by the callable's signature, keeping only keyword arguments the target accepts.

    - If the target accepts **kwargs (VAR_KEYWORD), return them unchanged (no filtering needed).
    - Only POSITIONAL_OR_KEYWORD and KEYWORD_ONLY parameter names are kept.
    - "self" is ignored automatically.
    - If the signature is unavailable (e.g. builtins or C extensions), return them unchanged.
    """
    try:
        sig = signature(func)
    except (ValueError, TypeError):
        return dict(kwargs)

    params = sig.parameters
    if any(p.kind == Parameter.VAR_KEYWORD for p in params.values()):
        return dict(kwargs)

    allowed_names = {
        name
        for name, p in params.items()
        if name != "self" and p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
    }
    return {k: v for k, v in kwargs.items() if k in allowed_names}


