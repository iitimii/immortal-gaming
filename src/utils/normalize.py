"""
Name normalization utilities.

Shared helpers for stripping brackets and extra annotations from names.
"""

def remove_parentheses(name: str, recursive: bool = False) -> str:
    """
    Generic bracket removal.
    
    Args:
        name: original string
        recursive: whether to remove all brackets recursively (nested brackets)
    """
    s = str(name).strip()
    brackets = [
        # Full-width variants are kept as escapes so LLM output using them still normalizes.
        ("(", ")"), ("\uff08", "\uff09"),
        ("[", "]"), ("\u3010", "\u3011"),
        ("\u300c", "\u300d"), ("\u300e", "\u300f"),
        ("<", ">"), ("\u300a", "\u300b")
    ]
    
    while True:
        found = False
        for left, right in brackets:
            # Find the outermost opening bracket
            start = s.find(left)
            if start != -1:
                # Removal is usually about dropping annotations and keeping the main name.
                # To stay consistent with the original region logic (e.g.
                # "Forest (Ancient Pine (Core Formation))" -> "Forest"), truncate at the
                # first opening bracket. This covers the common "Name (Info)" case.
                s = s[:start].strip()
                found = True
                break
        
        if not recursive or not found:
            break
            
    return s.strip()

def normalize_name(name: str) -> str:
    """
    Most general normalization: remove brackets and their contents.
    """
    return remove_parentheses(name)

# --- Aliases / specializations for specific business logic ---

def normalize_avatar_name(name: str) -> str:
    return remove_parentheses(name)

def normalize_region_name(name: str) -> str:
    # Region names may contain nested brackets. With the truncation strategy, recursion
    # adds nothing, since the first pass already truncates. Current naming conventions put
    # bracketed notes at the end, so truncating is safe.
    return remove_parentheses(name)

def normalize_goods_name(name: str) -> str:
    """Goods names additionally strip a trailing ' -'."""
    s = remove_parentheses(name)
    return s.rstrip(" -").strip()

def normalize_weapon_type(name: str) -> str:
    s = str(name).strip()
    for suffix in [" type", " weapon"]:
        if s.lower().endswith(suffix):
            s = s[:-len(suffix)].strip()
    return s
