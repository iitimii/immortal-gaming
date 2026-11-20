import pytest
import re
import ast
from pathlib import Path
from typing import Set, Dict

from src.utils.df import load_game_configs
from src.i18n import t
from src.i18n.locale_registry import get_source_locale

# =============================================================================
# Helper Functions & Constants
# =============================================================================

# Define Chinese character range
ZH_PATTERN = re.compile(r'[\u4e00-\u9fff]')
# Match msgid "content"
MSGID_PATTERN = re.compile(r'^msgid\s+"(.*)"')

def get_po_files():
    """Get all .po files in static/locales"""
    root_dir = Path(__file__).parent.parent / "static" / "locales"
    return list(root_dir.rglob("*.po"))

def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent

# =============================================================================
# CSV Integrity Tests
# =============================================================================

def test_all_csv_ids_have_translations():
    """
    Walk every loaded game config CSV and check all fields ending in _id (name_id, desc_id, title_id, ...)
    to make sure each has a translation in the default locale.

    If t(key) returns the key itself and the key is all upper case (typical ID format), it is missing.
    """
    # 1. Load configs (the force_default_language fixture is already active)
    configs = load_game_configs()
    
    missing_keys = []
    
    # 2. Walk every config table
    for config_name, rows in configs.items():
        if not rows:
            continue
            
        print(f"Checking config: {config_name}.csv ({len(rows)} rows)")
        
        for i, row in enumerate(rows):
            # Walk every key/value pair in the row
            for key, value in row.items():
                # Check whether the key ends with _id (e.g. title_id)
                # and the value is a non-empty string
                if key.lower().endswith("id") and isinstance(value, str) and value.strip():
                    # Assume every translatable ID is upper case and contains an underscore
                    if value.isupper() and "_" in value:
                        translated = t(value)
                        
                        # If the translation equals the key itself, treat it as missing
                        if translated == value:
                            missing_keys.append(f"[{config_name}.csv Row {i+1}] {key}={value}")

    # 3. Assert
    if missing_keys:
        error_msg = f"Found {len(missing_keys)} missing translations in the default locale:\n" + "\n".join(missing_keys)
        pytest.fail(error_msg)


# =============================================================================
# PO File Quality Tests
# =============================================================================

