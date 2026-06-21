"""
ui/tab_people.py — Gestión de Personas y Fusión de Clústeres
Interfaz al estilo Immich para corregir y fusionar rostros duplicados con estética premium.
"""

from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

from core.database import DatabaseManager


def _get_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


def render_people_management(db: DatabaseManager) -> None:
    # ── CSS PREMIUM ────────────────────────────────────────────────────────
    st.markdown(
        """
        <style>
        .people-header { margin-bottom: 18px; }
        .people-title { margin: 0; font-size: 28px; font-weight: 700; color: #e2e8f0; font-family: 'Inter', sans-serif; }
        .people-subtitle { color: #94a3b8; margin: 4px 0 0; font-size: 14px; }
        
        /* Face Cards */
        .face-card {
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            aspect-ratio: 1/1;
            background: #1e293b;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid transparent;
            margin-bottom: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease;
        }
        .face-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        }
        .face-card img { width: 100%; height: 100%; object-fit: cover; }
        .face-card-selected {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
        }
        .face-label {
            position: absolute; bottom: 0; left: 0; right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
            color: white; padding: 20px 10px 8px; font-size: 13px;
            font-weight: 600; text-align: center; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis;
        }
        
        /* Cluster Stacks */
        .cluster-stack {
            position: relative; width: 100%; aspect-ratio: 1/1;
            margin-bottom: 8px; transition: all 0.2s ease;
        }
        .cluster-stack:hover { transform: translateY(-4px); }
        .stack-img {
            position: absolute; width: 80%; height: 80%;
            border-radius: 12px; object-fit: cover;
            border: 2px solid #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .stack-img-1 { top: 0; left: 0; z-index: 1; opacity: 0.6; }
        .stack-img-2 { top: 10%; left: 10%; z-index: 2; opacity: 0.8; }
        .stack-img-3 { top: 20%; left: 20%; z-index: 3; }
        
        .cluster-badge {
            position: absolute; bottom: 8px; right: 8px; background: #3b82f6;
            color: white; border-radius: 999px; padding: 4px 10px;
            font-size: 12px; font-weight: bold; z-index: 4;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="people-header">
            <h3 class="people-title">👥 Gestión de Personas</h3>
            <p class="people-subtitle">Combina identidades duplicadas o fusiona clústeres IA. Selecciona varias tarjetas para activar el panel de fusión inteligente.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_known, tab_clusters = st.tabs(
        [
            "👥 Identidades Verificadas",
            "🪄 Clústeres IA (DBSCAN)",
        ]
    )

    with tab_known:
        _render_known_people(db)

    with tab_clusters:
        _render_unverified_clusters(db)


def _render_known_people(db: DatabaseManager) -> None:
    people = db.get_known_faces_with_crops()

    if not people:
        st.markdown(
            """
            <div style="text-align: center; padding: 60px 20px; background: #1e293b; border-radius: 16px; margin-top: 20px; border: 1px dashed #334155;">
                <div style="font-size: 48px; margin-bottom: 16px;">👻</div>
                <h4 style="color: #cbd5e1; margin: 0;">Aún no hay identidades</h4>
                <p style="color: #94a3b8; font-size: 14px;">Clasifica rostros en la pestaña Triaje para empezar a crear perfiles.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if "selected_people" not in st.session_state:
        st.session_state.selected_people = set()

    cols_per_row = 6
    rows = [people[i : i + cols_per_row] for i in range(0, len(people), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for i, person in enumerate(row):
            pid = person["id"]
            name = person["name"]
            crop_path = person["face_crop_path"]
            
            with cols[i]:
                is_selected = pid in st.session_state.selected_people
                sel_class = "face-card-selected" if is_selected else ""
                
                if crop_path and Path(crop_path).exists():
                    b64 = _get_b64(crop_path)
                    img_html = f'<img src="data:image/jpeg;base64,{b64}">'
                else:
                    img_html = '<div style="font-size: 40px; color: #475569;">👤</div>'
                
                st.markdown(
                    f"""
                    <div class="face-card {sel_class}">
                        {img_html}
                        <div class="face-label">{name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                changed = st.checkbox(
                    f"Selec. {name}",
                    value=is_selected,
                    key=f"chk_p_{pid}",
                    label_visibility="collapsed"
                )
                
                if changed != is_selected:
                    if changed:
                        st.session_state.selected_people.add(pid)
                    else:
                        st.session_state.selected_people.discard(pid)
                    st.rerun()

    selected_ids = list(st.session_state.selected_people)
    if len(selected_ids) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_merge_panel(db, people, selected_ids, is_cluster=False)


def _render_unverified_clusters(db: DatabaseManager) -> None:
    clusters = db.get_clusters_with_samples(limit_per_cluster=3)

    if not clusters:
        st.markdown(
            """
            <div style="text-align: center; padding: 60px 20px; background: #1e293b; border-radius: 16px; margin-top: 20px; border: 1px dashed #334155;">
                <div style="font-size: 48px; margin-bottom: 16px;">✨</div>
                <h4 style="color: #cbd5e1; margin: 0;">No hay clústeres IA</h4>
                <p style="color: #94a3b8; font-size: 14px;">Ejecuta el Agrupamiento en la pestaña Triaje para encontrar caras similares.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if "selected_clusters" not in st.session_state:
        st.session_state.selected_clusters = set()

    cols_per_row = 6
    rows = [clusters[i : i + cols_per_row] for i in range(0, len(clusters), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for i, cl in enumerate(row):
            cid = cl["cluster_id"]
            count = cl["count"]
            samples = cl["samples"]
            
            with cols[i]:
                is_selected = cid in st.session_state.selected_clusters
                sel_style = "border: 2px solid #3b82f6; transform: scale(0.95);" if is_selected else ""
                
                stack_html = ""
                for j, s in enumerate(samples[:3]):
                    path = s["face_crop_path"]
                    if path and Path(path).exists():
                        b64 = _get_b64(path)
                        stack_html += f'<img src="data:image/jpeg;base64,{b64}" class="stack-img stack-img-{j+1}">'
                
                if not stack_html:
                    stack_html = '<div class="stack-img stack-img-3" style="background:#334155; display:flex; align-items:center; justify-content:center; font-size:32px;">👤</div>'

                st.markdown(
                    f"""
                    <div class="cluster-stack" style="{sel_style}">
                        {stack_html}
                        <div class="cluster-badge">+{count}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Checkbox con ID del cluster
                changed = st.checkbox(
                    f"Grupo #{cid}",
                    value=is_selected,
                    key=f"chk_c_{cid}"
                )
                
                if changed != is_selected:
                    if changed:
                        st.session_state.selected_clusters.add(cid)
                    else:
                        st.session_state.selected_clusters.discard(cid)
                    st.rerun()

    selected_cids = list(st.session_state.selected_clusters)
    if len(selected_cids) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_merge_panel(db, clusters, selected_cids, is_cluster=True)


def _render_merge_panel(db: DatabaseManager, items: list[dict], selected_ids: list[int], is_cluster: bool) -> None:
    st.divider()
    st.markdown("### 🧬 Visualizador de Fusión")
    
    if is_cluster:
        options = {i["cluster_id"]: f"Grupo #{i['cluster_id']} ({i['count']} fotos)" for i in items if i["cluster_id"] in selected_ids}
    else:
        options = {i["id"]: i["name"] for i in items if i["id"] in selected_ids}

    col1, _ = st.columns([1, 2])
    with col1:
        target_id = st.selectbox(
            "Selecciona la identidad principal:",
            options=list(options.keys()),
            format_func=lambda x: options[x],
        )

    source_ids = [s for s in selected_ids if s != target_id]
    
    st.markdown("<br>", unsafe_allow_html=True)
    c_src, c_arrow, c_tgt = st.columns([4, 1, 3])
    
    with c_src:
        st.markdown("**Se reasignarán a:**")
        cols = st.columns(len(source_ids) if source_ids else 1)
        for idx, sid in enumerate(source_ids):
            with cols[idx]:
                if is_cluster:
                    item = next(i for i in items if i["cluster_id"] == sid)
                    path = item["samples"][0]["face_crop_path"] if item["samples"] else ""
                    name = f"Grupo #{sid}"
                else:
                    item = next(i for i in items if i["id"] == sid)
                    path = item["face_crop_path"]
                    name = item["name"]
                    
                if path and Path(path).exists():
                    st.image(path, use_container_width=True, caption=name)
                else:
                    st.markdown("👤", unsafe_allow_html=True)
                    
    with c_arrow:
        st.markdown(
            "<div style='height:100%; display:flex; align-items:center; justify-content:center; font-size:48px; color:#3b82f6; margin-top:20px'>➔</div>", 
            unsafe_allow_html=True
        )
        
    with c_tgt:
        st.markdown("**Identidad Principal Final:**")
        if is_cluster:
            item = next(i for i in items if i["cluster_id"] == target_id)
            path = item["samples"][0]["face_crop_path"] if item["samples"] else ""
            name = f"Grupo #{target_id}"
        else:
            item = next(i for i in items if i["id"] == target_id)
            path = item["face_crop_path"]
            name = item["name"]
            
        if path and Path(path).exists():
            st.image(path, width=150, caption=f"{name} (IA Recalculada)")
        else:
            st.markdown("👤", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🪄 Confirmar Fusión", type="primary", use_container_width=True):
        with st.spinner("Fusionando identidades y actualizando la base de datos..."):
            if is_cluster:
                db.merge_dbscan_clusters(target_id, source_ids)
                st.session_state.selected_clusters.clear()
            else:
                db.merge_known_faces(target_id, source_ids)
                st.session_state.selected_people.clear()
            st.toast("✅ ¡Fusión completada con éxito!")
            st.rerun()
