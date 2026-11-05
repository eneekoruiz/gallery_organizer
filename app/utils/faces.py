import numpy as np
from app.globals import FOTOS_DIR, RESULTADOS_DIR

def sanitize_display_name(name):
    if not name: return ""
    clean = str(name).replace("_rejected", "").replace("_solitario", "").replace("_compania", "")
    if clean.startswith("? "):
        clean = clean[2:]
    elif clean.startswith("?"):
        clean = clean[1:].strip()
    return clean.strip()

_IDENTITIES_CACHE = None
_IDENTITIES_CACHE_TS = 0

def clear_identities_cache():
    global _IDENTITIES_CACHE, _IDENTITIES_CACHE_TS
    _IDENTITIES_CACHE = None
    _IDENTITIES_CACHE_TS = 0

def get_all_identities():
    global _IDENTITIES_CACHE, _IDENTITIES_CACHE_TS
    import time
    now = time.time()
    # Cache for 120s in memory unless explicitly invalidated
    if _IDENTITIES_CACHE is not None and (now - _IDENTITIES_CACHE_TS) < 120:
        return _IDENTITIES_CACHE

    import os
    identities = []
    seen = set()
    for base_dir in [FOTOS_DIR, RESULTADOS_DIR]:
        if base_dir.exists():
            for cat in base_dir.iterdir():
                if not cat.is_dir() or cat.name in ["Ignorar", "temp", "cache", ".thumbnails", "_Dudosos"]:
                    continue
                for ident in cat.iterdir():
                    if ident.is_dir():
                        has_files = False
                        try:
                            with os.scandir(str(ident)) as it:
                                for entry in it:
                                    if entry.is_file() and os.path.splitext(entry.name)[1].lower() in {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}:
                                        has_files = True
                                        break
                        except Exception:
                            pass
                        
                        if not has_files:
                            try:
                                os.rmdir(str(ident))
                            except Exception:
                                pass
                            continue
                            
                        c_name = cat.name
                        i_name = ident.name
                        if i_name.startswith("Falso_Positivo") or i_name.startswith("Ignorar_"):
                            continue
                        if i_name.upper() == 'YO':
                            c_name = 'YO'
                            i_name = 'YO'
                        elif c_name == 'Recuerdos' or i_name == 'Recuerdos':
                            c_name = 'Recuerdos'
                            i_name = 'Recuerdos'
                        elif i_name.lower().startswith('persona') or i_name.lower().startswith('desconocid'):
                            c_name = 'Personas Sin Nombre'
                        key = f"{c_name}/{i_name}"
                        if key not in seen:
                            identities.append({"categoria": c_name, "identidad": i_name})
                            seen.add(key)
    res = sorted(identities, key=lambda x: x['identidad'])
    _IDENTITIES_CACHE = res
    _IDENTITIES_CACHE_TS = now
    return res

def get_cosine_similarity(feat1, feat2):
    f1 = np.squeeze(feat1)
    f2 = np.squeeze(feat2)
    return np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))

def iou(boxA, boxB):
    bA = [float(x) for x in boxA]
    bB = [float(x) for x in boxB]
    xA = max(bA[0], bB[0])
    yA = max(bA[1], bB[1])
    xB = min(bA[0] + bA[2], bB[0] + bB[2])
    yB = min(bA[1] + bA[3], bB[1] + bB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0: return 0.0
    boxAArea = bA[2] * bA[3]
    boxBArea = bB[2] * bB[3]
    return interArea / float(boxAArea + boxBArea - interArea)
