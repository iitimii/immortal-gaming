def to_json_str_with_intent(data, unescape_newlines: bool = True) -> str:
    """
    Convert a Python object into a formatted JSON string for filling LLM prompt templates.

    Args:
        data: any JSON-serializable object (dict, list, etc.).
        unescape_newlines: whether to turn '\\n' in the JSON into real newlines; defaults to True.

    Returns:
        An indented JSON string with non-ASCII text kept as-is (not escaped to \\uXXXX).

    Note:
        The returned string is safe to use with str.format(), since format() does not recursively parse substituted content.
    """
    import json
    s = json.dumps(data, ensure_ascii=False, indent=2)
    if unescape_newlines:
        s = s.replace("\\n", "\n")
    return s


def intentify_prompt_infos(infos: dict) -> dict:
    processed: dict = dict(infos or {})
    if "avatar_infos" in processed:
        processed["avatar_infos"] = to_json_str_with_intent(processed["avatar_infos"])
    if "world_info" in processed:
        processed["world_info"] = to_json_str_with_intent(processed["world_info"])
    if "general_action_infos" in processed:
        processed["general_action_infos"] = to_json_str_with_intent(processed["general_action_infos"])
    if "expanded_info" in processed:
        processed["expanded_info"] = to_json_str_with_intent(processed["expanded_info"])
    return processed

