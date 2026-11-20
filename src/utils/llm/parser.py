"""JSON parsing logic."""

import re
import json5
from .exceptions import ParseError


def parse_json(text: str) -> dict:
    """
    Parse JSON, extracting from markdown code blocks or parsing directly.
    """
    text = (text or '').strip()
    if not text:
        return {}
    
    # Strategy 1: try extracting from Markdown code blocks
    # Prefer json/json5 blocks; blocks without a language are tried too
    blocks = _extract_code_blocks(text)
    for lang, content in blocks:
        if not lang or lang in ("json", "json5"):
            try:
                obj = json5.loads(content)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
    
    # Strategy 2: try parsing the whole text
    # Sometimes the LLM outputs raw JSON without markdown
    try:
        obj = json5.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    
    # Failed
    raise ParseError(
        "Unable to parse JSON: no valid JSON object or code block found",
        raw_text=text[:500]
    )


def _extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract markdown code blocks."""
    pattern = re.compile(r"```([^\n`]*)\n([\s\S]*?)```", re.DOTALL)
    blocks = []
    for lang, content in pattern.findall(text):
        blocks.append((lang.strip().lower(), content.strip()))
    return blocks
