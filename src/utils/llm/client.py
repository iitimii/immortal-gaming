"""Core LLM client call logic."""

import json
import urllib.request
import urllib.error
import asyncio
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Optional

from src.config import get_settings_service
from src.run.log import log_llm_call
from src.utils.config import CONFIG
from .config import LLMMode, LLMConfig, get_task_mode
from .parser import parse_json
from .prompt import build_prompt, load_template
from .exceptions import LLMError, ParseError, ProviderCallError, ProviderFailureKind
from .runtime_mode import is_test_mode_enabled
from .test_mode_fallbacks import TestModeLLMUnavailable, resolve_test_mode_task

# Module-level semaphore, lazily created
_SEMAPHORE: Optional[asyncio.Semaphore] = None
_SEMAPHORE_LIMIT: Optional[int] = None
_LLM_FAILURE_HANDLER: Optional[Callable[[str], Awaitable[None] | None]] = None

_QUOTA_ERROR_CODES = {
    "insufficient_quota",
    "quota_exceeded",
    "insufficient_balance",
    "balance_not_enough",
    "balance_not_sufficient",
    "billing_not_active",
    "payment_required",
}
_RATE_LIMIT_ERROR_CODES = {
    "rate_limit_exceeded",
    "rate_limited",
    "too_many_requests",
}
_BILLING_KEYWORDS = (
    "insufficient quota",
    "insufficient_quota",
    "quota exceeded",
    "insufficient balance",
    "insufficient_balance",
    "payment required",
    "billing details",
    "free token quota",
    # Chinese-language providers' "insufficient balance/quota" phrases, kept as escapes.
    "\u4f59\u989d\u4e0d\u8db3",
    "\u914d\u989d\u4e0d\u8db3",
    "\u989d\u5ea6\u4e0d\u8db3",
    "\u989d\u5ea6\u4e0d\u591f",
)
_BILLING_KEYWORD_HTTP_STATUSES = {400, 402, 403, 429}


class LLMFailureKind(str, Enum):
    CONFIG_REQUIRED = "config_required"
    RATE_LIMITED = "rate_limited"
    TEMPORARY_NETWORK = "temporary_network"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LLMFailureInfo:
    kind: LLMFailureKind
    user_message: str
    http_status: int | None = None
    provider_message: str = ""

    @property
    def is_config_required(self) -> bool:
        return self.kind in {LLMFailureKind.CONFIG_REQUIRED, LLMFailureKind.RATE_LIMITED}


def register_llm_failure_handler(handler: Callable[[str], Awaitable[None] | None] | None) -> None:
    global _LLM_FAILURE_HANDLER
    _LLM_FAILURE_HANDLER = handler


async def _notify_config_required(error_message: str) -> None:
    if _LLM_FAILURE_HANDLER is None:
        return

    result = _LLM_FAILURE_HANDLER(error_message)
    if asyncio.iscoroutine(result):
        await result


def _extract_provider_message(body_str: str) -> str:
    provider_msg = body_str
    try:
        body_json = json.loads(body_str)
        if isinstance(body_json, dict):
            if "error" in body_json and isinstance(body_json["error"], dict):
                provider_msg = body_json["error"].get("message") or body_json["error"].get("msg") or body_str
            elif body_json.get("type") == "error" and "error" in body_json:
                err_obj = body_json["error"]
                if isinstance(err_obj, dict):
                    provider_msg = err_obj.get("message") or body_str
            elif "message" in body_json:
                provider_msg = body_json["message"]
    except Exception:
        pass

    if len(provider_msg) > 200:
        provider_msg = provider_msg[:200] + "..."
    return provider_msg


def _load_provider_body(body_str: str) -> dict | None:
    try:
        body_json = json.loads(body_str)
    except Exception:
        return None
    if isinstance(body_json, dict):
        return body_json
    return None


