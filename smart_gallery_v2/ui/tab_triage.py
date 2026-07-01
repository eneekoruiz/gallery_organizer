"""
ui/tab_triage.py — Sistema de Triaje con 3 Bandejas
Bandeja SEGURA · Bandeja DUDOSA (1-clic validación) · Bandeja SIN CLASIFICAR
Etiquetado Faceless · Bulk Actions · Inspector con BBoxes
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from application.identity_corrections import CorrectIdentity, IdentityRegion
from domain.models import RegionKind
from infrastructure.sqlite.identity_repository import SqliteIdentityCorrectionRepository
from PIL import Image

from core.database import DatabaseManager
from core.symlink_manager import create_faceless_symlink


# ──────────────────────────────────────────────────────────────────────────────
# Render principal
# ──────────────────────────────────────────────────────────────────────────────
def render_triage(db: DatabaseManager) -> None:
    st.markdown(
        """
    <div style='margin-bottom:18px'>
      <h3 style='margin:0'>⚖️ Bandeja de Triaje</h3>
      <p style='color:#505570;margin:4px 0 0;font-size:14px'>
        El sistema clasifica automáticamente por nivel de confianza. Tú solo revisas lo dudoso.
      </p>
    </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:linear-gradient(145deg,#10121a,#14172280);border:1px solid #1c1f2e;border-radius:16px;padding:14px 16px;margin:0 0 14px">'
        '<div style="font-size:12px;color:#7f88a8;text-transform:uppercase;letter-spacing:.12em">Flujo recomendado</div>'
        '<div style="font-size:14px;color:#dce2f2;margin-top:5px;line-height:1.5">'
        "1) Confirma lo seguro. 2) Revisa lo dudoso. 3) Usa <strong>Deshacer último cambio</strong> solo después de validar, renombrar o etiquetar manualmente. "
        "Los archivos originales no se tocan desde aquí; solo se corrigen relaciones, etiquetas y symlinks."
        "</div></div>",
        unsafe_allow_html=True,
    )

    tab_safe, tab_review, tab_unk, tab_faceless, tab_clusters = st.tabs(
        [
            "✅ Seguros (>85%)",
            "🔶 Revisar (40–85%)",
            "❓ Sin Clasificar",
            "👤 Etiquetado Manual",
            "🪄 Agrupamiento IA",
        ]
    )

    with tab_safe:
        _render_safe_bin(db)

    with tab_review:
        _render_review_bin(db)

    with tab_unk:
        _render_unknown_bin(db)

    with tab_faceless:
        _render_faceless_panel(db)

    with tab_clusters:
        _render_clusters_tab(db)

    # Inspector modal si está activo
    if st.session_state.get("inspect_det_id"):
        _render_inspector(db)


