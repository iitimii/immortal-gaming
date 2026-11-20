from __future__ import annotations

from collections.abc import Callable

from .config import LLMConfig
from .validation import llm_requires_api_key


def check_llm_profile_connectivity(
    *,
    profile,
    api_key: str,
    fast_api_key: str = "",
    test_connectivity: Callable[..., tuple[bool, str]],
) -> tuple[bool, str]:
    base_url = (profile.base_url or "").strip()
    api_format = (profile.api_format or "openai").strip() or "openai"
    model_name = (profile.model_name or "").strip()
    fast_model_name = (profile.fast_model_name or "").strip()
    use_separate_fast_config = bool(getattr(profile, "use_separate_fast_config", False))
    fast_base_url = (
        (getattr(profile, "fast_base_url", "") or "").strip()
        if use_separate_fast_config else base_url
    )
    fast_api_format = (
        (getattr(profile, "fast_api_format", "openai") or "openai").strip()
        if use_separate_fast_config else api_format
    )
    resolved_fast_api_key = fast_api_key if use_separate_fast_config else api_key

    if not base_url:
        return False, "Incomplete LLM configuration: please enter the Base URL"
    if not model_name:
        return False, "Incomplete LLM configuration: please enter the smart model name"
    if not fast_model_name:
        return False, "Incomplete LLM configuration: please enter the fast model name"
    if not fast_base_url:
        return False, "Incomplete LLM configuration: please enter the fast model Base URL"
    if llm_requires_api_key(base_url=base_url, api_format=api_format) and not api_key:
        return False, "Incomplete LLM configuration: please enter the API Key"

    if llm_requires_api_key(base_url=fast_base_url, api_format=fast_api_format) and not resolved_fast_api_key:
        return False, "Incomplete LLM configuration: please enter the fast model API Key"

    normal_config = LLMConfig(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        api_format=api_format,
    )
    success, error_msg = test_connectivity(config=normal_config)
    if not success:
        return False, f"Smart model connection failed: {error_msg}"

    if (
        fast_model_name == model_name
        and fast_base_url == base_url
        and fast_api_format == api_format
        and resolved_fast_api_key == api_key
    ):
        return True, ""

    fast_config = LLMConfig(
        base_url=fast_base_url,
        api_key=resolved_fast_api_key,
        model_name=fast_model_name,
        api_format=fast_api_format,
    )
    success, error_msg = test_connectivity(config=fast_config)
    if not success:
        return False, f"Fast model connection failed: {error_msg}"

    return True, ""
