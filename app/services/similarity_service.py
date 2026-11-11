# -*- coding: utf-8 -*-
"""
app/services/similarity_service.py
Servicio de sugerencias de fusion basado en similitud de centroides.
"""
import numpy as np
from flask import jsonify, request

_suggestions_cache = None
_suggestions_cache_key = None

def get_cosine_sim(a, b):
    try:
        a = np.array(a, dtype=np.float32).flatten()
        b = np.array(b, dtype=np.float32).flatten()
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        return 0.0

def extract_centroid(data):
    if data is None:
        return None
    if isinstance(data, dict):
        for key in ("centroid", "feature", "embedding"):
            c = data.get(key)
            if c is not None:
                break
        if c is not None:
            return np.array(c, dtype=np.float32).flatten()
    if isinstance(data, (list, np.ndarray)):
        arr = np.array(data, dtype=np.float32).flatten()
        if arr.size > 10:
            return arr
    return None

def find_sample_for_identity(gallery, identity_name):
    if not gallery or not identity_name:
        return None, 0
    ident_l = identity_name.lower().strip()
    for cat, idents in gallery.items():
        if cat == '__smart_album__': continue
        for iname, items in idents.items():
            if iname.lower().strip() == ident_l:
                if items:
                    for item in items:
                        p = item.get('path')
                        if p:
                            return p, len(items)
    return None, 0

def api_suggest_merges():
    global _suggestions_cache, _suggestions_cache_key
    from app.globals import known_faces, get_gallery_cache
    threshold_known = float(request.args.get("threshold", 0.38))
    threshold_new   = float(request.args.get("threshold_new", 0.45))
    force           = request.args.get("force", "false").lower() == "true"
    gallery = get_gallery_cache()
    if gallery is None:
        from app.routes.api_gallery import get_gallery
        get_gallery()
        gallery = get_gallery_cache() or {}
        
    cache_key = id(gallery)
    if not force and _suggestions_cache is not None and _suggestions_cache_key == cache_key:
        return jsonify(_suggestions_cache)
    if not known_faces:
        return jsonify({"suggestions": [], "msg": "known_faces vacio"})
    known_centroids   = {}
    persona_centroids = {}
    for name, data in known_faces.items():
        vec = extract_centroid(data)
        if vec is None:
            continue
        name_l = str(name).lower()
        if "persona nueva" in name_l or "persona #" in name_l or "persona_nueva" in name_l:
            persona_centroids[name] = vec
        else:
            if name in ("Falso_Positivo", "Ignorar_Irrelevante", "Sin_Rostro"):
                continue
            known_centroids[name] = vec
    suggestions = []
    for pname, pvec in persona_centroids.items():
        best_sim  = 0.0
        best_name = None
        for kname, kvec in known_centroids.items():
            sim = get_cosine_sim(pvec, kvec)
            if sim > best_sim:
                best_sim  = sim
                best_name = kname
        if best_sim >= threshold_known and best_name:
            src_avatar, src_cnt = find_sample_for_identity(gallery, pname)
            tgt_avatar, tgt_cnt = find_sample_for_identity(gallery, best_name)
            suggestions.append({
                "type":          "persona_nueva_to_known",
                "source":        pname,
                "target":        best_name,
                "similarity":    round(best_sim, 4),
                "label":         f"{pname} => {best_name}",
                "confidence":    "alta" if best_sim >= 0.52 else "media",
                "source_avatar": src_avatar,
                "target_avatar": tgt_avatar,
                "source_count":  src_cnt,
                "target_count":  tgt_cnt
            })
    # Se omiten sugerencias persona_nueva a persona_nueva: la IA solo debe sugerir fusionar con personas confirmadas
    suggestions.sort(key=lambda x: x["similarity"], reverse=True)
    suggestions = suggestions[:40]
    result = {
        "suggestions": suggestions,
        "total": len(suggestions),
        "personas_nuevas_count": len(persona_centroids),
        "known_count": len(known_centroids)
    }
    _suggestions_cache = result
    _suggestions_cache_key = cache_key
    return jsonify(result)

def api_face_top_matches():
    import os
    from app.globals import known_faces, faces_cache
    data = request.json or {}
    path = data.get("path", "")
    face_idx = int(data.get("face_index", 0))
    if not path or not os.path.exists(path):
        return jsonify({"matches": []})
    cached_faces = faces_cache.get(path, [])
    feature = None
    if face_idx < len(cached_faces):
        f = cached_faces[face_idx]
        raw = f.get("feature")
        if raw is not None:
            try:
                feature = np.array(raw, dtype=np.float32).flatten()
            except Exception:
                feature = None
    if feature is None:
        return jsonify({"matches": [], "msg": "No embedding disponible"})
    matches = []
    for name, kdata in known_faces.items():
        if name in ("Falso_Positivo", "Ignorar_Irrelevante", "Sin_Rostro"):
            continue
        kvec = extract_centroid(kdata)
        if kvec is None:
            continue
        sim = get_cosine_sim(feature, kvec)
        if sim > 0.25:
            matches.append({"identity": name, "similarity": round(sim, 4)})
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return jsonify({"matches": matches[:5]})
