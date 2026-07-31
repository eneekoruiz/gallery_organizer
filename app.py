import storage_adapters
from state_memory import state_memory
import time
import os
import shutil
import pickle
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
import cv2
import numpy as np
import exifread

app = Flask(__name__)

# Rutas Principales
RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
FOTOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos")
APP_DIR = Path(__file__).resolve().parent
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"

FACES_CACHE_FILE = Path("faces_cache.pkl")
faces_cache = {}
if FACES_CACHE_FILE.exists():
    try:
        with open(FACES_CACHE_FILE, 'rb') as f:
            faces_cache = pickle.load(f)
    except:
        faces_cache = {}


# Inicializar Modelos AI
try:
    detector = cv2.FaceDetectorYN.create(
        str(APP_DIR / "models" / "face_detection_yunet.onnx"), 
        "", 
        (320, 320),
        0.70,  # umbral ajustado para evitar detectar texturas como caras
        0.3,
        5000
    )
    recognizer = cv2.FaceRecognizerSF.create(
        str(APP_DIR / "models" / "face_recognition_sface.onnx"), 
        ""
    )
    # Cargar Dataset de Aprendizaje (Ground Truth)
    with open(CACHE_FILE, 'rb') as f:
        cache_data = pickle.load(f)
        if isinstance(cache_data, list):
            known_faces = {}
            for item in cache_data:
                known_faces[item['identidad']] = {'centroid': item['feature'], 'names': []}
            # Guardar en formato diccionario correcto para futuras lecturas
            with open(CACHE_FILE, 'wb') as f2:
                pickle.dump(known_faces, f2)
        else:
            known_faces = cache_data
except Exception as e:
    print(f"Error cargando IA: {e}")
    detector = None
    recognizer = None
    known_faces = {}

def get_all_identities():
    identities = []
    seen = set()
    for base_dir in [FOTOS_DIR, RESULTADOS_DIR]:
        if base_dir.exists():
            for cat in base_dir.iterdir():
                if cat.is_dir():
                    if cat.name == 'Mascotas':
                        continue
                    for ident in cat.iterdir():
                        if ident.is_dir():
                            c_name = cat.name
                            i_name = ident.name
                            if i_name.upper() == 'YO':
                                c_name = 'YO'
                                i_name = 'YO'
                            elif c_name == 'Recuerdos' or i_name == 'Recuerdos':
                                c_name = 'Recuerdos'
                                i_name = 'Recuerdos'
                            key = f"{c_name}/{i_name}"
                            if key not in seen:
                                identities.append({"categoria": c_name, "identidad": i_name})
                                seen.add(key)
    return sorted(identities, key=lambda x: x['identidad'])

def get_cosine_similarity(feat1, feat2):
    f1 = np.squeeze(feat1)
    f2 = np.squeeze(feat2)
    return np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.after_request
