from pathlib import Path

def read_txt(path: Path) -> str:
    """
    Read a UTF-8 text file.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()