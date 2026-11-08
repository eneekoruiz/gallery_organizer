r"""
Genera y coloca la imagen de la cara principal del centroide como primer archivo (_00_CENTROIDE_<Persona>.jpg)
en cada una de las carpetas de personas (tanto en Google Drive G:\ como en el Escritorio local).
"""
import os
import re
import sys
import cv2
import pickle
import numpy as np
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.globals import APP_DIR, THUMBNAILS_DIR, FOTOS_DIR, RESULTADOS_DIR

# Carpetas raíz donde el usuario inspecciona fotos
GALLERY_ROOTS = [
    Path(r"G:\Mi unidad\SmartGallery - traslado 2026-11-03\Resultados"),
    Path(r"G:\Mi unidad\SmartGallery - traslado 2026-11-03\Fotos"),
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados"),
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos"),
    APP_DIR / "Resultados",
    APP_DIR / "Fotos"
]

CATEGORIES = ["Conocidos", "Familia", "YO", "Mascotas", "Personas Sin Nombre"]

def get_best_avatar_image(cat, ident):
    """Obtiene la mejor imagen para el centroide de una persona desde .thumbnails o caché."""
    ident_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(ident))
    clean_ident = ident.replace('👤', '').strip()
    clean_ident_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(clean_ident))
    cat_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(cat))

    candidates = [
        THUMBNAILS_DIR / f"av_{cat_clean}_{ident_clean}.webp",
        THUMBNAILS_DIR / f"av_{cat_clean}_{clean_ident_clean}.webp",
        THUMBNAILS_DIR / f"av_Conocidos_{clean_ident_clean}.webp",
        THUMBNAILS_DIR / f"av_Familia_{clean_ident_clean}.webp",
        THUMBNAILS_DIR / f"av_Personas_Sin_Nombre_{clean_ident_clean}.webp",
        APP_DIR / "cache" / "thumbnails" / f"av_{cat_clean}_{ident_clean}.webp"
    ]

    for c in candidates:
        if c.exists() and c.stat().st_size > 200:
            img = cv2.imread(str(c))
            if img is not None and img.shape[0] >= 40 and img.shape[1] >= 40:
                return img

    return None

def extract_face_from_folder_photos(folder_path):
    """Extrae ÚNICAMENTE una cara real detectada con confianza alta. NUNCA recortar paisajes ni fotos sin caras."""
    from app.globals import detector
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith(("_00_", "00_", "!00_"))]
    if not photos or detector is None:
        return None

    photos.sort(key=lambda x: x.stat().st_size, reverse=True)
    
    for photo_path in photos[:8]:
        data = np.fromfile(str(photo_path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h_img, w_img = img.shape[:2]
        # Scaled detection
        max_dim = 1024
        scale = 1.0
        if max(w_img, h_img) > max_dim:
            scale = max_dim / max(w_img, h_img)
            det_w = max(160, int(w_img * scale))
            det_h = max(160, int(h_img * scale))
            det_img = cv2.resize(img, (det_w, det_h), interpolation=cv2.INTER_AREA)
        else:
            det_w, det_h = w_img, h_img
            det_img = img
            
        inv_scale = 1.0 / scale
        try:
            detector.setInputSize((det_w, det_h))
            detector.setScoreThreshold(0.55)
            _, faces = detector.detect(det_img)
            if faces is not None and len(faces) > 0:
                # Filtrar la mejor cara
                faces = sorted(faces, key=lambda f: f[2]*f[3]*f[-1], reverse=True)
                best_f = faces[0]
                if best_f[-1] >= 0.55:
                    x, y, w, h = int(best_f[0] * inv_scale), int(best_f[1] * inv_scale), int(best_f[2] * inv_scale), int(best_f[3] * inv_scale)
                    if w >= 40 and h >= 40:
                        pad_x = int(min(w * 0.15, x, w_img - (x + w)))
                        pad_y = int(min(h * 0.15, y, h_img - (y + h)))
                        px1, py1 = max(0, x - pad_x), max(0, y - pad_y)
                        px2, py2 = min(w_img, x + w + pad_x), min(h_img, y + h + pad_y)
                        crop = img[py1:py2, px1:px2]
                        if crop.size > 0:
                            return crop
        except Exception:
            pass

    return None

def generate_covers_for_all_folders(force=False):
    """Genera _00_CENTROIDE_<Identidad>.jpg en todas las carpetas de personas."""
    stats = {
        "roots_scanned": 0,
        "folders_checked": 0,
        "covers_created": 0,
        "covers_existing": 0,
        "covers_failed": 0
    }

    for root in GALLERY_ROOTS:
        if not root.exists():
            continue
        stats["roots_scanned"] += 1
        print(f"[*] Escaneando raíz: {root}")

        for cat in CATEGORIES:
            cat_dir = root / cat
            if not cat_dir.exists():
                continue

            for person_dir in cat_dir.iterdir():
                if not person_dir.is_dir():
                    continue

                ident = person_dir.name
                if ident.startswith(("_", "📋", "⏳")):
                    continue

                stats["folders_checked"] += 1
                
                # Nombre con prefijo _00_ para garantizar que se ordene en primer lugar siempre
                cover_filename = f"_00_CENTROIDE_{ident}.jpg"
                cover_path = person_dir / cover_filename

                if cover_path.exists() and not force:
                    stats["covers_existing"] += 1
                    continue

                # 1. Obtener imagen del avatar/centroide
                avatar_img = get_best_avatar_image(cat, ident)
                
                # 2. Si no hay avatar, extraer de las fotos de la carpeta
                if avatar_img is None:
                    avatar_img = extract_face_from_folder_photos(person_dir)

                if avatar_img is not None:
                    try:
                        # Redimensionar a 320x320 con calidad alta
                        h, w = avatar_img.shape[:2]
                        if h != 320 or w != 320:
                            avatar_img = cv2.resize(avatar_img, (320, 320), interpolation=cv2.INTER_LANCZOS4)

                        # Guardar como JPEG con calidad 95 (excelente compatibilidad para thumbnails en Drive y Windows)
                        cv2.imwrite(str(cover_path), avatar_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        stats["covers_created"] += 1
                    except Exception as e:
                        print(f"[!] Error guardando en {cover_path}: {e}")
                        stats["covers_failed"] += 1
                else:
                    stats["covers_failed"] += 1

    return stats

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("GENERADOR DE IMÁGENES DE PORTADA DEL CENTROIDE (_00_CENTROIDE.jpg)")
    print("=" * 60)
    res = generate_covers_for_all_folders(force=False)
    print("\n[RESULTADO]")
    print(f"  Raíces escaneadas : {res['roots_scanned']}")
    print(f"  Carpetas revisadas: {res['folders_checked']}")
    print(f"  Portadas creadas  : {res['covers_created']}")
    print(f"  Portadas ya exist.: {res['covers_existing']}")
    print(f"  Sin imagen / omit.: {res['covers_failed']}")