def _normalize_error_token(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _collect_provider_error_codes(body_str: str) -> set[str]:
    body_json = _load_provider_body(body_str)
    if body_json is None:
        return set()

    values: set[str] = set()

    def collect_from_dict(data: dict) -> None:
        for key in ("code", "type", "error_code", "err_code"):
            value = data.get(key)
            if value is not None:
                values.add(_normalize_error_token(value))

    collect_from_dict(body_json)
    error_obj = body_json.get("error")
    if isinstance(error_obj, dict):
        collect_from_dict(error_obj)

    return {value for value in values if value}


def _has_billing_or_quota_signal(body_str: str, provider_msg: str, http_status: int | None) -> bool:
    error_codes = _collect_provider_error_codes(body_str)
    if error_codes & _QUOTA_ERROR_CODES:
        return True
    if http_status == 429 and error_codes & _RATE_LIMIT_ERROR_CODES:
        return True
    if http_status not in _BILLING_KEYWORD_HTTP_STATUSES:
        return False

    haystack = f"{body_str}\n{provider_msg}".lower()
    return any(keyword in haystack for keyword in _BILLING_KEYWORDS)


def _build_quota_message(
    *,
    code_str: str,
    provider_msg: str,
    base_url: str = "",
) -> str:
    if "longcat.chat" in base_url.lower():
        return (
            f"LongCat API Key has run out of free token quota. Request a quota increase on the LongCat usage page or use a different key. "
            f"Provider response: {provider_msg}"
        )
    return (
        f"Insufficient quota or billing restricted ({code_str}). Check your account balance, token quota, or provider usage limits. "
        f"Provider response: {provider_msg}"
    )


def classify_llm_error(error_raw: str | ProviderCallError, *, base_url: str = "") -> LLMFailureInfo:
    if isinstance(error_raw, ProviderCallError):
        if error_raw.kind is ProviderFailureKind.NETWORK:
            return LLMFailureInfo(
                kind=LLMFailureKind.TEMPORARY_NETWORK,
                user_message=f"Network connection failed. Check that the Base URL is reachable and your local proxy settings. (Underlying error: {error_raw.message})",
                provider_message=error_raw.message,
            )
        if error_raw.kind is ProviderFailureKind.HTTP:
            return _classify_http_error(
                str(error_raw.status_code or ""),
                error_raw.response_body,
                base_url=base_url,
            )
        return LLMFailureInfo(
            kind=LLMFailureKind.UNKNOWN,
            user_message=f"Unknown error: {error_raw.message}",
            provider_message=error_raw.message,
        )

    if error_raw.startswith("NETWORK_ERROR::"):
        reason = error_raw.split("::", 1)[1]
        return LLMFailureInfo(
            kind=LLMFailureKind.TEMPORARY_NETWORK,
            user_message=f"Network connection failed. Check that the Base URL is reachable and your local proxy settings. (Underlying error: {reason})",
            provider_message=reason,
        )

    if error_raw.startswith("HTTP_"):
        parts = error_raw.split("::", 1)
        code_str = parts[0].replace("HTTP_", "")
        body_str = parts[1] if len(parts) > 1 else ""
        return _classify_http_error(code_str, body_str, base_url=base_url)

    return LLMFailureInfo(
        kind=LLMFailureKind.UNKNOWN,
        user_message=f"Unknown error: {error_raw}",
        provider_message=error_raw,
    )


def _classify_http_error(code_str: str, body_str: str, *, base_url: str) -> LLMFailureInfo:
    provider_msg = _extract_provider_message(body_str)
    try:
        http_status = int(code_str)
    except ValueError:
        http_status = None

    if _has_billing_or_quota_signal(body_str, provider_msg, http_status):
        return LLMFailureInfo(
            kind=LLMFailureKind.RATE_LIMITED,
            http_status=http_status,
            provider_message=provider_msg,
            user_message=_build_quota_message(
                code_str=code_str,
                provider_msg=provider_msg,
                base_url=base_url,
            ),
        )
    if code_str == "401":
            return LLMFailureInfo(
                kind=LLMFailureKind.CONFIG_REQUIRED,
                http_status=http_status,
                provider_message=provider_msg,
                user_message=f"Authentication failed (401). Check that the API Key is correct. Provider response: {provider_msg}",
            )
    if code_str == "403":
            return LLMFailureInfo(
                kind=LLMFailureKind.CONFIG_REQUIRED,
                http_status=http_status,
                provider_message=provider_msg,
                user_message=f"Access denied (403). The model may not be authorized or your IP may be restricted. Provider response: {provider_msg}",
            )
    if code_str == "404":
            return LLMFailureInfo(
                kind=LLMFailureKind.CONFIG_REQUIRED,
                http_status=http_status,
                provider_message=provider_msg,
                user_message=f"Service not found (404). Check that the Base URL is correct (it usually ends with /v1) and that the model name exists. Provider response: {provider_msg}",
            )
    if code_str == "429":
            return LLMFailureInfo(
                kind=LLMFailureKind.RATE_LIMITED,
                http_status=http_status,
                provider_message=provider_msg,
                user_message=f"Quota exceeded or too many requests (429). Check your account balance. Provider response: {provider_msg}",
            )
    if code_str.startswith("5"):
            return LLMFailureInfo(
                kind=LLMFailureKind.PROVIDER_UNAVAILABLE,
                http_status=http_status,
                provider_message=provider_msg,
                user_message=f"Provider internal error ({code_str}). Please try again later. Provider response: {provider_msg}",
            )
    return LLMFailureInfo(
        kind=LLMFailureKind.UNKNOWN,
        http_status=http_status,
        provider_message=provider_msg,
        user_message=f"Request failed ({code_str}). Provider response: {provider_msg}",
    )


def _get_semaphore() -> asyncio.Semaphore:
    global _SEMAPHORE, _SEMAPHORE_LIMIT
    if _SEMAPHORE is None:
        limit = get_settings_service().get_llm_runtime_config()[0].max_concurrent_requests
        _SEMAPHORE = asyncio.Semaphore(limit)
        _SEMAPHORE_LIMIT = limit
        return _SEMAPHORE

    limit = get_settings_service().get_llm_runtime_config()[0].max_concurrent_requests
    if _SEMAPHORE_LIMIT != limit:
        _SEMAPHORE = asyncio.Semaphore(limit)
        _SEMAPHORE_LIMIT = limit
    return _SEMAPHORE


def _call_openai(config: LLMConfig, prompt: str) -> str:
    """Call via plain urllib (OpenAI-compatible API)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
        "User-Agent": "CultivationWorldSimulator/1.0"
    }
    data = {
        "model": config.model_name,
        "messages": [{"role": "user", "content": prompt}]
    }

    url = config.base_url
    if not url:
        raise ValueError("Base URL is required for requests mode (OpenAI Compatible)")

    # Normalize the URL so it points to chat/completions
    if "chat/completions" not in url:
        url = url.rstrip("/")
        url = f"{url}/chat/completions"

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise ProviderCallError(
            ProviderFailureKind.HTTP,
            f"HTTP {e.code}: {_extract_provider_message(error_body)}",
            status_code=e.code,
            response_body=error_body,
            provider_message=_extract_provider_message(error_body),
            cause=e,
        ) from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        reason = getattr(e, "reason", str(e))
        raise ProviderCallError(ProviderFailureKind.NETWORK, str(reason), cause=e) from e
    except Exception as e:
        if isinstance(e, ProviderCallError):
            raise
        raise ProviderCallError(ProviderFailureKind.UNKNOWN, str(e), cause=e) from e


def _call_anthropic(config: LLMConfig, prompt: str) -> str:
    """Call via plain urllib (native Anthropic API)."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.api_key,
        "anthropic-version": "2023-06-01",
        "User-Agent": "CultivationWorldSimulator/1.0"
    }
    data = {
        "model": config.model_name,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }

    url = config.base_url
    if not url:
        raise ValueError("Base URL is required for Anthropic API")

    # Normalize the URL so it points to /v1/messages
    if "/messages" not in url:
        url = url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        url = f"{url}/messages"

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        # Anthropic response format: {"content": [{"type": "text", "text": "..."}]}
        for block in result.get("content", []):
            if block.get("type") == "text":
                return block["text"]
        raise Exception("UNKNOWN_ERROR::No text content found in the Anthropic response")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise ProviderCallError(
            ProviderFailureKind.HTTP,
            f"HTTP {e.code}: {_extract_provider_message(error_body)}",
            status_code=e.code,
            response_body=error_body,
            provider_message=_extract_provider_message(error_body),
            cause=e,
        ) from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        reason = getattr(e, "reason", str(e))
        raise ProviderCallError(ProviderFailureKind.NETWORK, str(reason), cause=e) from e
    except Exception as e:
        if isinstance(e, ProviderCallError):
            raise
        raise ProviderCallError(ProviderFailureKind.UNKNOWN, str(e), cause=e) from e


