"""Prompt handling."""

from pathlib import Path
from src.utils.strings import intentify_prompt_infos


def build_prompt(template: str, infos: dict) -> str:
    """
    Build a prompt from a template.
    
    Args:
        template: prompt template
        infos: dict of values to fill in
        
    Returns:
        str: the built prompt
    """
    processed = intentify_prompt_infos(infos)
    return template.format(**processed)


def load_template(path: Path | str) -> str:
    """
    Load a template file.
    
    Args:
        path: template file path
        
    Returns:
        str: template contents
    """
    path = Path(path)
    return path.read_text(encoding="utf-8")