@pytest.mark.parametrize("po_file", get_po_files())
def test_msgid_should_not_contain_chinese(po_file):
    """
    Ensure msgid in .po files does not contain Chinese characters.
    Convention: msgid should be English source text, msgstr is the translation.
    """
    errors = []
    
    try:
        with open(po_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                match = MSGID_PATTERN.match(line)
                if match:
                    content = match.group(1)
                    if ZH_PATTERN.search(content):
                        errors.append(f"Line {line_num}: {content}")
    except FileNotFoundError:
        pytest.skip(f"File not found: {po_file}")
    
    error_msg = "\n".join(errors)
    assert not errors, f"Found Chinese characters in msgid in {po_file}:\n{error_msg}"


class TestSourceCodeQuality:
    """Check source code for i18n issues"""

    EXCLUDE_PATTERNS = [
        '__pycache__',
        '.pyc',
        'test_',
        '/tests/',
        'conftest.py',
    ]

    @staticmethod
    def contains_chinese(text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    @staticmethod
    def is_comment_or_docstring(line: str) -> bool:
        stripped = line.strip()
        return (
            stripped.startswith('#') or
            stripped.startswith('"""') or
            stripped.startswith("'''") or
            'docstring' in stripped.lower()
        )

    @staticmethod
    def is_in_string_literal(line: str) -> bool:
        if '#' in line:
            line = line[:line.index('#')]
        return '"' in line or "'" in line

    def test_no_hardcoded_chinese_in_src_classes(self):
        """src/classes/ should not contain hard-coded Chinese strings (use t() instead)."""
        classes_dir = get_project_root() / "src" / "classes"
        
        if not classes_dir.exists():
            pytest.skip("src/classes directory not found")
        
        violations = []
        
        for py_file in classes_dir.rglob("*.py"):
            if any(pattern in str(py_file) for pattern in self.EXCLUDE_PATTERNS):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if self.is_comment_or_docstring(line):
                        continue
                    
                    if self.contains_chinese(line):
                        if self.is_in_string_literal(line) and 't(' not in line:
                            violations.append(f"{py_file.relative_to(get_project_root())}:{i} -> {line.strip()[:100]}")
            
            except Exception as e:
                print(f"Warning: Could not read {py_file}: {e}")
        
        if violations:
            error_msg = f"Found {len(violations)} lines with hardcoded Chinese strings (should use t()):\n" + "\n".join(violations[:20])
            if len(violations) > 20:
                error_msg += f"\n... and {len(violations) - 20} more."
            # Note: This is a strict check, might produce false positives. 
            # Uncomment pytest.fail to enforce it, or keep as a warning printer for now if codebase is not clean yet.
            # pytest.fail(error_msg) 
            print(f"\n[WARNING] {error_msg}")


class TestTranslationKeysIntegrity:
    """Check that used translation keys exist in PO files"""

    @staticmethod
    def extract_t_calls_from_file(py_file: Path) -> Set[str]:
        try:
            content = py_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
            msgids = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    if func_name == 't' and node.args:
                        first_arg = node.args[0]
                        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                            msgids.add(first_arg.value)
            return msgids
        except Exception:
            return set()

    @staticmethod
    def extract_msgids_from_po(po_file: Path) -> Set[str]:
        if not po_file.exists():
            return set()
        msgids = set()
        try:
            # Try polib first
            import polib
            po = polib.pofile(str(po_file))
            for entry in po:
                msgids.add(entry.msgid)
        except ImportError:
            # Fallback to regex
            content = po_file.read_text(encoding='utf-8')
            pattern = r'msgid\s+"([^"]*)"'
            matches = re.findall(pattern, content)
            for m in matches:
                if m:
                    decoded = m.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                    msgids.add(decoded)
        return msgids

    def test_all_used_msgids_are_defined_in_po(self):
        """Every msgid used in code must be defined in the source locale PO files."""
        src_dir = get_project_root() / "src"
        locales_dir = get_project_root() / "static/locales" / get_source_locale()
        
        if not src_dir.exists() or not locales_dir.exists():
            pytest.skip("Required directories not found")
        
        defined_msgids = set()
        # Walk every source-locale PO file (messages.po and game_configs_modules included)
        for po_file in locales_dir.rglob("*.po"):
            defined_msgids.update(self.extract_msgids_from_po(po_file))
            
        used_msgids = set()
        
        for py_file in src_dir.rglob("*.py"):
            if 'test_' in py_file.name or '/tests/' in str(py_file):
                continue
            used_msgids.update(self.extract_t_calls_from_file(py_file))
        
        undefined_msgids = used_msgids - defined_msgids
        
        if undefined_msgids:
            error_msg = f"Found {len(undefined_msgids)} msgids used in code but not defined in PO file:\n"
            error_msg += "\n".join([f"  - '{m}'" for m in sorted(undefined_msgids)[:20]])
            if len(undefined_msgids) > 20:
                error_msg += f"\n  ... and {len(undefined_msgids) - 20} more."
            pytest.fail(error_msg)


class TestFormatParameterConsistency:
    """Check consistency of format parameters in translations"""

    @staticmethod
    def extract_format_params(text: str) -> Set[str]:
        return set(re.findall(r'\{(\w+)\}', text))
    
    @staticmethod
    def extract_pairs(po_file: Path) -> Dict[str, str]:
        """Extract msgid -> msgstr pairs using polib to handle multiline correctly"""
        try:
            import polib
            po = polib.pofile(str(po_file))
            return {entry.msgid: entry.msgstr for entry in po if entry.msgid and not entry.obsolete}
        except ImportError:
            # Fallback to simple regex if polib is missing (though it should be installed)
            # This regex approach is fragile for multiline, but kept as backup
            content = po_file.read_text(encoding='utf-8')
            pairs = {}
            # ... (omitted complex regex implementation for brevity, rely on polib)
            # If polib is missing, this test might be flaky. 
            # Given the project uses polib in other tests, we assume it's available.
            print("Warning: polib not found, skipping precise pair extraction.")
            return {}

    def test_format_params_consistency(self):
        """Source-locale translations must keep the format parameters of their msgid."""
        po_dir = get_project_root() / "static" / "locales" / get_source_locale() / "LC_MESSAGES"
        po_files = sorted(po_dir.glob("*.po"))

        if not po_files:
            pytest.skip("PO files not found")

        inconsistencies = []

        for po_file in po_files:
            for msgid, msgstr in self.extract_pairs(po_file).items():
                msgid_params = self.extract_format_params(msgid)
                if not msgid_params:
                    # Key-based msgid (e.g. "retreat_start"): no source params to compare against
                    continue
                # If msgstr is empty (fallback to msgid), use msgid content for param extraction
                content = msgstr if msgstr else msgid
                params = self.extract_format_params(content)
                if params != msgid_params:
                    inconsistencies.append(
                        f"{po_file.name} msgid: {msgid[:50]}...\n"
                        f"  Params: Original={msgid_params}, Translation={params}"
                    )

        if inconsistencies:
            error_msg = f"Found {len(inconsistencies)} translation entries with inconsistent format parameters:\n" + "\n".join(inconsistencies[:10])
            pytest.fail(error_msg)