def add_header(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response


_GALLERY_CACHE = None
PENDING_DELETIONS_FILE = Path("pending_deletions.txt")

def process_pending_deletions():
    if not PENDING_DELETIONS_FILE.exists(): return
    try:
        with open(PENDING_DELETIONS_FILE, "r") as f:
            paths = f.read().splitlines()
        remaining = []
        for p in paths:
            if not p.strip(): continue
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

def clear_gallery_cache():
    global _GALLERY_CACHE
    _GALLERY_CACHE = None

@app.route('/api/identities')
def api_identities():
    return jsonify(get_all_identities())


import gc, time, shutil, os

def safe_move_file(src, dst):
    src_str, dst_str = str(src), str(dst)
    gc.collect()
    for attempt in range(5):
        try:
            shutil.move(src_str, dst_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    try:
        shutil.copy2(src_str, dst_str)
        try:
            os.remove(src_str)
        except:
            pass
        return True
    except Exception as e:
        raise e

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False


@app.route('/api/gallery')
def get_gallery():
    process_pending_deletions()
    
    global _GALLERY_CACHE
    if _GALLERY_CACHE is not None:
        return jsonify(_GALLERY_CACHE)
        
    gallery = {}
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    seen_files = {}
    
    overrides = load_overrides()
    
    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass
    
    
    def scan_dir(base_dir, is_orig_dataset):
        if not base_dir.exists(): return
        for root, dirs, files in os.walk(str(base_dir)):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    path_obj = Path(root) / file
                    try:
                        rel_path = path_obj.relative_to(base_dir)
                        parts = rel_path.parts
                        if len(parts) >= 2:
                            cat = parts[0]
                            ident = parts[1]
                            
                            # Extraer carpeta YO como seccion principal
                            if ident.upper() == 'YO':
                                cat = 'YO'
                                ident = 'YO'
                            elif cat == 'Publicaciones_Instagram' or ident == 'Publicaciones_Instagram':
                                cat = 'Publicaciones_Instagram'
                                ident = 'Publicaciones_Instagram'
                            elif cat == 'Recuerdos' or ident == 'Recuerdos':
                                cat = 'Recuerdos'
                                ident = 'Recuerdos'

                            
                            key = (cat, ident, file)
                            is_dudoso = "_Dudosos" in str(path_obj)
                            file_key = get_file_key(str(path_obj))
                            
                            # Duplicados / Apilamiento
                            try:
                                abs_path = str(path_obj.resolve())
                                if abs_path in dup_data:
                                    d_info = dup_data[abs_path]
                                    item_data['group_id'] = d_info['group_id']
                                    item_data['group_size'] = d_info['group_size']
                                    item_data['is_group_rep'] = d_info['is_rep']
                            except:
                                pass
                                
                            # Determinación estricta de la etiqueta (Dataset vs Manual vs IA)
                            labels = []
                            if is_orig_dataset:
                                labels.append("Dataset")
                            else:
                                labels.append("IA")
                                
                            if file_key in overrides and len(overrides[file_key]) > 0:
                                labels.append("Manual")
                                
                            label = " + ".join(labels)
                                
                            if key in seen_files:
                                existing = seen_files[key]
                                if label not in existing["source"]:
                                    existing["source"] = f"{existing['source']} + {label}"
                            else:
                                abs_p = str(path_obj)
                                num_f = len(faces_cache.get(abs_p, []))
                                if num_f == 0 and file_key in overrides:
                                    num_f = len(overrides[file_key])
                                item = {
                                    "path": str(path_obj),
                                    "name": file,
                                    "status": "Dudoso" if is_dudoso else "Clasificado",
                                    "source": label,
                                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                    "num_faces": num_f
                                }
                                seen_files[key] = item
                    except Exception:
                        pass
                        
    scan_dir(FOTOS_DIR, True)
    scan_dir(RESULTADOS_DIR, False)
    
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}

    for (cat, ident, filename), item in seen_files.items():
        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        gallery[cat][ident].append(item)
        
        # Inclusión Virtual Multi-Persona: La foto aparece en el álbum de cada persona presente
        faces_in_file = faces_cache.get(item['path'], [])
        file_k = get_file_key(item['path'])
        if file_k in overrides:
            faces_in_file = overrides[file_k]
            
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and other_id != ident and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                other_cat = ident_to_cat_map.get(other_id)
                if not other_cat:
                    if other_id.startswith('C. '): other_cat = 'Conocidos'
                    elif other_id.startswith('F. '): other_cat = 'Familia'
                    elif other_id == 'YO': other_cat = 'YO'
                    else: other_cat = 'Conocidos'
                    
                if other_cat not in gallery: gallery[other_cat] = {}
                if other_id not in gallery[other_cat]: gallery[other_cat][other_id] = []
                
                if not any(x['path'] == item['path'] for x in gallery[other_cat][other_id]):
                    gallery[other_cat][other_id].append(item)
        
    _GALLERY_CACHE = gallery
    return jsonify(gallery)



@app.route('/api/purge_exact_duplicates', methods=['POST'])
def api_purge_exact_duplicates():
    global _GALLERY_CACHE, faces_cache
    import hashlib
    size_map = {}
    base_dir = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
    
    for root, dirs, files in os.walk(str(base_dir)):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
                p = Path(root) / f
                try:
                    sz = p.stat().st_size
                    if sz not in size_map: size_map[sz] = []
                    size_map[sz].append(p)
                except: pass
                
    hash_map = {}
    for sz, paths in size_map.items():
        if len(paths) > 1:
            for p in paths:
                try:
                    with open(p, 'rb') as f:
                        md5 = hashlib.md5(f.read()).hexdigest()
                    if md5 not in hash_map: hash_map[md5] = []
                    hash_map[md5].append(p)
                except: pass
                
    purged_count = 0
    for md5, paths in hash_map.items():
        if len(paths) > 1:
            def score_path(p):
                p_str = str(p)
                score = 0
                if 'Resultados' in p_str: score += 10
                if 'Conocidos' in p_str or 'Familia' in p_str or 'YO' in p_str: score += 10
                if '_Dudosos' in p_str: score -= 5
                return score
            sorted_paths = sorted(paths, key=score_path, reverse=True)
            for rem in sorted_paths[1:]:
                try:
                    safe_remove_file(rem)
                    purged_count += 1
                except: pass
                
    _GALLERY_CACHE = None
    return jsonify({"success": True, "purged_count": purged_count})


@app.route('/api/metadata')
def api_metadata():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return jsonify({"error": "File not found"}), 404
    filepath = real_path
        
    stats = os.stat(filepath)
    size = f"{stats.st_size / (1024*1024):.2f} MB"
    
    # Fallback mtime (Fecha de Modificación de Windows)
    mtime = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    real_date = mtime
    
    camera = "Desconocida"
    res = "Desconocida"
    
    is_video = filepath.lower().endswith(('.mp4', '.mov', '.avi'))
    
    if not is_video:
        try:
            with open(filepath, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                if 'Image Make' in tags:
                    camera = f"{tags['Image Make']} {tags.get('Image Model', '')}"
                if 'EXIF ExifImageWidth' in tags:
                    res = f"{tags['EXIF ExifImageWidth']} x {tags.get('EXIF ExifImageLength', '')}"
                    
                # Extraer Fecha Original Pura
                if 'EXIF DateTimeOriginal' in tags:
                    real_date = str(tags['EXIF DateTimeOriginal'])
                elif 'Image DateTime' in tags:
                    real_date = str(tags['Image DateTime'])
        except:
            pass
            
    # Último intento: Buscar patrón YYYYMMDD en el nombre del archivo
    if real_date == mtime:
        import re
        match = re.search(r'(19\d{2}|20\d{2})([0-1]\d)([0-3]\d)', Path(filepath).name)
        if match:
            year, month, day = match.groups()
            try:
                parsed_date = datetime.datetime(int(year), int(month), int(day))
                real_date = f"{parsed_date.strftime('%Y-%m-%d')} (Archivo)"
            except ValueError:
                pass
    
    return jsonify({"size": size, "date": real_date, "camera": camera, "resolution": res})

@app.route('/media')
def get_media():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    res = send_file(real_path, conditional=True)
    res.headers['Cache-Control'] = 'public, max-age=86400'
    return res




def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False

import json

OVERRIDES_FILE = APP_DIR / "manual_overrides.json"

def load_overrides():
    if OVERRIDES_FILE.exists():
        with open(OVERRIDES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_overrides(data):
    with open(OVERRIDES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def find_relocated_file(filepath):
    if not filepath:
        return None
    if os.path.exists(filepath):
        return filepath
    filename = Path(filepath).name
    for bdir in [RESULTADOS_DIR, FOTOS_DIR]:
        if bdir.exists():
            for root, dirs, files in os.walk(str(bdir)):
                if filename in files:
                    return os.path.join(root, filename)
    return None

def get_file_key(filepath):
    try:
        return str(os.stat(filepath).st_ino)
    except:
        return str(filepath)

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0: return 0.0
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    return interArea / float(boxAArea + boxBArea - interArea)


def calculate_sharpness(filepath):
    try:
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None: return 0.0
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return 0.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return round(cv2.Laplacian(gray, cv2.CV_64F).var(), 1)
    except:
        return 0.0


DHASH_CACHE_FILE = Path("dhash_cache.pkl")
_DHASH_CACHE = {}
if DHASH_CACHE_FILE.exists():
    try:
        import pickle
        with open(DHASH_CACHE_FILE, 'rb') as f:
            _DHASH_CACHE = pickle.load(f)
    except:
        pass

def save_dhash_cache():
    try:
        import pickle
        with open(DHASH_CACHE_FILE, 'wb') as f:
            pickle.dump(_DHASH_CACHE, f)
    except:
        pass

def calculate_dhash(filepath):
    global _DHASH_CACHE
    try:
        file_key = get_file_key(filepath)
        if file_key in _DHASH_CACHE:
            return _DHASH_CACHE[file_key]
            
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, img = cap.read()
            cap.release()
            if not ret or img is None: return None
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return None
            
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        h = (gray[:, 1:] > gray[:, :-1]).flatten()
        _DHASH_CACHE[file_key] = h
        return h
    except:
        return None

@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    try:
        data = request.json or {}
        filepath = data.get('path')
        if not filepath:
            return jsonify({"duplicate": False, "sharpness": 0.0}), 200
            
        real_path = find_relocated_file(filepath)
        if not real_path or not os.path.exists(real_path):
            return jsonify({"duplicate": False, "sharpness": 0.0}), 200
        filepath = real_path
            
        path_obj = Path(filepath)
        parent_dir = path_obj.parent
        
        current_sharpness = 0.0
        try:
            current_sharpness = calculate_sharpness(filepath)
        except: pass
        
        current_hash = None
        try:
            current_hash = calculate_dhash(filepath)
        except: pass
        
        if current_hash is None:
            return jsonify({"sharpness": current_sharpness, "duplicate": None})
            
        valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
        duplicate_info = None
        
        if parent_dir.exists():
            for other_file in parent_dir.iterdir():
                try:
                    if not other_file.is_file() or other_file.name == path_obj.name: continue
                    if other_file.suffix.lower() not in valid_exts: continue
                    
                    other_hash = calculate_dhash(str(other_file))
                    if other_hash is not None and len(other_hash) == len(current_hash):
                        hamming_dist = np.count_nonzero(current_hash != other_hash)
                        similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
                        if similarity >= 85.0:
                            duplicate_info = {
                                "duplicate": True,
                                "path": str(other_file),
                                "similarity": similarity
                            }
                            break
                except: pass
                
        return jsonify({
            "sharpness": current_sharpness,
            "duplicate": duplicate_info["duplicate"] if duplicate_info else False,
            "duplicate_info": duplicate_info
        })
    except Exception as e:
        return jsonify({"sharpness": 0.0, "duplicate": False, "error": str(e)}), 200, 200
        filepath = real_path
            
        path_obj = Path(filepath)
        parent_dir = path_obj.parent
        
        current_sharpness = calculate_sharpness(filepath)
        current_hash = calculate_dhash(filepath)
        
        if current_hash is None:
            return jsonify({"sharpness": current_sharpness, "duplicate": None})
            
        valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
        duplicate_info = None
        
        for other_file in parent_dir.iterdir():
            if not other_file.is_file() or other_file.name == path_obj.name: continue
            if other_file.suffix.lower() not in valid_exts: continue
            
            other_hash = calculate_dhash(str(other_file))
            if other_hash is not None and len(other_hash) == len(current_hash):
                hamming_dist = np.count_nonzero(current_hash != other_hash)
                similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
                
                if similarity >= 75.0:
                    other_sharpness = calculate_sharpness(str(other_file))
                    is_better = current_sharpness >= other_sharpness
                    duplicate_info = {
                        "other_name": other_file.name,
                        "other_path": str(other_file),
                        "similarity": similarity,
                        "other_sharpness": other_sharpness,
                        "is_current_better": is_better
                    }
                    break
                    
        return jsonify({
            "sharpness": current_sharpness,
            "duplicate": duplicate_info
        })
    except Exception as e:
        return jsonify({"sharpness": 100.0, "duplicate": None})


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    path_obj = Path(filepath)
    is_video = path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]
    faces_data = []
    
    
    force_reanalyze = data.get('force', False) or is_video or (data.get('timestamp') is not None)
    if not force_reanalyze and filepath in faces_cache:
        return jsonify({"faces": faces_cache[filepath]})
        
    try:
        timestamp_in = data.get('timestamp')
        timestamp = 0.0
        
        if is_video:
            cap = cv2.VideoCapture(str(filepath))
            fps = cap.get(cv2.CAP_PROP_FPS)
            img = None
            if timestamp_in is not None:
                timestamp = float(timestamp_in)
                if fps > 0:
                    target_frame = max(0, int(timestamp * fps))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, img = cap.read()
                else:
                    ret = False
                if not ret or img is None:
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                    ret, frame = cap.read()
                    if ret: img = frame
                # Windows DirectShow fallback for accurate seeking if black frame
                if img is None:
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                    ret, frame = cap.read()
                    if ret: img = frame
            else:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                target_frame = 0
                if frame_count > 10:
                    target_frame = frame_count // 2
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                if ret: img = frame
                if fps > 0: timestamp = target_frame / fps
            cap.release()
            
            # Si el video falló por completo, lanzamos error en vez de "0 caras"
            if img is None:
                return jsonify({"error": "No se pudo leer el fotograma del vídeo (Windows Codec Error)"}), 500
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
        if img is not None:
            height, width, _ = img.shape
            
        if img is not None and detector is not None and recognizer is not None:
            detector.setInputSize((width, height))
            detector.setScoreThreshold(0.55)
            h_f, w_f = img.shape[:2]
            detector.setInputSize((w_f, h_f))
            _, faces = detector.detect(img)
            
            overrides = load_overrides()
            file_key = get_file_key(filepath)
            file_overrides = overrides.get(file_key, [])
            
            if faces is not None:
                for face in faces:
                    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    x, y = max(0, x), max(0, y)
                    w, h = min(w, width - x), min(h, height - y)
                    
                    identity_name = "Desconocido"
                    confidence_str = ""
                    current_box = [x, y, w, h]
                    
                    # 1. Chequear Memoria Absoluta
                    override_match = None
                    for ov in file_overrides:
                        ov_box = [ov['x'], ov['y'], ov['width'], ov['height']]
                        if iou(current_box, ov_box) > 0.4:
                            override_match = ov['identity']
                            x, y, w, h = ov['x'], ov['y'], ov['width'], ov['height']
                            break
                            
                    if override_match:
                        if override_match in ["Ignorar_Irrelevante", "Falso_Positivo"]:
                            continue
                        identity_name = override_match
                        confidence_str = "100.0%"
                    else:
                        # 2. IA Inference
                        try:
                            aligned = recognizer.alignCrop(img, face)
                            feature = recognizer.feature(aligned)
                            best_match = None
                            best_score = 0
                            for db_id, data_dict in known_faces.items():
                                centroid = data_dict.get('centroid')
                                if centroid is not None:
                                    score = get_cosine_similarity(feature[0], centroid)
                                    if score > best_score:
                                        best_score = score
                                        best_match = db_id
                            
                            if best_match and best_score > 0.45:
                                if best_match.startswith("Falso_Positivo"):
                                    continue
                                identity_name = best_match
                                confidence_str = f"{(best_score * 100):.1f}%"
                            elif best_match and best_score > 0.30:
                                current_folder = path_obj.parent.name
                                owner_folder = path_obj.parent.parent.name if current_folder == "_Dudosos" else current_folder
                                if best_match == owner_folder:
                                    identity_name = f"? {best_match}"
                                    confidence_str = f"{(best_score * 100):.1f}% (Dudoso)"
                        except:
                            pass
                    
                    faces_data.append({
                        "x": x, "y": y, "width": w, "height": h,
                        "img_width": width, "img_height": height,
                        "identity": identity_name,
                        "confidence": confidence_str,
                        "feature": feature[0] if ('feature' in locals() and feature is not None) else None
                    })
            
            # Inferencia por Propietario de Carpeta y Rescate
            folder_owner = Path(filepath).parent.name
            is_valid_owner = folder_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Conocidos", "Ignorar"]
            
            if is_valid_owner and len(faces_data) > 0:
                owner_assigned = any(f["identity"] == folder_owner for f in faces_data)
                if not owner_assigned:
                    best_idx = -1
                    best_owner_score = -1.0
                    owner_centroid = known_faces.get(folder_owner, {}).get('centroid')
                    
                    for idx, f in enumerate(faces_data):
                        if f["identity"] == "Desconocido":
                            if owner_centroid is not None and f.get("feature") is not None:
                                score = get_cosine_similarity(f["feature"], owner_centroid)
                                if score > best_owner_score:
                                    best_owner_score = score
                                    best_idx = idx
                                    
                    if best_idx == -1:
                        for idx, f in enumerate(faces_data):
                            if f["identity"] == "Desconocido":
                                best_idx = idx
                                break
                                
                    if best_idx != -1:
                        faces_data[best_idx]["identity"] = folder_owner
                        faces_data[best_idx]["confidence"] = "✨ 100.0% (Propietario del Álbum)"
            
            elif is_valid_owner and len(faces_data) == 0 and width > 0 and height > 0:
                # Recuadro de rescate automático para fotos sin caras detectadas dentro de un álbum
                faces_data.append({
                    "x": int(width * 0.15),
                    "y": int(height * 0.15),
                    "width": int(width * 0.70),
                    "height": int(height * 0.70),
                    "img_width": width,
                    "img_height": height,
                    "identity": folder_owner,
                    "confidence": "✨ Recuadro de Rescate (Álbum)"
                })
                        
            # Limpiar features de la respuesta JSON
            for f in faces_data:
                if "feature" in f: del f["feature"]

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})
        
    return jsonify({"faces": faces_data, "timestamp": timestamp})

@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    orig_path = Path(filepath)
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            return jsonify({"error": "Dataset protegido: Las fotos del dataset manual original no pueden eliminarse físicamente."}), 403
    except ValueError:
        pass
        
    try:
        safe_remove_file(orig_path)
        clear_gallery_cache()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rename_group', methods=['POST'])
def api_rename_group():
    data = request.json
    cat = data.get('cat')
    ident = data.get('ident')
    new_name = data.get('new_name')
    new_cat = data.get('new_cat', 'Conocidos')
    
    if not cat or not ident or not new_name:
        return jsonify({"error": "Parámetros insuficientes"}), 400
        
    src_dir_res = RESULTADOS_DIR / cat / ident
    src_dir_fotos = FOTOS_DIR / cat / ident
    
    if not src_dir_res.exists() and not src_dir_fotos.exists():
        return jsonify({"error": "Carpeta de grupo no encontrada"}), 404
        
    target_dir_res = RESULTADOS_DIR / new_cat / new_name
    target_dir_res.mkdir(parents=True, exist_ok=True)
    
    target_dir_fotos = FOTOS_DIR / new_cat / new_name
    
    moved_count = 0
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    
    # Mover de Resultados
    if src_dir_res.exists():
        for file_path in src_dir_res.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                target_file = target_dir_res / file_path.name
                counter = 1
                while target_file.exists():
                    target_file = target_dir_res / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1
                try:
                    shutil.move(str(file_path), str(target_file))
                    moved_count += 1
                except Exception as e:
                    try:
                        safe_move_file(file_path, target_file)
                        moved_count += 1
                    except:
                        pass
        try:
            os.rmdir(str(src_dir_res))
        except:
            pass

    # Mover de Fotos (dataset original) si existe
    if src_dir_fotos.exists():
        target_dir_fotos.mkdir(parents=True, exist_ok=True)
        for file_path in src_dir_fotos.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                target_file = target_dir_fotos / file_path.name
                counter = 1
                while target_file.exists():
                    target_file = target_dir_fotos / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1
                try:
                    import shutil
                    safe_move_file(file_path, target_file)
                    moved_count += 1
                except:
                    pass
        try:
            os.rmdir(str(src_dir_fotos))
        except:
            pass

    # Reaprendizaje Activo de la Persona (Actualización de Centroide en Caché)
    try:
        new_feats = []
        for file_path in target_dir_res.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
                img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img_al is not None and detector is not None and recognizer is not None:
                    h_al, w_al, _ = img_al.shape
                    detector.setInputSize((w_al, h_al))
                    _, faces_al = detector.detect(img_al)
                    if faces_al is not None and len(faces_al) > 0:
                        aligned = recognizer.alignCrop(img_al, faces_al[0])
                        feat = recognizer.feature(aligned)[0]
                        new_feats.append(feat)
                        
        if len(new_feats) > 0:
            avg_new = np.mean(new_feats, axis=0)
            if new_name in known_faces and 'centroid' in known_faces[new_name]:
                old_cent = known_faces[new_name]['centroid']
                known_faces[new_name]['centroid'] = 0.7 * old_cent + 0.3 * avg_new
            else:
                known_faces[new_name] = {'centroid': avg_new, 'names': []}
                
            with open(CACHE_FILE, 'wb') as f_cache:
                pickle.dump(known_faces, f_cache)
    except Exception as ex_retrain:
        print(f"Aviso de reentrenamiento: {ex_retrain}")
    
    clear_gallery_cache()
    return jsonify({"success": True, "count": moved_count})





import subprocess
import sys


@app.route('/api/recluster_unknowns', methods=['POST'])
def start_recluster():
    subprocess.Popen([sys.executable, "recluster.py"])
    return jsonify({"success": True})

@app.route('/api/recluster_status')
def get_recluster_status():
    status_file = Path("recluster_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})

@app.route('/api/auto_merge', methods=['POST'])
def start_auto_merge():
    # Lanzar auto_merge.py en background
    subprocess.Popen([sys.executable, "auto_merge.py"])
    return jsonify({"success": True})

@app.route('/api/auto_merge_status')
def get_auto_merge_status():
    status_file = Path("auto_merge_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})

@app.route('/api/mass_cleanup', methods=['POST'])
def api_mass_cleanup():
    global _GALLERY_CACHE
    promoted = 0
    try:
        from deep_auto_classify_all import run_deep_classify
        run_deep_classify(threshold=0.65)
        if Path("deep_classify_status.json").exists():
            with open("deep_classify_status.json", "r", encoding="utf-8") as sf:
                st_data = json.load(sf)
                promoted = st_data.get("details", {}).get("promoted", 0)
    except Exception as ex:
        print("Error in mass_cleanup execution:", ex)
        
    _GALLERY_CACHE = None
    return jsonify({"success": True, "moved_count": promoted, "count": promoted})


def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    if not filepath or not os.path.exists(filepath):
        return None
    orig_path = Path(filepath)
    target_path = orig_path
    is_manual_source = False
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            is_manual_source = True
    except ValueError:
        pass
        
    overrides = load_overrides()
    file_key = get_file_key(filepath)
    
    # Memoria Absoluta Guardado
    if face_data:
        if file_key not in overrides: overrides[file_key] = []
        updated = False
        face_box = [face_data['x'], face_data['y'], face_data['width'], face_data['height']]
        for ov in overrides[file_key]:
            ov_box = [ov['x'], ov['y'], ov['width'], ov['height']]
            if iou(face_box, ov_box) > 0.4:
                ov['identity'] = new_identidad
                ov['x'] = face_data['x']
                ov['y'] = face_data['y']
                ov['width'] = face_data['width']
                ov['height'] = face_data['height']
                updated = True
                break
        if not updated:
            overrides[file_key].append({
                'x': face_data['x'], 'y': face_data['y'], 
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad
            })
        save_overrides(overrides)
        
        # Actualizar la caché de caras instantáneamente para la UI
        if filepath not in faces_cache:
            faces_cache[filepath] = []
            
        updated_cache = False
        for c_face in faces_cache[filepath]:
            c_box = [c_face['x'], c_face['y'], c_face['width'], c_face['height']]
            if iou(face_box, c_box) > 0.4:
                c_face['identity'] = new_identidad
                c_face['confidence'] = "100.0"
                c_face['is_manual'] = True
                updated_cache = True
                break
                
        if not updated_cache:
            faces_cache[filepath].append({
                'x': face_data['x'], 'y': face_data['y'],
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad, 'confidence': "100.0", 'is_manual': True
            })
            
        try:
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
        except Exception as e:
            print("Failed to save faces cache:", e)

        
    # Ultra-Fast Active Learning (Direct Crop Feature Extraction)
    if new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"] and face_data:
        try:
            file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
            img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img_al is not None:
                h_al, w_al, _ = img_al.shape
                x1 = max(0, int(face_data['x']))
                y1 = max(0, int(face_data['y']))
                x2 = min(w_al, x1 + int(face_data['width']))
                y2 = min(h_al, y1 + int(face_data['height']))
                
                if (x2 - x1) > 10 and (y2 - y1) > 10:
                    crop = img_al[y1:y2, x1:x2]
                    resized_crop = cv2.resize(crop, (112, 112))
                    feature = recognizer.feature(resized_crop)
                    dict_key = new_identidad
                    if dict_key in known_faces and 'centroid' in known_faces[dict_key]:
                        old_centroid = known_faces[dict_key]['centroid']
                        new_centroid = old_centroid * 0.85 + feature[0] * 0.15
                        new_centroid = new_centroid / np.linalg.norm(new_centroid)
                        known_faces[dict_key]['centroid'] = new_centroid
                    else:
                        known_faces[dict_key] = {'centroid': feature[0], 'names': [orig_path.name]}
                    with open(CACHE_FILE, 'wb') as cf:
                        pickle.dump(known_faces, cf)
        except Exception as e:
            print("AL Fast Error:", e)

    # File Management
    target_path = orig_path
    if new_categoria != "Ignorar" and new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
        if is_manual_source:
            target_dir = FOTOS_DIR / new_categoria / new_identidad
        else:
            target_dir = RESULTADOS_DIR / new_categoria / new_identidad
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if orig_path.parent.resolve() == target_dir.resolve():
            target_path = orig_path
        else:
            orig_ino = os.stat(str(orig_path)).st_ino
            existing_link = None
            for f in target_dir.iterdir():
                if f.is_file() and os.stat(str(f)).st_ino == orig_ino:
                    existing_link = f
                    break
                    
            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))
                except Exception:
                    try:
                        import shutil
                        shutil.copy2(str(orig_path), str(target_path))
                    except Exception:
                        pass
            
    # Garbage Collector
    should_garbage_collect = False
    if target_path != orig_path:
        try:
            overrides = load_overrides()
            file_key = get_file_key(str(orig_path))
            other_faces_same_person = False
            has_other_people = False
            
            if file_key in overrides:
                for ov in overrides[file_key]:
                    if ov.get('identity') == orig_path.parent.name and (face_data is None or iou([ov['x'], ov['y'], ov['width'], ov['height']], face_box) <= 0.4):
                        other_faces_same_person = True
                    elif ov.get('identity') not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
                        has_other_people = True
            
            if not other_faces_same_person:
                file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
                img_gc = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img_gc is not None:
                    h_gc, w_gc, _ = img_gc.shape
                    detector.setInputSize((w_gc, h_gc))
                    _, faces_gc = detector.detect(img_gc)
                    if faces_gc is not None:
                        for f in faces_gc:
                            f_box = [int(f[0]), int(f[1]), int(f[2]), int(f[3])]
                            if face_data and iou(f_box, face_box) > 0.4:
                                continue
                                
                            aligned = recognizer.alignCrop(img_gc, f)
                            feature = recognizer.feature(aligned)
                            if feature is None: continue
                            
                            best_score = 0
                            best_match = None
                            for db_id, data_dict in known_faces.items():
                                centroid = data_dict.get('centroid')
                                if centroid is not None:
                                    score = get_cosine_similarity(feature[0], centroid)
                                    if score > best_score:
                                        best_score = score
                                        best_match = db_id
                                        
                            if best_match == orig_path.parent.name and best_score > 0.30:
                                other_faces_same_person = True
                                break
                                
            if not other_faces_same_person:
                should_garbage_collect = True
                
        except Exception as e:
            print("GC Error:", e)

    if should_garbage_collect:
        try:
            safe_remove_file(orig_path)
        except Exception:
            try:
                with open(PENDING_DELETIONS_FILE, 'a') as f:
                    f.write(str(orig_path) + '\n')
            except Exception:
                pass
                
    if str(target_path) != filepath and filepath in faces_cache:
        faces_cache[str(target_path)] = faces_cache.pop(filepath)
        try:
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
        except Exception as e:
            print("Failed to save faces cache:", e)
            
    return str(target_path)




@app.route('/api/remove_from_folder', methods=['POST'])
def remove_from_folder():
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        p_obj = Path(filepath)
        
        # Save manual override to Desconocidos
        overrides = load_overrides()
        file_key = get_file_key(filepath)
        overrides[file_key] = [{
            'x': 0, 'y': 0, 'width': 0, 'height': 0,
            'identity': 'Desconocida'
        }]
        save_overrides(overrides)
        
        # Invalidate gallery cache
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        # Move physical file if in Resultados
        if p_obj.exists() and RESULTADOS_DIR in p_obj.parents:
            target_dir = RESULTADOS_DIR / 'Personas Sin Nombre' / 'Desconocidos'
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / p_obj.name
            if target_path.exists() and target_path != p_obj:
                target_path = target_dir / f"{p_obj.stem}_removed{p_obj.suffix}"
            try:
                shutil.move(str(p_obj), str(target_path))
            except Exception as me:
                print("Physical move error:", me)
                
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/detect_deep', methods=['POST'])
def detect_deep():
    data = request.json
    filepath = data.get('path')
    if not filepath:
        return jsonify({"error": "File not found"}), 404
        
    p_obj = Path(filepath)
    if not p_obj.exists():
        alt_p = Path(filepath.replace('/', '\\')) if '/' in filepath else Path(filepath.replace('\\', '/'))
        if alt_p.exists():
            p_obj = alt_p
        else:
            return jsonify({"error": "File not found"}), 404
            
    filepath = str(p_obj)
        
    try:
        file_bytes = np.fromfile(filepath, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Could not read image"}), 400
            
        h, w = img.shape[:2]
        
        # Deep Scan: lower score threshold and NMS threshold
        # Default is 0.9, we drop it to 0.5 to find "hidden" faces
        try:
            deep_detector = cv2.FaceDetectorYN.create(str(APP_DIR / "models" / "face_detection_yunet.onnx"), "", (w, h), score_threshold=0.5, nms_threshold=0.3)
            _, faces = deep_detector.detect(img)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
        if faces is not None:
            new_faces = []
            for face in faces:
                x, y, w_f, h_f = map(int, face[:4])
                conf = face[-1]
                new_faces.append({
                    "x": x, "y": y, "width": w_f, "height": h_f,
                    "identity": "Desconocida",
                    "confidence": f"{conf*100:.1f}",
                    "is_manual": False
                })
            
            # Update cache!
            faces_cache[filepath] = new_faces
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
            
            return jsonify({"faces": new_faces})
        else:
            return jsonify({"faces": []})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/correct', methods=['POST'])
def api_correct():
    data = request.json
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
    
    try:
        # Perform instant file move and memory update
        target_path = apply_correction_to_file(filepath, new_categoria, new_identidad, face_data)
        
        # Non-blocking background thread for heavy disk persistence
        def bg_save():
            try:
                process_pending_deletions()
            except Exception as e:
                print("BG Save error:", e)
                
        import threading
        threading.Thread(target=bg_save, daemon=True).start()
        
        return jsonify({"success": True, "new_path": str(target_path) if target_path else filepath})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/stats')
def api_stats():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    total = 0
    manual_user = 0
    ia_verified = 0
    dudosos = 0
    pendientes = 0
    breakdown = {}
    
    overrides = load_overrides()
    
    for cat, idents in (_GALLERY_CACHE or {}).items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            
            if cat == 'Personas Sin Nombre':
                pendientes += count
            elif '_Dudosos' in ident or cat == 'Revision_Interactiva':
                dudosos += count
            else:
                for item in items:
                    p = item.get('path', '')
                    src = item.get('source', '')
                    if p in overrides or 'Manual' in src or 'Dataset' in src:
                        manual_user += 1
                    else:
                        ia_verified += 1
                
                label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
                breakdown[label] = breakdown.get(label, 0) + count
                
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))
                
    return jsonify({
        "total": total,
        "manual_user": manual_user,
        "ia_verified": ia_verified,
        "dudosos": dudosos,
        "pendientes": pendientes,
        "clasificadas": manual_user + ia_verified,
        "breakdown": breakdown_sorted
    }), 400
        
    total = 0
    clasificadas = 0
    pendientes = 0
    breakdown = {}
    
    for cat, idents in _GALLERY_CACHE.items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            if cat == 'Personas Sin Nombre' or cat == 'Resultados':
                pendientes += count
            else:
                clasificadas += count
                # Build breakdown
                label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
                breakdown[label] = breakdown.get(label, 0) + count
                
    # Sort breakdown by count descending
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))
                
    return jsonify({
        "total": total,
        "clasificadas": clasificadas,
        "pendientes": pendientes,
        "breakdown": breakdown_sorted
    })