# ──────────────────────────────────────────────────────────────────────────────
# Bandeja 1 — SEGURA (auto-clasificados, solo lectura / corrección)
# ──────────────────────────────────────────────────────────────────────────────
def _render_safe_bin(db: DatabaseManager) -> None:
    count = db.get_triage_count("safe")
    limit = 60
    num_pages = max(1, (count + limit - 1) // limit)

    st.markdown(
        '<div class="triage-header triage-safe">'
        '<span class="tier-badge tb-safe">✅ Alta Confianza > 85%</span>'
        f'<span style="color:#505570;font-size:13px">{count} detecciones clasificadas automáticamente</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if count > limit:
        page = st.number_input("Página (Seguros):", 1, num_pages, 1, key="p_safe")
        offset = (page - 1) * limit
    else:
        offset = 0

    df = db.get_triage_detections("safe", limit=limit, offset=offset)

    if df.empty:
        st.info("Sin detecciones de alta confianza todavía.")
        return

    _render_detection_grid(db, df, allow_confirm=False, show_bulk=True)


# ──────────────────────────────────────────────────────────────────────────────
# Bandeja 2 — DUDOSA (la IA propone, el humano valida con 1 clic)
# ──────────────────────────────────────────────────────────────────────────────
def _render_review_bin(db: DatabaseManager) -> None:
    count = db.get_triage_count("review")
    limit = 48
    num_pages = max(1, (count + limit - 1) // limit)

    st.markdown(
        '<div class="triage-header triage-review">'
        '<span class="tier-badge tb-review">🔶 Confianza Media 40–85%</span>'
        f'<span style="color:#505570;font-size:13px">{count} detecciones pendientes de tu validación</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if count > limit:
        page = st.number_input("Página (Dudosos):", 1, num_pages, 1, key="p_review")
        offset = (page - 1) * limit
    else:
        offset = 0

    df = db.get_triage_detections("review", limit=limit, offset=offset)

    if df.empty:
        st.success("🎉 ¡Sin dudas pendientes! La IA tiene todo controlado.")
        return

    st.caption("La IA propone un nombre. Confirma o deniega con un solo clic.")
    _render_detection_grid(db, df, allow_confirm=True, show_bulk=True)


# ──────────────────────────────────────────────────────────────────────────────
# Bandeja 3 — SIN CLASIFICAR (ni cara ni objeto detectados)
# ──────────────────────────────────────────────────────────────────────────────
def _render_unknown_bin(db: DatabaseManager) -> None:
    count = db.get_files_count(status="DONE", triage="unclassified")
    limit = 80
    num_pages = max(1, (count + limit - 1) // limit)

    st.markdown(
        '<div class="triage-header triage-unk">'
        '<span class="tier-badge tb-unk">❓ Sin Clasificar</span>'
        f'<span style="color:#505570;font-size:13px">{count} archivos sin detecciones</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    if count > limit:
        page = st.number_input("Página (Sin clasificar):", 1, num_pages, 1, key="p_unk")
        offset = (page - 1) * limit
    else:
        offset = 0

    df_files = db.get_files_with_thumbs_df(
        status="DONE", triage="unclassified", limit=limit, offset=offset
    )

    if df_files.empty:
        st.info("No hay archivos sin clasificar.")
        return

    st.caption("Puedes usar 'Etiquetado Manual' para asignar identidades a estas fotos.")
    _render_file_grid(db, df_files)


# ──────────────────────────────────────────────────────────────────────────────
# Panel Faceless — Etiquetado sin rostro
# ──────────────────────────────────────────────────────────────────────────────
def _render_faceless_panel(db: DatabaseManager) -> None:
    st.markdown(
        """
    <div class="triage-header triage-unk" style="margin-bottom:16px">
      <span class="tier-badge tb-unk">👤 Etiquetado Manual (Faceless)</span>
      <span style="color:#505570;font-size:13px">
        Asigna identidades a personas de espaldas, siluetas o sin cara visible.
        No requiere embedding facial — vinculación directa por nombre.
      </span>
    </div>""",
        unsafe_allow_html=True,
    )

    # Selector de archivo
    df = db.get_files_df(status="DONE", limit=200)
    if df.empty:
        st.info("Procesa imágenes primero para poder etiquetarlas manualmente.")
        return

    filenames = df["filename"].tolist()
    sel_name = st.selectbox("Selecciona una foto para etiquetar:", filenames, key="fl_file_sel")
    sel_row = df[df["filename"] == sel_name].iloc[0]
    file_id = int(sel_row["id"])
    filepath = sel_row["filepath"]

    crop_box = None
    image_size = (1, 1)
    col_img, col_form = st.columns([3, 2])

    with col_img:
        if Path(filepath).exists():
            image = Image.open(filepath)
            image_size = image.size
            try:
                from streamlit_cropper import st_cropper

                st.caption("Arrastra y redimensiona el área sobre la persona, ropa o silueta.")
                crop_box = st_cropper(
                    image,
                    realtime_update=True,
                    box_color="#007aff",
                    return_type="box",
                    key=f"identity_crop_{file_id}",
                )
            except ImportError:
                st.image(image, use_container_width=True, caption=f"📷 {sel_name}")
                st.info("Instala streamlit-cropper para dibujar directamente sobre la foto.")
        else:
            st.warning("Archivo no encontrado en disco.")

    with col_form:
        st.markdown("#### Asignar identidad")
        st.caption("Puedes opcionalmente indicar la región del cuerpo con coordenadas.")

        known = db.get_all_identity_names()
        opts = ["(Nueva identidad)"] + known
        sel_id = st.selectbox("Identidad conocida:", opts, key="fl_known")
        new_id = ""
        if sel_id == "(Nueva identidad)":
            new_id = st.text_input(
                "Nombre de la persona:",
                key="fl_new_name",
                placeholder="Ej: Carlos Ruiz",
            )

        region_mode = st.radio(
            "Presencia en la imagen",
            ["Área seleccionada", "Toda la fotografía"],
            horizontal=True,
            help="Toda la fotografía fuerza la presencia sin asociarla a una zona concreta.",
        )
        hard_case = st.selectbox(
            "Caso útil para aprendizaje activo",
            ["other", "back_view", "occluded", "helmet", "small_region", "low_light"],
            format_func=lambda value: {
                "other": "Normal",
                "back_view": "De espaldas",
                "occluded": "Tapada/o",
                "helmet": "Casco",
                "small_region": "Región pequeña",
                "low_light": "Poca luz",
            }[value],
        )

        if st.button("✅ Asignar identidad faceless", type="primary"):
            nombre_final = new_id.strip() if sel_id == "(Nueva identidad)" else sel_id
            if not nombre_final:
                st.error("Introduce un nombre válido.")
                return

            region = IdentityRegion()
            if region_mode == "Área seleccionada":
                if not crop_box:
                    st.error("Dibuja un área o selecciona ‘Toda la fotografía’.")
                    return
                width, height = image_size
                region = IdentityRegion(
                    kind=RegionKind.RECTANGLE,
                    x=max(0.0, float(crop_box["left"]) / width),
                    y=max(0.0, float(crop_box["top"]) / height),
                    width=min(1.0, float(crop_box["width"]) / width),
                    height=min(1.0, float(crop_box["height"]) / height),
                )

            CorrectIdentity(SqliteIdentityCorrectionRepository(db)).execute(
                media_id=file_id,
                display_name=nombre_final,
                region=region,
                hard_case=hard_case if hard_case != "other" else None,
            )

            # Crear symlink
            src = Path(filepath)
            if src.exists():
                create_faceless_symlink(src, nombre_final, db, file_id)

            st.success(f"✅ '{nombre_final}' asignado a '{sel_name}' sin embedding facial.")
            st.rerun()

    # Mostrar etiquetas faceless ya asignadas a este archivo
    ids = db.get_identities_for_file(file_id)
    if ids:
        st.markdown(f"**Identidades ya asignadas:** {', '.join(ids)}")

    st.divider()

    # Issue 17: Gestión Global de Identidades
    st.markdown("#### ⚙️ Gestión Global de Identidades")
    st.caption(
        "Cambia el nombre de una persona en todo el sistema (Base de datos + Carpetas de resultados)."
    )

    known = db.get_all_identity_names()
    if not known:
        st.info("No hay identidades registradas todavía.")
    else:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            old_name = st.selectbox("Persona a renombrar:", known, key="rn_old")
        with c2:
            new_name = st.text_input("Nuevo nombre:", key="rn_new", placeholder="Ej: Juan Pérez")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Renombrar", type="primary", use_container_width=True):
                if not new_name.strip():
                    st.error("Nombre inválido.")
                else:
                    # 1. Renombrar en DB
                    if db.rename_identity(old_name, new_name):
                        # 2. Mover carpetas físicas
                        from core.symlink_manager import rename_identity_folders

                        rename_identity_folders(old_name, new_name, db)
                        st.success(f"✅ '{old_name}' es ahora '{new_name}'")
                        st.rerun()
                    else:
                        st.error("Fallo al renombrar en la base de datos.")


# ──────────────────────────────────────────────────────────────────────────────
# Grid de detecciones (shared entre bandejas)
# ──────────────────────────────────────────────────────────────────────────────
def _render_detection_grid(
    db: DatabaseManager, df: pd.DataFrame, allow_confirm: bool, show_bulk: bool
) -> None:
    if "triage_sel" not in st.session_state:
        st.session_state.triage_sel = set()

    # ── Bulk actions ──────────────────────────────────────────────────────
    if show_bulk and st.session_state.triage_sel:
        _render_bulk_bar(db, df)

    # ── Grid ──────────────────────────────────────────────────────────────
    n_cols = 4
    rows = [df.iloc[i : i + n_cols] for i in range(0, len(df), n_cols)]
    known_ids = db.get_all_identity_names()

    for row_df in rows:
        cols = st.columns(n_cols)
        for col, (_, det) in zip(cols, row_df.iterrows()):
            with col:
                _render_det_card(db, det, known_ids, allow_confirm)


def _render_det_card(
    db: DatabaseManager, det: pd.Series, known_ids: list[str], allow_confirm: bool
) -> None:
    det_id = int(det["id"])
    crop_path = det.get("face_crop_path", "")
    name = det.get("assigned_name", "Desconocido")
    conf = float(det.get("confidence", 0))
    filename = det.get("filename", "")
    tier = det.get("triage_tier", "unclassified")
    filepath = det.get("filepath", "")

    # Selección bulk
    sel = det_id in st.session_state.get("triage_sel", set())
    now = st.checkbox("", value=sel, key=f"tsel_{det_id}", label_visibility="collapsed")
    if now != sel:
        if now:
            st.session_state.triage_sel.add(det_id)
        else:
            st.session_state.triage_sel.discard(det_id)

    # Imagen del recorte
    if crop_path and Path(crop_path).exists():
        st.image(crop_path, use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#10121a;border-radius:10px;aspect-ratio:1;'
            'display:flex;align-items:center;justify-content:center;font-size:30px">👤</div>',
            unsafe_allow_html=True,
        )

    # Badge de tier + nombre
    tb_css = {"safe": "tb-safe", "review": "tb-review", "unclassified": "tb-unk"}.get(
        tier, "tb-unk"
    )
    conf_pct = f"{conf * 100:.0f}%" if conf > 0 else "—"
    st.markdown(
        f'<span class="tier-badge {tb_css}">{conf_pct}</span> '
        f'<span style="font-size:12px;color:#8892a4">{name}</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"📷 {filename[:22]}")

    # Controles
    if allow_confirm and name != "Desconocido":
        # Validación de 1 clic: Confirmar o Denegar
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅", key=f"cfm_{det_id}", help="Confirmar", use_container_width=True):
                db.verify_detection(det_id, name)
                # Issue 8: Actualizar symlinks en disco inmediatamente
                from core.symlink_manager import create_group_symlinks

                create_group_symlinks(Path(filepath), [name], db, int(det["file_id"]))
                st.toast(f"✅ {name} confirmado.")
                st.rerun()
        with c2:
            if st.button(
                "❌",
                key=f"den_{det_id}",
                help="Denegar / Falso positivo",
                use_container_width=True,
            ):
                db.mark_false_positive(det_id)
                st.toast("Falso positivo eliminado.")
                st.rerun()
    else:
        # Asignación manual
        opts = ["(Sin cambios)"] + known_ids + ["➕ Nuevo nombre"]
        sel_name = st.selectbox("", opts, key=f"dsel_{det_id}", label_visibility="collapsed")
        new_name = ""
        if sel_name == "➕ Nuevo nombre":
            new_name = st.text_input(
                "",
                key=f"dtxt_{det_id}",
                label_visibility="collapsed",
                placeholder="Nombre…",
            )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅", key=f"sv_{det_id}", use_container_width=True, type="primary"):
                n = new_name if sel_name == "➕ Nuevo nombre" else sel_name
                if n and n != "(Sin cambios)":
                    db.verify_detection(det_id, n)
                    # Issue 8: Actualizar symlinks en disco
                    from core.symlink_manager import create_group_symlinks

                    create_group_symlinks(Path(filepath), [n], db, int(det["file_id"]))
                    st.toast(f"✅ {n} guardado.")
                    st.rerun()
        with c2:
            if st.button("🗑", key=f"fp_{det_id}", use_container_width=True):
                db.mark_false_positive(det_id)
                st.toast("Eliminado.")
                st.rerun()

    # Botón inspector
    if st.button("🔍 Ver foto", key=f"ins_{det_id}", use_container_width=True):
        st.session_state.inspect_det_id = det_id
        st.session_state.inspect_path = filepath
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Bulk Actions Bar
# ──────────────────────────────────────────────────────────────────────────────
def _render_bulk_bar(db: DatabaseManager, df: pd.DataFrame) -> None:
    selected = st.session_state.triage_sel
    n = len(selected)
    known = db.get_all_identity_names()

    st.markdown(
        f'<div style="background:#14172280;border:1px solid #252840;border-radius:12px;padding:14px 18px;margin-bottom:12px">'
        f'<strong style="color:#a78bfa">{n} detecciones seleccionadas</strong></div>',
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4 = st.columns([3, 2, 2, 2])

    with b1:
        opts = ["(Seleccionar…)"] + known + ["➕ Nuevo nombre"]
        bk_sel = st.selectbox("Reasignar a:", opts, key="bk_sel")
        bk_new = ""
        if bk_sel == "➕ Nuevo nombre":
            bk_new = st.text_input("Nombre:", key="bk_new")

    with b2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"✅ Aplicar a {n}", type="primary"):
            nombre = bk_new if bk_sel == "➕ Nuevo nombre" else bk_sel
            if nombre and nombre != "(Seleccionar…)":
                db.bulk_verify(list(selected), nombre)
                # Issue 8: Bulk update symlinks
                from core.symlink_manager import create_group_symlinks

                for did in selected:
                    det_row = df[df["id"] == did].iloc[0]
                    create_group_symlinks(
                        Path(det_row["filepath"]), [nombre], db, int(det_row["file_id"])
                    )

                st.session_state.triage_sel = set()
                st.toast(f"✅ {n} detecciones → '{nombre}'")
                st.rerun()

    with b3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"🗑 {n} falsos positivos"):
            db.bulk_false_positive(list(selected))
            st.session_state.triage_sel = set()
            st.rerun()

    with b4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Deseleccionar"):
            st.session_state.triage_sel = set()
            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Grid de archivos (bandeja SIN CLASIFICAR)
# ──────────────────────────────────────────────────────────────────────────────
def _render_file_grid(db: DatabaseManager, df: pd.DataFrame) -> None:
    n_cols = 5
    rows = [df.iloc[i : i + n_cols] for i in range(0, len(df), n_cols)]
    for row_df in rows:
        cols = st.columns(n_cols)
        for col, (_, rec) in zip(cols, row_df.iterrows()):
            with col:
                # Usar cached_thumb si existe (requiere que el df venga de get_files_with_thumbs_df)
                # Si no, fallback seguro
                th = rec.get("cached_thumb")
                if th and Path(th).exists():
                    st.image(th, use_container_width=True)
                else:
                    st.markdown(
                        '<div style="background:#10121a;border-radius:10px;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:28px">🖼️</div>',
                        unsafe_allow_html=True,
                    )
                st.caption(rec.get("filename", "")[:22])


# ──────────────────────────────────────────────────────────────────────────────
# Inspector de imagen con BBoxes
# ──────────────────────────────────────────────────────────────────────────────
def _render_inspector(db: DatabaseManager) -> None:
    # det_id   = st.session_state.get("inspect_det_id")
    filepath = st.session_state.get("inspect_path", "")

    st.divider()
    st.markdown(f"### 🔍 Inspector · `{Path(filepath).name}`")

    if st.button("✖ Cerrar inspector"):
        st.session_state.pop("inspect_det_id", None)
        st.session_state.pop("inspect_path", None)
        st.rerun()

    if not Path(filepath).exists():
        st.error("Archivo no encontrado en disco.")
        return

    # Cargar detecciones del archivo a través del manager
    file_info = db.get_file_by_path(filepath)
    dets = []
    if file_info:
        dets = db.get_detections_for_file(file_info["id"])

    # Cargar imagen y dibujar bboxes con OpenCV
    stream = np.fromfile(filepath, dtype=np.uint8)
    img_bgr = cv2.imdecode(stream, cv2.IMREAD_COLOR)
    if img_bgr is None:
        st.error("No se pudo decodificar la imagen.")
        return

    h, w = img_bgr.shape[:2]
    max_w = 820
    scale = min(1.0, max_w / w)
    disp_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
    disp_rgb = cv2.cvtColor(disp_bgr, cv2.COLOR_BGR2RGB)

    colors = [
        (99, 102, 241),
        (236, 72, 153),
        (52, 211, 153),
        (251, 191, 36),
        (96, 165, 250),
        (248, 113, 113),
    ]
    for i, det in enumerate(dets):
        try:
            bbox = json.loads(det["bbox_json"])
            top = int(bbox["top"] * scale)
            bot = int(bbox["bottom"] * scale)
            left = int(bbox["left"] * scale)
            right = int(bbox["right"] * scale)
            name = det["assigned_name"]
            conf = det["confidence"]
            col = colors[i % len(colors)]

            cv2.rectangle(disp_rgb, (left, top), (right, bot), col, 2)
            label = f"{name} {conf * 100:.0f}%" if conf > 0 else name
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
            cv2.rectangle(disp_rgb, (left, top - th - 10), (left + tw + 10, top), col, -1)
            cv2.putText(
                disp_rgb,
                label,
                (left + 5, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (255, 255, 255),
                1,
            )
        except Exception:
            pass

    img_col, info_col = st.columns([3, 2])
    with img_col:
        st.image(disp_rgb, use_container_width=True)

    with info_col:
        st.markdown(f"**{len(dets)} detecciones** en esta imagen")
        known_ids = db.get_all_identity_names()

        for det in dets:
            tier = det.get("triage_tier", "unclassified")
            tb = {"safe": "tb-safe", "review": "tb-review"}.get(tier, "tb-unk")
            with st.expander(f"👤 {det['assigned_name']} ({det['confidence'] * 100:.0f}%)"):
                if det.get("face_crop_path") and Path(det["face_crop_path"]).exists():
                    st.image(det["face_crop_path"], width=90)
                st.markdown(
                    f'<span class="tier-badge {tb}">{tier}</span>',
                    unsafe_allow_html=True,
                )

                opts = ["(Sin cambios)"] + known_ids + ["➕ Nuevo nombre"]
                sel = st.selectbox("Corregir:", opts, key=f"insp_sel_{det['id']}")
                nw = ""
                if sel == "➕ Nuevo nombre":
                    nw = st.text_input("Nombre:", key=f"insp_txt_{det['id']}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Guardar", key=f"insp_sv_{det['id']}", type="primary"):
                        nombre = nw if sel == "➕ Nuevo nombre" else sel
                        if nombre and nombre != "(Sin cambios)":
                            db.verify_detection(det["id"], nombre)
                            # Issue 8: Actualizar symlinks
                            from core.symlink_manager import create_group_symlinks

                            create_group_symlinks(Path(filepath), [nombre], db, int(det["file_id"]))
                            st.toast(f"✅ {nombre}")
                            st.rerun()
                with c2:
                    if st.button("Falso+", key=f"insp_fp_{det['id']}"):
                        db.mark_false_positive(det["id"])
                        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Bandeja 5 — AGRUPAMIENTO IA (DBSCAN de caras desconocidas)
# ──────────────────────────────────────────────────────────────────────────────
def _render_clusters_tab(db: DatabaseManager) -> None:
    from core.clustering import FaceClustering

    st.markdown(
        '<div class="triage-header triage-review">'
        '<span class="tier-badge tb-review">🪄 Agrupamiento IA</span>'
        '<span style="color:#505570;font-size:13px">La IA busca caras parecidas entre tus "Desconocidos"</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🚀 Ejecutar Agrupamiento (DBSCAN)", use_container_width=True):
            with st.spinner("Analizando rostros..."):
                fc = FaceClustering(db)
                n = fc.run()
                st.success(f"¡He encontrado {n} grupos de personas!")
                st.rerun()
    with c2:
        st.caption(
            "Esto agrupa caras que pertenecen a la misma persona para que puedas etiquetarlas de golpe."
        )

    clusters = db.get_clusters_with_samples()
    if not clusters:
        st.info(
            "No hay grupos detectados. Pulsa el botón de arriba para analizar tus rostros desconocidos."
        )
        return

    for cl in clusters:
        cid = cl["cluster_id"]
        count = cl["count"]
        with st.expander(f"Grupo #{cid} — {count} fotos detectadas", expanded=True):
            cols = st.columns(len(cl["samples"]) + 1)
            for i, sample in enumerate(cl["samples"]):
                with cols[i]:
                    if Path(sample["face_crop_path"]).exists():
                        st.image(sample["face_crop_path"], use_container_width=True)

            with cols[-1]:
                st.write("**¿Quién es?**")
                known = db.get_all_identity_names()
                opts = ["(Seleccionar…)"] + known + ["➕ Nuevo nombre"]
                sel = st.selectbox("Asignar nombre:", opts, key=f"cl_sel_{cid}")
                new_name = ""
                if sel == "➕ Nuevo nombre":
                    new_name = st.text_input("Nombre:", key=f"cl_txt_{cid}")

                if st.button(f"Confirmar {count} fotos", key=f"cl_btn_{cid}", type="primary"):
                    final_name = new_name if sel == "➕ Nuevo nombre" else sel
                    if final_name and final_name != "(Seleccionar…)":
                        db.verify_cluster(cid, final_name)
                        st.toast(f"✅ {count} fotos asignadas a {final_name}")
                        st.rerun()
