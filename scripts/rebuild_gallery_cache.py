#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/rebuild_gallery_cache.py
Rebuilds gallery_cache.json cleanly with get_gallery(force_reload=True).
"""

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.services.gallery_service import get_gallery
import json
import time

app = create_app()
with app.app_context():
    print("Rebuilding gallery cache cleanly...")
    t0 = time.time()
    gallery = get_gallery(force_reload=True)
    t1 = time.time()
    print(f"Gallery built in {t1 - t0:.2f} seconds!")
    
    # Print key statistics
    por_org = gallery.get("📋 Revisión / Por Organizar", {})
    print("\n--- 📋 Revisión / Por Organizar ---")
    for k, v in por_org.items():
        print(f"  {k}: {len(v)} elements")