def _call_with_requests(config: LLMConfig, prompt: str) -> str:
    """Dispatch to the implementation matching api_format."""
    if config.api_format == "anthropic":
        return _call_anthropic(config, prompt)
    return _call_openai(config, prompt)


async def call_llm(prompt: str, mode: LLMMode = LLMMode.NORMAL) -> str:
    """
    Basic LLM call with automatic concurrency control.
    Calls the OpenAI-compatible API directly via urllib.
    """
    if is_test_mode_enabled():
        raise TestModeLLMUnavailable("raw_llm_call")

    config = LLMConfig.from_mode(mode)
    semaphore = _get_semaphore()
    
    try:
        async with semaphore:
            result = await asyncio.to_thread(_call_with_requests, config, prompt)
    except Exception as exc:
        failure = classify_llm_error(exc if isinstance(exc, ProviderCallError) else str(exc), base_url=config.base_url)
        if failure.is_config_required:
            await _notify_config_required(failure.user_message)
        raise
    
    log_llm_call(config.model_name, prompt, result)
    return result


async def call_llm_json(
    prompt: str,
    mode: LLMMode = LLMMode.NORMAL,
    max_retries: int | None = None
) -> dict:
    """Call the LLM and parse the result as JSON, with retries."""
    if max_retries is None:
        max_retries = int(getattr(CONFIG.ai, "max_parse_retries", 0))
    
    last_error: ParseError | None = None
    for attempt in range(max_retries + 1):
        response = await call_llm(prompt, mode)
        try:
            return parse_json(response)
        except ParseError as e:
            last_error = e
            if attempt < max_retries:
                continue
            raise LLMError(f"Parsing failed (after {max_retries} retries)", cause=last_error) from last_error
    
    # This should never be reached, but satisfies type checker.
    raise LLMError("Unknown error")


