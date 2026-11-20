"""LLM configuration management."""

from enum import Enum
from dataclasses import dataclass

from src.config import get_settings_service
from src.utils.config import CONFIG

class LLMMode(str, Enum):
    """LLM call mode."""
    NORMAL = "normal"
    FAST = "fast"
    DEFAULT = "default"


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration dataclass."""
    model_name: str
    api_key: str
    base_url: str
    api_format: str = "openai"  # "openai" or "anthropic"

    @classmethod
    def from_mode(cls, mode: LLMMode) -> 'LLMConfig':
        """
        Create a config for the given mode, read from CONFIG.

        Args:
            mode: LLM call mode

        Returns:
            LLMConfig: config object
        """
        profile, api_key = get_settings_service().get_llm_runtime_config()
        base_url = profile.base_url
        api_key_value = api_key
        # Profiles saved before api_format was introduced use the OpenAI-compatible API.
        api_format = getattr(profile, "api_format", "openai") or "openai"

        # Pick the model by mode
        model_name = ""
        if mode == LLMMode.FAST:
            model_name = profile.fast_model_name
            if profile.use_separate_fast_config:
                base_url = profile.fast_base_url
                api_key_value = get_settings_service().get_secrets().fast_api_key
                api_format = getattr(profile, "fast_api_format", "openai") or "openai"
        else:
            # NORMAL or DEFAULT fallback
            model_name = profile.model_name

        return cls(
            model_name=model_name,
            api_key=api_key_value,
            base_url=base_url,
            api_format=api_format,
        )


def get_task_mode(task_name: str) -> LLMMode:
    """
    Get the LLM mode for a task name.
    """
    # Read the global mode from CONFIG
    profile, _ = get_settings_service().get_llm_runtime_config()
    global_mode = (profile.mode or "default").lower()
    
    if global_mode == "normal":
        return LLMMode.NORMAL
    elif global_mode == "fast":
        return LLMMode.FAST
    
    # Default mode: look up task_name in the fine-grained config
    # If default_modes is configured, return the mode for the task name
    default_modes = getattr(CONFIG.llm, "default_modes", {})
    if default_modes and task_name in default_modes:
        task_mode = default_modes[task_name].lower()
        if task_mode == "fast":
            return LLMMode.FAST
        else:
            return LLMMode.NORMAL
    
    # Not configured: default to NORMAL
    return LLMMode.NORMAL
