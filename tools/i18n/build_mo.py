#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile PO files into MO files, merging modular PO sources.

Usage:
    python tools/i18n/build_mo.py

What it does:
    1. Scans the locale directories under static/locales
    2. Merges modular sources:
       - modules/ -> LC_MESSAGES/messages.po
       - game_configs_modules/ -> LC_MESSAGES/game_configs.po
    3. Compiles the matching .mo files
    4. Compiles any other standalone .po files in LC_MESSAGES
"""

import sys
import shutil
from pathlib import Path

def compile_domain_modules(lang_dir: Path, source_folder: str, domain_name: str) -> bool:
    """
    Merge the .po files under source_folder into LC_MESSAGES/{domain_name}.po.
    
    Args:
        lang_dir: Root directory of the locale
        source_folder: Module source folder name (e.g. "modules")
        domain_name: Target domain name (e.g. "messages" -> messages.po)
        
    Returns:
        bool: True on success (or when there is nothing to do)
    """
    try:
        import polib
    except ImportError:
        print("[ERROR] polib is not installed. Run: pip install polib")
        return False
        
    modules_dir = lang_dir / source_folder
    lc_messages_dir = lang_dir / "LC_MESSAGES"
    lc_messages_dir.mkdir(parents=True, exist_ok=True)
    
    target_po_path = lc_messages_dir / f"{domain_name}.po"
    target_mo_path = lc_messages_dir / f"{domain_name}.mo"
    
    # 1. Merge from the module directory when it exists
    if modules_dir.exists() and list(modules_dir.glob("*.po")):
        print(f"  [merge] {source_folder}/ -> {domain_name}.po")
        
        merged_po = polib.POFile()
        module_files = sorted(list(modules_dir.glob("*.po")))
        
        # Keep the metadata of the first module file
        if module_files:
            try:
                first_po = polib.pofile(str(module_files[0]))
                merged_po.metadata = first_po.metadata
            except:
                pass
                
        # Merge all entries
        count = 0
        for po_file in module_files:
            try:
                po = polib.pofile(str(po_file))
                for entry in po:
                    merged_po.append(entry)
                count += 1
            except Exception as e:
                print(f"    [warn] Failed to read {po_file.name}: {e}")
                
        print(f"    - Merged {count} files, {len(merged_po)} entries")
        
        # Save PO
        merged_po.save(str(target_po_path))
        
        # Compile MO
        merged_po.save_as_mofile(str(target_mo_path))
        print(f"    - Wrote: {target_mo_path.name}")
        return True
        
    # 2. Without a module directory, compile an existing target PO file (legacy mode)
    elif target_po_path.exists():
        print(f"  [compile] {domain_name}.po (no module sources)")
        try:
            po = polib.pofile(str(target_po_path))
            po.save_as_mofile(str(target_mo_path))
            return True
        except Exception as e:
            print(f"    [error] {e}")
            return False
            
    return True  # Nothing to do is not an error

def process_language(lang_dir: Path) -> bool:
    """Run all build tasks for a single locale directory."""
    
    # Tasks: (source folder, target domain name)
    tasks = [
        ("modules", "messages"),
        ("game_configs_modules", "game_configs")
    ]
    
    # Track processed domains to avoid compiling them twice
    processed_domains = set()
    
    success = True
    
    # 1. Run the module merge tasks
    for source_folder, domain_name in tasks:
        if compile_domain_modules(lang_dir, source_folder, domain_name):
            processed_domains.add(domain_name)
        else:
            success = False
            
    # 2. Compile any remaining standalone PO files
    lc_messages_dir = lang_dir / "LC_MESSAGES"
    if lc_messages_dir.exists():
        for po_file in lc_messages_dir.glob("*.po"):
            domain = po_file.stem
            if domain in processed_domains:
                continue
                
            print(f"  [compile] {po_file.name} (standalone file)")
            try:
                import polib
                po = polib.pofile(str(po_file))
                po.save_as_mofile(str(po_file.with_suffix('.mo')))
            except Exception as e:
                print(f"    [error] {e}")
                
    return success

def main():
    print("="*60)
    print("Building i18n files (Module -> PO -> MO)")
    print("="*60)
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    i18n_dir = project_root / "static" / "locales"
    
    if not i18n_dir.exists():
        print(f"[ERROR] i18n directory not found: {i18n_dir}")
        sys.exit(1)
    
    all_success = True
    for lang_dir in i18n_dir.iterdir():
        if not lang_dir.is_dir() or lang_dir.name == "templates":
            continue
            
        print(f"\nProcessing locale: {lang_dir.name}")
        if not process_language(lang_dir):
            all_success = False
            
    print("-" * 60)
    if all_success:
        print("\n[OK] All locales built")
        return 0
    else:
        print("\n[FAIL] Errors occurred during the build")
        return 1

if __name__ == "__main__":
    sys.exit(main())