async def call_llm_with_template(
    template_path: Path | str,
    infos: dict,
    mode: LLMMode = LLMMode.NORMAL,
    max_retries: int | None = None
) -> dict:
    """Call the LLM with a template."""
    template = load_template(template_path)
    prompt = build_prompt(template, infos)
    return await call_llm_json(prompt, mode, max_retries)


async def call_llm_with_task_name(
    task_name: str,
    template_path: Path | str,
    infos: dict,
    max_retries: int | None = None
) -> dict:
    """
    Automatically pick the LLM mode by task name and call it.
    
    Args:
        task_name: task name, used to look up its mode in config.yml
        template_path: template path
        infos: template parameters
        max_retries: maximum number of retries
        
    Returns:
        dict: JSON data returned by the LLM
    """
    if is_test_mode_enabled():
        return resolve_test_mode_task(task_name, infos)

    mode = get_task_mode(task_name)
    
    return await call_llm_with_template(template_path, infos, mode, max_retries)


def test_connectivity(mode: LLMMode = LLMMode.NORMAL, config: Optional[LLMConfig] = None) -> tuple[bool, str]:
    """
    Test LLM service connectivity (synchronous).
    
    Args:
        mode: mode to test (NORMAL/FAST); ignored if config is given
        config: test with this config directly
        
    Returns:
        tuple[bool, str]: (success, error message); the error message is empty on success
    """
    try:
        if config is None:
            config = LLMConfig.from_mode(mode)
            
        _call_with_requests(config, "Hello, this is a connectivity test. Please reply 'OK'.")
        return True, ""
    except Exception as e:
        return False, classify_llm_error(
            e if isinstance(e, ProviderCallError) else str(e),
            base_url=config.base_url,
        ).user_message
