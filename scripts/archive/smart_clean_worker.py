import os, json, sys, pickle
from pathlib import Path

# Run deep auto classification
try:
    from deep_auto_classify_all import run_deep_classify
    run_deep_classify(threshold=0.65)
except Exception as e:
    with open("smart_clean_status.json", "w", encoding="utf-8") as f:
        json.dump({"status": f"Error: {e}", "progress": -1}, f)
