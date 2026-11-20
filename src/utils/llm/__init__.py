"""
LLM call module.

Provides three core APIs:
- call_llm: basic call, returns raw text
- call_llm_json: call and parse as JSON
- call_llm_with_template: call with a template (most common)
"""

from .client import (
    call_llm, 
    call_llm_json, 
    call_llm_with_template, 
    call_llm_with_task_name,
    test_connectivity
)
from .config import LLMMode, get_task_mode
from .exceptions import LLMError, ParseError, ConfigError
from .runtime_mode import is_test_mode_enabled, is_world_test_mode, llm_test_mode_scope

__all__ = [
    "call_llm",
    "call_llm_json", 
    "call_llm_with_template",
    "call_llm_with_task_name",
    "test_connectivity",
    "LLMMode",
    "get_task_mode",
    "LLMError",
    "ParseError",
    "ConfigError",
    "is_test_mode_enabled",
    "is_world_test_mode",
    "llm_test_mode_scope",
]
