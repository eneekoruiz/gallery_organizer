#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_frontend.py
Clean Code Modular Build Pipeline for SmartGallery AI.
Assembles, validates, and optimizes all modules in static/js/modules/ into static/dist/app.js and static/app.js.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
MODULES_DIR = STATIC_DIR / "js" / "modules"
DIST_DIR = STATIC_DIR / "dist"
DIST_APP = DIST_DIR / "app.js"
STATIC_APP = STATIC_DIR / "app.js"

MODULE_ORDER = [
    "00_init.js",
    "01_state.js",
    "02_navigation.js",
    "03_grid.js",
    "04_lightbox.js",
    "05_faces.js",
    "06_selection.js",
    "07_modals.js",
    "08_tasks.js",
    "09_exports.js",
]

def format_clean_lines(lines):
    """Format and eliminate redundant empty lines while keeping clean spacing."""
    formatted = []
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            if formatted and formatted[-1].strip().endswith(('{', '(', '[')):
                continue
            if i + 1 < len(lines) and lines[i+1].strip().startswith(('}', ')', ']', 'else', 'catch', 'finally', 'case', 'default:')):
                continue
            if formatted and not formatted[-1].strip():
                continue
            if formatted and i + 1 < len(lines):
                prev_s = formatted[-1].strip()
                next_s = lines[i+1].strip()
                if (prev_s.startswith(('let ', 'const ', 'var ')) and next_s.startswith(('let ', 'const ', 'var '))) and not prev_s.endswith('{'):
                    continue
        formatted.append(l.rstrip() + "\n")
    return formatted

def build():
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    MODULES_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""/**
 * ====================================================================
 * SmartGallery AI - Production Modular Bundle (Clean Code Architecture)
 * Generated: {timestamp}
 * Architecture: Decoupled Modules in static/js/modules/
 * ====================================================================
 */
"""
    bundle_chunks = [header]

    for mod_name in MODULE_ORDER:
        mod_path = MODULES_DIR / mod_name
        if not mod_path.exists():
            print(f"[BUILD ERROR] Module file missing: {mod_path}", file=sys.stderr)
            sys.exit(1)
        with open(mod_path, "r", encoding="utf-8") as mf:
            lines = mf.readlines()
        cleaned = format_clean_lines(lines)
        # Also rewrite the modular file cleaned in-place
        with open(mod_path, "w", encoding="utf-8") as mf:
            mf.writelines(cleaned)

        bundle_chunks.append(f"\n// ====================================================================\n")
        bundle_chunks.append(f"// MODULE: {mod_name}\n")
        bundle_chunks.append(f"// ====================================================================\n\n")
        bundle_chunks.append("".join(cleaned))
        bundle_chunks.append("\n")

    full_bundle = "".join(bundle_chunks)

    # Write to static/dist/app.js
    with open(DIST_APP, "w", encoding="utf-8") as f:
        f.write(full_bundle)

    # Keep static/app.js in sync
    with open(STATIC_APP, "w", encoding="utf-8") as f:
        f.write(full_bundle)

    total_lines = len(full_bundle.splitlines())
    file_size_kb = len(full_bundle.encode("utf-8")) / 1024

    print(f"[BUILD SUCCESS] Bundled {len(MODULE_ORDER)} modules.")
    print(f"  -> {DIST_APP.relative_to(BASE_DIR)} ({total_lines} lines, {file_size_kb:.1f} KB)")
    print(f"  -> {STATIC_APP.relative_to(BASE_DIR)} ({total_lines} lines, {file_size_kb:.1f} KB)")

    # Validate syntax with Node.js
    res = subprocess.run(["node", "-c", str(DIST_APP)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[BUILD ERROR] Syntax check failed on {DIST_APP.name}:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  -> Node.js syntax check passed with 0 errors!")

if __name__ == "__main__":
    build()
