"""LLM-related exception definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LLMError(Exception):
    """Base class for LLM-related errors."""
    
    def __init__(self, message: str, *, cause: Exception | None = None, **context):
        super().__init__(message)
        self.cause = cause
        self.context = context


class ParseError(LLMError):
    """JSON parsing failed."""
    
    def __init__(self, message: str, *, raw_text: str = ""):
        super().__init__(message, raw_text=raw_text)
        self.raw_text = raw_text


class ConfigError(LLMError):
    """Configuration error."""
    pass


class ProviderFailureKind(str, Enum):
    """Transport-level failures before an LLM response can be consumed."""

    HTTP = "http"
    NETWORK = "network"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass
class ProviderCallError(Exception):
    """Structured provider failure retained across the transport boundary."""

    kind: ProviderFailureKind
    message: str
    status_code: int | None = None
    response_body: str = ""
    provider_message: str = ""
    cause: Exception | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

