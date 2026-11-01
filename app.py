import os
# -*- coding: utf-8 -*-
"""
app.py
Punto de entrada de la aplicación con revisión de sintaxis integrada (Husky-style).
"""
import sys
from pathlib import Path

import subprocess

def check_js_syntax():
    js_files = [
        Path(__file__).resolve().parent / "static" / "app.js",
        Path(__file__).resolve().parent / "static" / "dist" / "app.js"
    ]
    cache_file = Path(__file__).resolve().parent / ".js_lint_mtime"
    cached_mtimes = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r") as fp:
                for line in fp:
                    if "=" in line:
                        p, m = line.strip().split("=", 1)
                        cached_mtimes[p] = float(m)
        except Exception:
            pass

    updated_mtimes = dict(cached_mtimes)
    for js_file in js_files:
        if not js_file.exists():
            continue
        cur_mtime = js_file.stat().st_mtime
        if cached_mtimes.get(str(js_file)) == cur_mtime:
            continue
        try:
            res = subprocess.run(["node", "-c", str(js_file)], capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                print(f"[LINT] Error de sintaxis JS en {js_file.name}: {res.stderr.strip()}")
                sys.exit(1)
            updated_mtimes[str(js_file)] = cur_mtime
        except Exception:
            pass

    try:
        with open(cache_file, "w") as fp:
            for p, m in updated_mtimes.items():
                fp.write(f"{p}={m}\n")
    except Exception:
        pass

# Ejecutar chequeo antes de importar la app
check_js_syntax()

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=host, port=port, debug=False, threaded=True)
