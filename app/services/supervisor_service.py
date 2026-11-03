import os
import json
import time
import pickle
import numpy as np
from pathlib import Path
from app.globals import APP_DIR, set_gallery_cache
from app.services.apple_service import load_apple_db, save_apple_db

SUPERVISOR_LOG_FILE = APP_DIR / "scratch" / "supervisor_audit_log.json"
CENTROIDS_FILE = APP_DIR / "centroids.pkl"

_SUPERVISOR_STATE = {
    "active": True,
    "last_audit_time": None,
    "total_decisions_audited": 0,
    "approved_count": 0,
    "downgraded_to_dudoso": 0,
    "clusters_merged": 0,
    "recent_interventions": []
}

def get_supervisor_status():
    if SUPERVISOR_LOG_FILE.exists():
        try:
            with open(SUPERVISOR_LOG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                _SUPERVISOR_STATE.update(saved)
        except Exception:
            pass
    return dict(_SUPERVISOR_STATE)

def _save_supervisor_state():
    try:
        SUPERVISOR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SUPERVISOR_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(_SUPERVISOR_STATE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def audit_recent_decisions(n=30):
    """Audita las últimas decisiones del clasificador para corregir o validar en tiempo real."""
    t0 = time.time()
    apple_db = load_apple_db()
    if not apple_db:
        return {"status": "empty", "audited": 0}

    centroids = {}
    if CENTROIDS_FILE.exists():
        try:
            with open(CENTROIDS_FILE, "rb") as cf:
                centroids = pickle.load(cf)
        except Exception:
            centroids = {}

    known_centroids = {k: v for k, v in centroids.items() if not (isinstance(k, tuple) and "Persona Nueva" in str(k[1]))}
    new_person_centroids = {k: v for k, v in centroids.items() if isinstance(k, tuple) and "Persona Nueva" in str(k[1])}

    db_items = list(apple_db.items())
    sample_to_audit = db_items[-n:] if len(db_items) >= n else db_items

    interventions = []
    approved = 0
    downgraded = 0
    merged = 0
    db_modified = False

    for path_str, info in sample_to_audit:
        fname = os.path.basename(path_str)
        cat = info.get("category", "")
        ident = info.get("identity", "")
        status = info.get("status", "Clasificado")
        faces = info.get("faces", [])

        # Regla 1: Validar asignaciones a personas conocidas con margen estrecho (<0.04)
        if cat in ("Conocidos", "Familia", "YO") and status != "Dudoso":
            for f in faces:
                feat = f.get("feature")
                if feat and len(feat) == 128:
                    f_vec = np.array(feat, dtype=np.float32)
                    f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-10)

                    # Obtener top 2 similitudes
                    scores = []
                    for k_id, k_vec in known_centroids.items():
                        k_norm = k_vec.flatten() / (np.linalg.norm(k_vec) + 1e-10)
                        sim = float(np.dot(f_norm, k_norm))
                        scores.append((sim, k_id))
                    scores.sort(key=lambda x: x[0], reverse=True)

                    if len(scores) >= 2:
                        top1_sim, top1_id = scores[0]
                        top2_sim, top2_id = scores[1]
                        margin = top1_sim - top2_sim

                        # Si similitud es frontera (<0.64) y el margen es menor a 0.04, degradar a Dudoso para seguridad
                        if 0.58 <= top1_sim < 0.64 and margin < 0.04:
                            info["category"] = "📋 Revisión / Por Organizar"
                            info["identity"] = top1_id[1] if isinstance(top1_id, tuple) else str(top1_id)
                            info["status"] = "Dudoso"
                            f["identity"] = f"? {info['identity']}"
                            f["confidence"] = f"⚠️ Dudoso (Margen {margin:.3f})"
                            db_modified = True
                            downgraded += 1
                            interventions.append({
                                "file": fname,
                                "action": "downgrade_to_doubtful",
                                "reason": f"Margen estrecho ({margin:.3f}) entre {top1_id} y {top2_id}",
                                "timestamp": time.strftime("%H:%M:%S")
                            })
                            break
        
        # Regla 2: Anti-fragmentación de Persona Nueva (fusión de clusters idénticos >=0.54)
        if "Persona Nueva" in ident:
            for f in faces:
                feat = f.get("feature")
                if feat and len(feat) == 128:
                    f_vec = np.array(feat, dtype=np.float32)
                    f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-10)

                    for np_id, np_vec in list(new_person_centroids.items()):
                        np_name = np_id[1] if isinstance(np_id, tuple) else str(np_id)
                        if np_name != ident:
                            np_norm = np_vec.flatten() / (np.linalg.norm(np_vec) + 1e-10)
                            sim = float(np.dot(f_norm, np_norm))
                            if sim >= 0.54:
                                # Fusionar hacia el número menor para mantener orden canónico
                                target_name = min(ident, np_name, key=lambda x: int(x.split("#")[-1]) if "#" in x else 9999)
                                source_name = ident if target_name != ident else np_name
                                
                                info["identity"] = target_name
                                f["identity"] = target_name
                                db_modified = True
                                merged += 1
                                interventions.append({
                                    "file": fname,
                                    "action": "merge_new_person",
                                    "reason": f"Fusión de {source_name} en {target_name} (similitud {sim:.3f})",
                                    "timestamp": time.strftime("%H:%M:%S")
                                })
                                break

        approved += 1

    if db_modified:
        save_apple_db()
        set_gallery_cache(None)

    _SUPERVISOR_STATE["last_audit_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _SUPERVISOR_STATE["total_decisions_audited"] += len(sample_to_audit)
    _SUPERVISOR_STATE["approved_count"] += approved
    _SUPERVISOR_STATE["downgraded_to_dudoso"] += downgraded
    _SUPERVISOR_STATE["clusters_merged"] += merged
    if interventions:
        _SUPERVISOR_STATE["recent_interventions"] = (interventions + _SUPERVISOR_STATE["recent_interventions"])[:20]
    _save_supervisor_state()

    return {
        "status": "success",
        "audited_in_pass": len(sample_to_audit),
        "downgraded": downgraded,
        "merged": merged,
        "interventions": interventions,
        "elapsed_sec": round(time.time() - t0, 3)
    }