CONFIDENCE_CACHE_FILE = Path("confidence_cache.pkl")
_CONFIDENCE_CACHE = {}
if CONFIDENCE_CACHE_FILE.exists():
    try:
        import pickle
        with open(CONFIDENCE_CACHE_FILE, 'rb') as f:
            _CONFIDENCE_CACHE = pickle.load(f)
    except: pass

@app.route('/api/clear_confidence_cache', methods=['POST'])
def api_clear_confidence_cache():
    global _CONFIDENCE_CACHE
    _CONFIDENCE_CACHE = {}
    if CONFIDENCE_CACHE_FILE.exists():
        try:
            CONFIDENCE_CACHE_FILE.unlink()
        except: pass
    return jsonify({"success": True})

def save_confidence_cache():
    try:
        import pickle
        with open(CONFIDENCE_CACHE_FILE, 'wb') as f:
            pickle.dump(_CONFIDENCE_CACHE, f)
    except: pass

@app.route('/api/start_smart_clean', methods=['POST'])
def start_smart_clean():
    subprocess.Popen([sys.executable, "smart_clean_worker.py"])
    return jsonify({"success": True})

@app.route('/api/smart_clean_status')
def get_smart_clean_status():
    status_file = Path("smart_clean_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})

@app.route('/api/pending_sorted')
def api_pending_sorted():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        load_gallery_cache()
        
    items_to_sort = []
    
    if 'Personas Sin Nombre' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Personas Sin Nombre'].items():
            for item in items:
                items_to_sort.append(item)
                
    if 'Resultados' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Resultados'].items():
            for item in items:
                items_to_sort.append(item)
                
    # Solamente leer de la cache, NO calcular nada aqui. El script en background ya lo hizo.
    for item in items_to_sort:
        file_key = get_file_key(item['path'])
        item['confidence'] = _CONFIDENCE_CACHE.get(file_key, 0.0)
        
    items_to_sort.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
    return jsonify({"items": items_to_sort})


import hashlib

import gc, time, shutil, os

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False


THUMBNAILS_DIR = APP_DIR / ".thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

def generate_thumbnail(original_path, max_size=280):
    try:
        path_str = str(original_path)
        path_hash = hashlib.md5(path_str.encode('utf-8')).hexdigest()
        thumb_path = THUMBNAILS_DIR / f"{path_hash}.webp"
        
        if thumb_path.exists():
            return str(thumb_path)
            
        is_video = path_str.lower().endswith((".mp4", ".mov", ".avi"))
        img = None
        
        if is_video:
            cap = cv2.VideoCapture(path_str)
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, frame = cap.read()
            if ret: img = frame
            cap.release()
        else:
            file_bytes = np.fromfile(path_str, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
        if img is None:
            return None
            
        # Resize maintaining aspect ratio
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        # Save as webp for maximum compression and speed
        cv2.imwrite(str(thumb_path), img, [cv2.IMWRITE_WEBP_QUALITY, 60])
        return str(thumb_path)
    except Exception as e:
        print("Thumbnail Error:", e)
        return None

@app.route('/api/thumbnail')
def api_thumbnail():
    path_param = request.args.get('path')
    if not path_param:
        return "Falta path", 400
    
    thumb = generate_thumbnail(path_param)
    if thumb and os.path.exists(thumb):
        res = send_file(thumb, mimetype='image/webp')
        res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return res
    
    if os.path.exists(path_param):
        res = send_file(path_param)
        res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return res
    return "No encontrado", 404



@app.route('/api/correct_bulk', methods=['POST'])
def api_correct_bulk():
    data = request.json
    paths = data.get('paths', [])
    new_identity = data.get('new_identity', '')
    
    if not paths or not new_identity:
        return jsonify({"success": False, "error": "Faltan datos"})
        
    global _GALLERY_CACHE
    overrides = load_overrides()
    
    # Check if folder exists
    dest_dir = DATASET_DIR / new_identity
    if new_identity != 'Ignorar' and not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        if _GALLERY_CACHE is not None and 'Conocidos' in _GALLERY_CACHE:
            if new_identity not in _GALLERY_CACHE['Conocidos']:
                _GALLERY_CACHE['Conocidos'][new_identity] = []
                
    success_count = 0
    for file_path in paths:
        try:
            # Add to overrides
            file_key = get_file_key(file_path)
            
            if file_key not in overrides:
                overrides[file_key] = []
                
            # Assume we only reassign the primary face (idx 0) for bulk actions 
            # or we reassign all faces in that image if it's a false positive etc.
            # But wait, usually bulk is used on images that have ONE main face, 
            # or the user wants to reassign the first face. Let's reassign idx 0.
            
            # Find if there is an override for face_idx 0
            idx_found = False
            for ov in overrides[file_key]:
                if ov['face_idx'] == 0:
                    ov['identity'] = new_identity
                    ov['is_manual'] = True
                    idx_found = True
                    break
            
            if not idx_found:
                overrides[file_key].append({
                    "face_idx": 0,
                    "identity": new_identity,
                    "is_manual": True
                })
                
            # If identity matches a known person, copy the image to their dataset folder
            # to reinforce learning (as requested by user previously)
            if new_identity != 'Ignorar' and new_identity != 'Desconocido' and not new_identity.startswith('IA '):
                src_path = Path(file_path)
                if src_path.exists():
                    dest_file = dest_dir / src_path.name
                    if not dest_file.exists():
                        shutil.copy2(src_path, dest_file)
            
            success_count += 1
        except Exception as e:
            print(f"Error bulk correcting {file_path}: {e}")
            
    save_overrides(overrides)
    
    # Reload gallery to reflect changes
    load_gallery_cache()
    
    return jsonify({"success": True, "count": success_count})

@app.route('/api/scan_video', methods=['POST'])
def api_scan_video():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    path_obj = Path(filepath)
    if path_obj.suffix.lower() not in [".mp4", ".mov", ".avi"]:
        return jsonify({"error": "Not a video"}), 400
        
    try:
        cap = cv2.VideoCapture(str(filepath))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        results = {}
        
        # Scan 1 frame per second
        for sec in range(0, int(duration) + 1):
            target_frame = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
                
            h, w, _ = frame.shape
            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            
            if faces is not None:
                for f in faces:
                    aligned = recognizer.alignCrop(frame, f)
                    feature = recognizer.feature(aligned)
                    if feature is None: continue
                    
                    best_score = 0
                    best_match = None
                    for db_id, data_dict in known_faces.items():
                        centroid = data_dict.get('centroid')
                        if centroid is not None:
                            score = get_cosine_similarity(feature[0], centroid)
                            if score > best_score:
                                best_score = score
                                best_match = db_id
                                
                    if best_match and best_score > 0.60:
                        if best_match not in results:
                            results[best_match] = []
                        results[best_match].append(sec)
                        
        cap.release()
        
        # Format results
        final_results = []
        for ident, secs in results.items():
            if ident.startswith("Falso_Positivo") or ident.startswith("Ignorar_Irrelevante"):
                continue
            final_results.append({
                "identity": ident,
                "seconds": sorted(list(set(secs)))
            })
            
        return jsonify({"success": True, "detections": final_results})
        
    except Exception as e:
        print("Video Scan Error:", e)
        return jsonify({"error": str(e)}), 500

def find_avatar_image(target_dir):
    valid_exts = {".jpg", ".jpeg", ".png"}
    if not target_dir: return None
    if isinstance(target_dir, str): target_dir = Path(target_dir)
    if not target_dir.exists(): return None
    if target_dir.is_file() and target_dir.suffix.lower() in valid_exts:
        return str(target_dir.resolve())
    if target_dir.is_dir():
        for root, dirs, files in os.walk(str(target_dir)):
            for f in files:
                if Path(f).suffix.lower() in valid_exts:
                    full_p = os.path.join(root, f)
                    try:
                        if os.path.getsize(full_p) > 1024:
                            return full_p
                    except:
                        pass
    return None

@app.route('/api/person_avatar')
def api_person_avatar():
    cat = request.args.get('cat')
    ident = request.args.get('ident')
    if not cat or not ident:
        return "Missing params", 400
        
    target_dir = Path('Resultados') / cat / ident
    if not target_dir.exists():
        target_dir = FOTOS_DIR / cat / ident
        
    if target_dir is None or not target_dir.exists():
        return "Not found", 404
        
    # Find first valid image recursively
    first_img_path = find_avatar_image(RESULTADOS_DIR / cat / ident)
    if not first_img_path:
        first_img_path = find_avatar_image(FOTOS_DIR / cat / ident)
            
    if not first_img_path:
        return "No image found", 404
        
    # Look up face in cache
    face_box = None
    overrides = load_overrides()
    file_key = get_file_key(first_img_path)
    
    if file_key in overrides:
        for ov in overrides[file_key]:
            if ov.get('identity') == ident:
                face_box = ov
                break
                
    if not face_box and first_img_path in faces_cache:
        for fc in faces_cache[first_img_path]:
            if fc.get('identity') == ident:
                face_box = fc
                break
        if not face_box and len(faces_cache[first_img_path]) > 0:
            face_box = faces_cache[first_img_path][0]
                
    try:
        file_bytes = np.fromfile(first_img_path, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: return "Bad image", 404
        
        cropped = None
        if face_box:
            try:
                x, y, w, h = int(face_box['x']), int(face_box['y']), int(face_box['width']), int(face_box['height'])
                pad_x = int(w * 0.2)
                pad_y = int(h * 0.2)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(img.shape[1], x + w + pad_x)
                y2 = min(img.shape[0], y + h + pad_y)
                if x2 > x1 and y2 > y1:
                    cropped = img[y1:y2, x1:x2]
            except:
                pass
                
        if cropped is None or cropped.size == 0:
            h, w = img.shape[:2]
            sz = min(h, w)
            cropped = img[h//2 - sz//2 : h//2 + sz//2, w//2 - sz//2 : w//2 + sz//2]
            if cropped.size == 0:
                return "Invalid dimensions", 400
                
        _, buf = cv2.imencode('.jpg', cropped)
        res = Response(buf.tobytes(), mimetype='image/jpeg')
        res.headers['Cache-Control'] = 'public, max-age=86400'
        return res
    except Exception as e:
        print("Avatar error:", e)
        return str(e), 404



@app.route('/api/batch_move', methods=['POST'])
def api_batch_move():
    global _GALLERY_CACHE
    try:
        data = request.json or {}
        files = data.get('files', [])
        target_cat = data.get('target_cat')
        target_ident = data.get('target_ident')
        
        if not files or not target_cat or not target_ident:
            return jsonify({"error": "Parámetros incompletos"}), 400
            
        target_dir = RESULTADOS_DIR / target_cat / target_ident
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        moved_count = 0
        new_features = []
        
        detector = cv2.FaceDetectorYN.create("models/face_detection_yunet_2023mar.onnx", "", (320, 320))
        recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface_2021dec.onnx", "")
        
        overrides = load_overrides()
        
        for fpath in files:
            p_obj = Path(fpath)
            if p_obj.exists():
                dest = target_dir / p_obj.name
                if dest.exists() and dest != p_obj:
                    dest = target_dir / f"moved_{p_obj.name}"
                try:
                    shutil.move(str(p_obj), str(dest))
                    moved_count += 1
                    
                    file_k = str(dest.resolve())
                    overrides[file_k] = [{
                        'x': 0, 'y': 0, 'width': 0, 'height': 0,
                        'identity': target_ident
                    }]
                    
                    img = cv2.imread(str(dest))
                    if img is not None:
                        h, w = img.shape[:2]
                        detector.setInputSize((w, h))
                        _, faces = detector.detect(img)
                        if faces is not None and len(faces) > 0:
                            aligned = recognizer.alignCrop(img, faces[0])
                            feat = recognizer.feature(aligned)
                            new_features.append(feat)
                except Exception as e:
                    print(f"Error moving {fpath}:", e)
                    
        save_overrides(overrides)
        
        if new_features:
            try:
                centroids = {}
                if os.path.exists('centroids.pkl'):
                    with open('centroids.pkl', 'rb') as cfile:
                        centroids = pickle.load(cfile)
                        
                key = (target_cat, target_ident)
                existing = centroids.get(key)
                all_f = new_features + ([existing] if existing is not None else [])
                avg_f = np.mean(all_f, axis=0)
                avg_f = avg_f / np.linalg.norm(avg_f)
                centroids[key] = avg_f
                
                with open('centroids.pkl', 'wb') as cfile:
                    pickle.dump(centroids, cfile)
                print(f"✓ Re-trained AI centroid for {target_ident} with {len(new_features)} moved faces!")
            except Exception as e:
                print("Centroid retrain error:", e)
                
        _GALLERY_CACHE = None
        
        return jsonify({
            "status": "success",
            "moved": moved_count,
            "retrained_faces": len(new_features)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/duplicates_scan')
def api_duplicates_scan():
    try:
        import hashlib
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        size = fp.stat().st_size
                        if size < 5000: continue
                        with open(fp, 'rb') as fh:
                            chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append({'path': str(fp), 'size': size, 'name': fp.name})
                    except: pass
                        
        groups = []
        total_waste_bytes = 0
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                group_waste = sum(f['size'] for f in file_list[1:])
                total_waste_bytes += group_waste
                groups.append({
                    'hash': h_val,
                    'files': file_list,
                    'waste_mb': round(group_waste / (1024 * 1024), 2)
                })
                
        groups.sort(key=lambda x: x['waste_mb'], reverse=True)
        return jsonify({
            'groups': groups,
            'total_waste_mb': round(total_waste_bytes / (1024 * 1024), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/duplicates_clean', methods=['POST'])
def api_duplicates_clean():
    try:
        data = request.json or {}
        target_hash = data.get('hash')
        clean_all = data.get('clean_all', False)
        import hashlib
        freed_bytes = 0
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        size = fp.stat().st_size
                        if size < 5000: continue
                        with open(fp, 'rb') as fh:
                            chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append(fp)
                    except: pass
                    
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                if clean_all or h_val == target_hash:
                    for dup_p in file_list[1:]:
                        try:
                            freed_bytes += dup_p.stat().st_size
                            dup_p.unlink()
                        except Exception as de: print("Error deleting duplicate:", de)
                            
        return jsonify({'success': True, 'freed_mb': round(freed_bytes / (1024 * 1024), 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/similar_scan')
def api_similar_scan():
    try:
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        image_files = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    image_files.append(fp)
                    
        prefixes = {}
        for fp in image_files:
            prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
            if prefix not in prefixes: prefixes[prefix] = []
            prefixes[prefix].append(fp)
            
        groups = []
        for pref, f_list in prefixes.items():
            if len(f_list) > 1:
                evaluated = []
                for fp in f_list:
                    score = 0.0
                    try:
                        img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            score = cv2.Laplacian(img, cv2.CV_64F).var()
                    except: pass
                    evaluated.append({
                        'path': str(fp),
                        'name': fp.name,
                        'sharpness_score': round(score, 1)
                    })
                evaluated.sort(key=lambda x: x['sharpness_score'], reverse=True)
                for idx, ev in enumerate(evaluated):
                    ev['is_sharpest'] = (idx == 0)
                groups.append({'group_id': pref, 'files': evaluated})
                
        groups = groups[:15]
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/similar_clean', methods=['POST'])
def api_similar_clean():
    try:
        data = request.json or {}
        group_id = data.get('group_id')
        if not group_id: return jsonify({'error': 'Falta group_id'}), 400
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        f_list = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
                    if prefix == group_id: f_list.append(fp)
                        
        if len(f_list) > 1:
            evaluated = []
            for fp in f_list:
                score = 0.0
                try:
                    img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                    if img is not None: score = cv2.Laplacian(img, cv2.CV_64F).var()
                except: pass
                evaluated.append((score, fp))
            evaluated.sort(key=lambda x: x[0], reverse=True)
            for _, dup_p in evaluated[1:]:
                try: dup_p.unlink()
                except Exception as de: print("Error deleting burst file:", de)
                    
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


CONFIG_FILE = Path("config.json")

def load_system_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"mode": "local", "local_path": r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR", "gdrive_folder_id": "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"}

def save_system_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.json or {}
        mode = data.get('mode', 'local')
        local_path = data.get('local_path')
        gdrive_url_or_id = data.get('gdrive_url_or_id')
        
        cfg = load_system_config()
        cfg['mode'] = mode
        if local_path:
            cfg['local_path'] = local_path
        if gdrive_url_or_id:
            # Extract folder ID if full link was provided
            folder_id = gdrive_url_or_id
            if 'folders/' in gdrive_url_or_id:
                folder_id = gdrive_url_or_id.split('folders/')[1].split('?')[0]
            cfg['gdrive_folder_id'] = folder_id
            
        save_system_config(cfg)
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        return jsonify({"success": True, "config": cfg})
    else:
        return jsonify(load_system_config())

@app.route('/api/delta_sync', methods=['POST'])
def api_delta_sync():
    try:
        cfg = load_system_config()
        adapter = storage_adapters.get_adapter(cfg.get('mode', 'local'), cfg)
        all_files = adapter.list_files()
        unprocessed = state_memory.get_unprocessed_files(all_files)
        
        state_memory.update_delta_sync_time()
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({
            "success": True,
            "total_files": len(all_files),
            "unprocessed_files": len(unprocessed)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


import magic_links

@app.route('/share/<token>')
def view_share_guest(token):
    info = magic_links.get_magic_link_info(token)
    if not info:
        return render_template('share_guest.html', error="Enlace caducado o no válido")
    return render_template('share_guest.html')

@app.route('/api/share/<token>/gallery')
def api_share_guest_gallery(token):
    info = magic_links.get_magic_link_info(token)
    if not info:
        return jsonify({"error": "Enlace no válido"}), 404
        
    category = info['category']
    identity = info['identity']
    
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    items = []
    if category in _GALLERY_CACHE and identity in _GALLERY_CACHE[category]:
        items = _GALLERY_CACHE[category][identity]
        
    return jsonify({
        "category": category,
        "identity": identity,
        "items": items
    })

@app.route('/api/magic_links/create', methods=['POST'])
def api_create_magic_link():
    data = request.json or {}
    category = data.get('category')
    identity = data.get('identity')
    days = data.get('days')
    
    if not category or not identity:
        return jsonify({"error": "Faltan datos"}), 400
        
    token = magic_links.create_magic_link(category, identity, duration_days=days)
    share_url = f"{request.host_url}share/{token}"
    return jsonify({"success": True, "token": token, "share_url": share_url})

@app.route('/api/magic_links/list')
def api_list_magic_links():
    return jsonify({"links": magic_links.list_active_magic_links()})

@app.route('/api/magic_links/revoke', methods=['POST'])
def api_revoke_magic_link():
    data = request.json or {}
    token = data.get('token')
    if token and magic_links.revoke_magic_link(token):
        return jsonify({"success": True})
    return jsonify({"error": "Token no encontrado"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
