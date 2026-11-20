import pytest
import os
import re
from pathlib import Path
from collections import Counter

from src.i18n.locale_registry import get_locale_codes, get_source_locale

# Try importing polib; tests are skipped if it is unavailable
try:
    import polib
    HAS_POLIB = True
except ImportError:
    HAS_POLIB = False

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def extract_msgids(filepath: Path) -> list[str]:
    if not HAS_POLIB:
        return []
    po = polib.pofile(str(filepath))
    # We ignore empty msgids as they are usually header entries in PO files
    return [entry.msgid for entry in po if entry.msgid]

def extract_po_pairs(filepath: Path) -> dict[str, str]:
    if not HAS_POLIB or not filepath.exists():
        return {}
    po = polib.pofile(str(filepath))
    return {entry.msgid: entry.msgstr for entry in po if entry.msgid and not entry.obsolete}

def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text or ""))

class TestBackendLocales:
    @pytest.mark.skipif(not HAS_POLIB, reason="polib not installed")
    def test_no_duplicate_msgids(self):
        """Check that no merged messages.po contains duplicate msgids."""
        root = get_project_root()
        locales = get_locale_codes()
        
        errors = []
        for loc in locales:
            po_file = root / "static" / "locales" / loc / "LC_MESSAGES" / "messages.po"
            if not po_file.exists():
                errors.append(f"File not found: {po_file}")
                continue
                
            msgids = extract_msgids(po_file)
            counter = Counter(msgids)
            duplicates = {msgid: count for msgid, count in counter.items() if count > 1}
            
            if duplicates:
                errors.append(f"Found duplicates in {loc}/messages.po:")
                for msgid, count in sorted(duplicates.items()):
                    errors.append(f"  - '{msgid}' appears {count} times")
                    
        if errors:
            pytest.fail("\n".join(errors))

    @pytest.mark.skipif(not HAS_POLIB, reason="polib not installed")
    def test_po_modules_match_merged_catalogs(self):
        """
        The split module .po files are the source of truth; the merged
        LC_MESSAGES catalogs must contain exactly the same msgid set.
        """
        root = get_project_root()
        domain_dirs = {"messages": "modules", "game_configs": "game_configs_modules"}

        errors = []
        for loc in get_locale_codes():
            for domain, module_dir in domain_dirs.items():
                dir_path = root / "static" / "locales" / loc / module_dir
                module_keys: set[str] = set()
                for po_file in dir_path.glob("*.po"):
                    module_keys.update(extract_msgids(po_file))

                merged_file = root / "static" / "locales" / loc / "LC_MESSAGES" / f"{domain}.po"
                if not merged_file.exists():
                    errors.append(f"File not found: {merged_file}")
                    continue
                merged_keys = set(extract_msgids(merged_file))

                missing = module_keys - merged_keys
                extra = merged_keys - module_keys
                if missing:
                    errors.append(
                        f"[{loc}/{domain}] merged catalog is missing {len(missing)} module msgids:\n"
                        + "\n".join(f"  - {m}" for m in sorted(missing)[:15])
                    )
                if extra:
                    errors.append(
                        f"[{loc}/{domain}] merged catalog has {len(extra)} msgids not in modules:\n"
                        + "\n".join(f"  + {m}" for m in sorted(extra)[:15])
                    )

        if errors:
            pytest.fail("Backend PO module/merged validation FAILED:\n" + "\n".join(errors))

    def test_template_files_consistency(self):
        """Check that every enabled locale has the same template file set as the source locale."""
        root = get_project_root()
        locales = get_locale_codes()
        base_loc = get_source_locale()
        base_template_dir = root / "static" / "locales" / base_loc / "templates"

        assert base_template_dir.exists(), f"Base template directory not found: {base_template_dir}"

        base_templates = {
            path.name
            for path in base_template_dir.glob("*.txt")
        }
        errors = []

        for loc in locales:
            target_template_dir = root / "static" / "locales" / loc / "templates"
            if not target_template_dir.exists():
                errors.append(f"Template directory not found: {target_template_dir}")
                continue

            target_templates = {path.name for path in target_template_dir.glob("*.txt")}
            missing = sorted(base_templates - target_templates)
            if missing:
                errors.append(
                    f"[{loc}] missing template files present in {base_loc}:\n"
                    + "\n".join(f"  - {name}" for name in missing)
                )

        if errors:
            pytest.fail("Backend template validation FAILED:\n" + "\n".join(errors))

    @pytest.mark.skipif(not HAS_POLIB, reason="polib not installed")
    def test_locale_catalogs_contain_no_cjk_text(self):
        """
        The project is English-only: no msgid or msgstr in any enabled locale
        may contain CJK characters (e.g. leftover untranslated copies).
        """
        root = get_project_root()

        errors = []
        for loc in get_locale_codes():
            for po_file in sorted((root / "static" / "locales" / loc).rglob("*.po")):
                for entry in polib.pofile(str(po_file)):
                    if contains_cjk(entry.msgid) or contains_cjk(entry.msgstr):
                        errors.append(
                            f"[{po_file.relative_to(root)}] {entry.msgid!r} -> {entry.msgstr!r}"
                        )

        if errors:
            pytest.fail("Locale catalogs contain CJK text:\n" + "\n".join(errors[:50]))
