import os

# Test discovery must not start cache migration or classification workers.
os.environ["SMART_GALLERY_BACKGROUND_TASKS"] = "0"

import unittest
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def run_suite():
    print("=" * 60)
    print("[TEST] EJECUTANDO BATERIA COMPLETA DE TESTS (TDD GALLERY ORGANIZER)")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(Path(__file__).parent), pattern="test_*.py")
    
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"[STATS] RESULTADOS FINALES: {result.testsRun} tests ejecutados en {elapsed:.2f}s")
    if result.wasSuccessful():
        print("[OK] 100% EXITO - TODOS LOS TESTS PASARON")
        print("[INFO] Las pruebas no sustituyen las copias de seguridad.")
    else:
        print(f"[FAIL] FALLOS: {len(result.failures)} | ERRORES: {len(result.errors)}")
    print("=" * 60)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_suite())