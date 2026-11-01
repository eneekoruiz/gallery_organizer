# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
from pathlib import Path
import shutil
from app.globals import FOTOS_DIR, RESULTADOS_DIR, clear_gallery_cache

def is_text_quote_image(img_bgr):
    """
    Detecta de forma ultrarrápida si una imagen es una frase de Instagram,
    meme de texto, captura de notas/Twitter o tarjeta gráfica tipográfica.
    """
    if img_bgr is None: return False, 0.0
    h, w = img_bgr.shape[:2]
    if h < 50 or w < 50: return False, 0.0
    
    max_dim = 640
    scale = max_dim / max(h, w) if max(h, w) > max_dim else 1.0
    img_s = cv2.resize(img_bgr, (int(w * scale), int(h * scale))) if scale < 1.0 else img_bgr
    
    gray = cv2.cvtColor(img_s, cv2.COLOR_BGR2GRAY)
    
    # 1. Gradiente morfológico para resaltar trazos de caracteres
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
    
    # 2. Umbralización Otsu
    _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    # 3. Conectar caracteres en palabras/líneas horizontales
    line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
    connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, line_kernel)
    
    # 4. Encontrar contornos de bloques de texto
    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    text_blocks = 0
    total_text_area = 0
    img_area = img_s.shape[0] * img_s.shape[1]
    
    for cnt in contours:
        bx, by, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / float(bh)
        box_area = bw * bh
        if aspect >= 1.6 and bh >= 7 and bw >= 20 and box_area < img_area * 0.45:
            text_blocks += 1
            total_text_area += box_area
            
    text_coverage = total_text_area / max(1, img_area)
    
    # 5. Varianza de color en bordes para detectar fondos planos/geométricos
    border_pixels = np.concatenate([
        img_s[:15, :].reshape(-1, 3), 
        img_s[-15:, :].reshape(-1, 3), 
        img_s[:, :15].reshape(-1, 3), 
        img_s[:, -15:].reshape(-1, 3)
    ])
    bg_std = np.mean(np.std(border_pixels, axis=0))
    is_solid_bg = bg_std < 35.0
    
    score = 0.0
    if text_blocks >= 3: score += 0.35
    if text_blocks >= 6: score += 0.25
    if text_coverage >= 0.04: score += 0.25
    if is_solid_bg: score += 0.25
    
    is_quote = (text_blocks >= 4 and score >= 0.50) or (is_solid_bg and text_blocks >= 2 and text_coverage >= 0.03)
    return is_quote, score

def scan_and_categorize_quotes(target_dirs=None):
    """
    Escanea carpetas de revisión y mueve las frases a 'Resultados/Frases/Frases e Imágenes de Texto'.
    """
    if target_dirs is None:
        target_dirs = []
        for b in [FOTOS_DIR, RESULTADOS_DIR]:
            if not b.exists(): continue
            rev = b / "Revision_Interactiva" / "Sin_Rostro"
            if rev.exists(): target_dirs.append(rev)
            desc = b / "Personas Sin Nombre" / "Desconocidos"
            if desc.exists(): target_dirs.append(desc)
            
    dest_dir = RESULTADOS_DIR / "Frases" / "Frases e Imágenes de Texto"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    moved_count = 0
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    
    for t_dir in target_dirs:
        if not t_dir.exists(): continue
        for f in list(t_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in valid_exts:
                try:
                    b_arr = np.fromfile(str(f), dtype=np.uint8)
                    img = cv2.imdecode(b_arr, cv2.IMREAD_COLOR)
                    if img is not None:
                        is_q, score = is_text_quote_image(img)
                        if is_q and score >= 0.55:
                            dest_f = dest_dir / f.name
                            if not dest_f.exists():
                                shutil.move(str(f), str(dest_f))
                                moved_count += 1
                except Exception as e:
                    print(f"[QUOTE_SERVICE] Error en {f.name}: {e}")
                    
    if moved_count > 0:
        clear_gallery_cache()
    return moved_count
