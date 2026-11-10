import os
import json
import time
import pickle
import numpy as np
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
    "learning_adaptations": 0,
    "mode": "100% Real-Time Supervision (Todas las fotos)",
    "recent_interventions": []
}

def _load_supervisor_state():
    if SUPERVISOR_LOG_FILE.exists():
        try:
            with open(SUPERVISOR_LOG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                _SUPERVISOR_STATE.update(saved)
        except Exception:
            pass


_load_supervisor_state()


def get_supervisor_status():
    return dict(_SUPERVISOR_STATE)

def save_supervisor_state():
    try:
        SUPERVISOR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SUPERVISOR_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(_SUPERVISOR_STATE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def supervise_and_adapt_decision(path_str, info, centroids, *, learn=True):
    """
    Supervisa cada foto individualmente en tiempo real (100% de cobertura).
    - Degrada asignaciones de margen estrecho a 'Dudoso'.
    - Fusiona clusters redundantes de 'Persona Nueva'.
    - Refuerza suavemente el centroide si la confianza es contundente (>75%).
    """
    fname = os.path.basename(path_str)
    cat = info.get("category", "")
    ident = info.get("identity", "")
    status = info.get("status", "Clasificado")
    faces = info.get("faces", [])
    
    interventions = []
    modified = False

    known_centroids = {k: v for k, v in centroids.items() if not (isinstance(k, tuple) and "Persona Nueva" in str(k[1]))}
    new_person_centroids = {k: v for k, v in centroids.items() if isinstance(k, tuple) and "Persona Nueva" in str(k[1])}

    # 1. Regla de seguridad: Filtrar borderline false positives (<0.64 con margen <0.04)
    if cat in ("Conocidos", "Familia", "YO") and status != "Dudoso":
        for f in faces:
            feat = f.get("feature")
            if not f.get("is_manual") and feat is not None and len(feat) == 128:
                f_vec = np.array(feat, dtype=np.float32)
                f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-10)

                # Calcular distancias a centroides conocidos
                scores_by_identity = {}
                for k_id, k_vec in known_centroids.items():
                    k_norm = k_vec.flatten() / (np.linalg.norm(k_vec) + 1e-10)
                    sim = float(np.dot(f_norm, k_norm))
                    identity = k_id[1] if isinstance(k_id, tuple) else str(k_id)
                    if identity not in scores_by_identity or sim > scores_by_identity[identity][0]:
                        scores_by_identity[identity] = (sim, k_id)
                scores = sorted(scores_by_identity.values(), key=lambda x: x[0], reverse=True)

                if len(scores) >= 2:
                    top1_sim, top1_id = scores[0]
                    top2_sim, top2_id = scores[1]
                    margin = top1_sim - top2_sim

                    clean_top1 = top1_id[1] if isinstance(top1_id, tuple) else str(top1_id)
                    clean_top2 = top2_id[1] if isinstance(top2_id, tuple) else str(top2_id)

                    # Si la similitud está en zona gris (<0.64) y el margen es estrecho (<0.04)
                    if clean_top1 != ident or f.get("identity") != ident:
                        continue
                    if 0.58 <= top1_sim < 0.64 and margin < 0.04:
                        info["category"] = "📋 Revisión / Por Organizar"
                        info["identity"] = clean_top1
                        info["status"] = "Dudoso"
                        f["identity"] = f"? {clean_top1}"
                        f["confidence"] = f"⚠️ Dudoso (Margen {margin:.3f})"
                        modified = True
                        _SUPERVISOR_STATE["downgraded_to_dudoso"] += 1
                        interventions.append({
                            "file": fname,
                            "action": "downgrade_to_doubtful",
                            "reason": f"Margen estrecho ({margin:.3f}) frente a {clean_top2}",
                            "timestamp": time.strftime("%H:%M:%S")
                        })
                        break
                    
                    # 2. Refuerzo adaptativo del centroide (Online Continuous Learning)
                    # Si la detección es inequívoca (>0.75 y margen >0.10)
                    elif learn and top1_sim >= 0.75 and margin >= 0.10 and len(faces) == 1:
                        target_key = top1_id
                        cur_centroid = known_centroids.get(target_key)
                        if cur_centroid is not None:
                            alpha = 0.03 # Refuerzo suave y seguro del 3%
                            cur_c_norm = cur_centroid.flatten() / (np.linalg.norm(cur_centroid) + 1e-10)
                            updated_c = (1.0 - alpha) * cur_c_norm + alpha * f_norm
                            updated_c = updated_c / (np.linalg.norm(updated_c) + 1e-10)
                            centroids[target_key] = updated_c
                            _SUPERVISOR_STATE["learning_adaptations"] += 1

    # 3. Regla Anti-fragmentación de Persona Nueva (fusión con pureza facial estricta >=0.66)
    if "Persona Nueva" in ident and len(faces) == 1:
        for f in faces:
            feat = f.get("feature")
            if not f.get("is_manual") and feat is not None and len(feat) == 128:
                f_vec = np.array(feat, dtype=np.float32)
                f_norm = f_vec / (np.linalg.norm(f_vec) + 1e-10)

                for np_id, np_vec in list(new_person_centroids.items()):
                    np_name = np_id[1] if isinstance(np_id, tuple) else str(np_id)
                    if np_name != ident:
                        np_norm = np_vec.flatten() / (np.linalg.norm(np_vec) + 1e-10)
                        sim = float(np.dot(f_norm, np_norm))
                        if sim >= 0.66 and ident.rpartition("#")[2].isdigit() and np_name.rpartition("#")[2].isdigit():
                            target_name = min(ident, np_name, key=lambda x: int(x.split("#")[-1]) if "#" in x else 9999)
                            if target_name == ident:
                                continue
                            source_name = ident
                            
                            info["identity"] = target_name
                            f["identity"] = target_name
                            modified = True
                            _SUPERVISOR_STATE["clusters_merged"] += 1
                            interventions.append({
                                "file": fname,
                                "action": "merge_new_person",
                                "reason": f"Fusión de {source_name} en {target_name} (similitud {sim:.3f})",
                                "timestamp": time.strftime("%H:%M:%S")
                            })
                            break

    _SUPERVISOR_STATE["total_decisions_audited"] += 1
    _SUPERVISOR_STATE["approved_count"] += int(not interventions)
    if interventions:
        _SUPERVISOR_STATE["recent_interventions"] = (interventions + _SUPERVISOR_STATE["recent_interventions"])[:20]
    _SUPERVISOR_STATE["last_audit_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

    return modified, interventions

def audit_all_photos(limit=None):
    """
    Audita retroactivamente el 100% de las fotos en la base de datos (apple_db).
    """
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

    total_audited = 0
    total_modified = 0
    all_interventions = []

    items = list(apple_db.items())
    if limit:
        items = items[-limit:]

    for path_str, info in items:
        mod, interv = supervise_and_adapt_decision(path_str, info, centroids, learn=False)
        total_audited += 1
        if mod:
            total_modified += 1
        if interv:
            all_interventions.extend(interv)

    if total_modified > 0:
        save_apple_db()
        set_gallery_cache(None)

    save_supervisor_state()
    return {
        "status": "success",
        "total_audited": total_audited,
        "modified_photos": total_modified,
        "interventions_count": len(all_interventions),
        "interventions": all_interventions[:20],
        "elapsed_sec": round(time.time() - t0, 3)
    }

def audit_recent_decisions(n=30):
    """Alias retro-compatible para auditar las últimas n fotos."""
    return audit_all_photos(limit=n)
