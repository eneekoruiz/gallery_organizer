from pathlib import Path
import os
import shutil
import gc
import time
from app.globals import PENDING_DELETIONS_FILE

def is_icloud_file(filepath):
    if not filepath:
        return False
    s = str(filepath).replace('\\', '/').lower()
    return 'icloud photos' in s or ('pictures/icloud' in s) or ('apple' in s and 'icloud' in s)

def process_pending_deletions():
    if not PENDING_DELETIONS_FILE.exists(): return
    try:
        with open(PENDING_DELETIONS_FILE, "r") as f:
            paths = f.read().splitlines()
        remaining = []
        for p in paths:
            if not p.strip(): continue
            if is_icloud_file(p):
                # Never delete iCloud files via pending deletions
                continue
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    remaining.append(p)
        with open(PENDING_DELETIONS_FILE, "w") as f:
            for r in remaining:
                f.write(f"{r}\n")
    except Exception as e:
        print(f"Error procesando pending deletions: {e}")

def safe_move_file(src, dst):
    """Move a file without replacing an existing destination.
    If target exists and differs, generates collision-free name (stem_1.ext).
    """
    src, dst = os.fspath(src), os.fspath(dst)
    if not os.path.isfile(src):
        return False
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    if os.path.exists(dst):
        try:
            if os.path.samefile(src, dst):
                if src != dst and not is_icloud_file(src):
                    os.unlink(src)
                return True
        except (OSError, ValueError):
            pass
        p_dst = Path(dst)
        counter = 1
        while p_dst.exists():
            p_dst = p_dst.parent / f"{p_dst.stem}_{counter}{p_dst.suffix}"
            counter += 1
        dst = str(p_dst)

    # CRITICAL ZERO-LOSS ICLOUD SHIELD:
    # Files residing in iCloud Photos must NEVER be unlinked or moved out of iCloud!
    # Moving/unlinking causes iCloud for Windows to detect deletion and send items to Trash.
    # We copy them non-destructively so the iCloud source stays intact.
    if is_icloud_file(src):
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            print(f"[iCloud Safety] Error copying {src} -> {dst}: {e}")
            return False

    try:
        os.link(src, dst)
    except (FileExistsError, OSError):
        with open(src, 'rb') as source:
            with open(dst, 'xb') as destination:
                try:
                    shutil.copyfileobj(source, destination)
                    destination.flush()
                    os.fsync(destination.fileno())
                except BaseException:
                    destination.close()
                    if os.path.exists(dst):
                        os.unlink(dst)
                    raise
        shutil.copystat(src, dst)
    os.unlink(src)
    return True


def safe_remove_file(filepath):
    f_str = str(filepath)
    if not os.path.exists(f_str):
        return False
    if is_icloud_file(f_str):
        print(f"[iCloud Protection] Intercepted safe_remove_file for iCloud path: {f_str} (file preserved)")
        return True
    # 1. Fast path: Direct removal
    try:
        os.remove(f_str)
        return True
    except FileNotFoundError:
        return False
    except (PermissionError, OSError):
        pass

    # 2. Retry loop for locked files
    for attempt in range(4):
        time.sleep(0.04 * (attempt + 1))
        gc.collect()
        try:
            os.remove(f_str)
            return True
        except FileNotFoundError:
            return False
        except (PermissionError, OSError):
            pass
    return False
