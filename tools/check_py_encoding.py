#!/usr/bin/env python3
"""Scan all .py files for encoding problems: BOM, non-UTF-8, mismatched coding declarations, suspicious Unicode, etc."""
from pathlib import Path
import re
import sys

# Suspicious characters: BOM, zero-width characters, replacement characters, stray BOMs, etc.
SUSPICIOUS_UNICODE = [
    ("BOM", "\ufeff"),
    ("ZERO WIDTH SPACE", "\u200b"),
    ("ZERO WIDTH NO-BREAK SPACE", "\u2060"),  # actually WORD JOINER
]
WORD_JOINER = "\u2060"
REPLACEMENT_CHAR = "\ufffd"
ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")


def check_file(path: Path) -> list[str]:
    issues = []
    raw = path.read_bytes()

    # 1. BOM detection
    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append("Contains a UTF-8 BOM (removal recommended)")

    # Strip the BOM before decoding for the remaining checks
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        issues.append(f"Not UTF-8 or contains invalid bytes: {e}")
        return issues

    lines = text.splitlines()
    if not lines:
        return issues

    # 2. Coding declaration check (first two lines only)
    coding_re = re.compile(r"#\s*-\*-\s*coding\s*[:=]\s*([\w\-]+)\s*-\*-")
    declared_encoding = None
    for line in lines[:2]:
        m = coding_re.search(line)
        if m:
            declared_encoding = m.group(1).strip().lower()
            if declared_encoding not in ("utf-8", "utf8"):
                issues.append(f"Declared encoding is {declared_encoding} (not utf-8)")
            break

    # 3. Suspicious Unicode characters
    for i, line in enumerate(lines, 1):
        if REPLACEMENT_CHAR in line:
            issues.append(f"Line {i} contains replacement character U+FFFD")
        if WORD_JOINER in line:
            issues.append(f"Line {i} contains word joiner U+2060")
        if "\u200b" in line or "\u200c" in line or "\u200d" in line:
            issues.append(f"Line {i} contains zero-width characters")
        if "\ufeff" in line and not (i == 1 and line.startswith("\ufeff")):
            issues.append(f"Line {i} contains a BOM character")

    # 4. Mixed line endings (informational only)
    if b"\r\n" in raw and b"\n" in raw and raw.count(b"\r\n") < raw.count(b"\n"):
        issues.append("Mixed line endings (CRLF and LF)")

    return issues


def main():
    root = Path(__file__).resolve().parent.parent
    py_files = sorted(root.rglob("*.py"))
    # Exclude venv / .venv, etc.
    py_files = [p for p in py_files if ".venv" not in p.parts and "venv" not in p.parts]
    total = 0
    with_issues = 0
    for path in py_files:
        total += 1
        issues = check_file(path)
        if issues:
            with_issues += 1
            rel = path.relative_to(root)
            print(f"{rel}")
            for i in issues:
                print(f"  - {i}")
            print()
    print(f"Scanned {total} .py files; {with_issues} have encoding-related issues.")
    return 1 if with_issues else 0


if __name__ == "__main__":
    sys.exit(main())
