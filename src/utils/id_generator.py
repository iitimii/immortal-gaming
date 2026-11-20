"""
Simplified ID generator, replacing UUID4.
"""

import random
import string


def base62_id(length: int = 8) -> str:
    """
    Generate a short base62 ID (digits plus upper/lowercase letters).
    Defaults to 8 characters, much shorter than UUID4's 36.
    """
    charset = string.ascii_letters + string.digits  # 0-9, a-z, A-Z (62 characters)
    return ''.join(random.choices(charset, k=length))


def get_avatar_id() -> str:
    """Default factory for Avatar IDs."""
    return base62_id(8)
