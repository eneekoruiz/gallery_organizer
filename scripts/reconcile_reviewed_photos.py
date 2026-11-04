"""Reanalyse unresolved local photos; journal every move and never train from predictions."""
import argparse
import gc
import hashlib
import json
import os
import pickle
import shutil
import tempfile
import time
from collections import Counter
from pathlib import Path

os.environ['SMART_GALLERY_BACKGROUND_TASKS'] = '0'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import cv2
import numpy as np

from app.services.face_learning import normalized_feature, rank_known_identities, update_confirmed_sample, face_rectangle
from app.services.group_album_service import group_albums, is_group_album


def recover_confirmed_samples(profiles, overrides, cache, categories):
    from app.utils.faces import iou
    recovered = 0
    for key, faces in overrides.items():
        for face in faces:
            identity = face.get('identity', '')
            if (not (face.get('is_manual') is True or face.get('provenance') in {'human', 'human_confirmed'})
                    or identity not in categories or is_group_album(identity)):
                continue
            try:
                box = list(face_rectangle(face).values())
                ranked = sorted(((iou(box, list(face_rectangle(c).values())), c)
                                 for c in cache.get(key, []) if c.get('feature') is not None),
                                key=lambda pair: pair[0], reverse=True)
                if not ranked or ranked[0][0] < .65 or (len(ranked) > 1 and ranked[1][0] > .5):
                    continue
                feature = normalized_feature(ranked[0][1]['feature'])
            except (ValueError, TypeError, KeyError):
                continue
            sample_key = key + ':' + json.dumps(box)
            if sample_key in profiles.get(identity, {}).get('confirmed_samples', {}):
                continue
            profiles = update_confirmed_sample(profiles, identity, sample_key, feature)
            profiles[identity]['cat'] = categories[identity]
            recovered += 1
    return profiles, recovered


def classify_faces(raw_faces, centroids, profiles):
    faces = []
    for raw in raw_faces:
        ranked = rank_known_identities(normalized_feature(raw['feature']), centroids, profiles)
        identity, confidence = 'Desconocido', 0
        if ranked:
            best, key = ranked[0]
            margin = best - ranked[1][0] if len(ranked) > 1 else 1
            # Legacy centroids need stronger evidence than a human-confirmed profile.
            human = profiles.get(key[1], {}).get('provenance') == 'human_confirmed'
            if best >= (.72 if human else .78) and margin >= (.12 if human else .15):
                identity, confidence = key[1], round(best * 100, 2)
        faces.append(dict(raw, identity=identity, confidence=confidence, is_manual=False))
    return faces


def destinations(faces, categories):
    albums = group_albums(faces, categories)
    if albums:
        return albums[0]
    known = [face for face in faces if face['identity'] in categories]
    if known:
        best = max(known, key=lambda face: face['confidence'])
        return categories[best['identity']], best['identity']
    return None


def apply_manual_labels(faces, overrides):
    from app.utils.faces import iou
    unmatched = False
    for override in overrides:
        if not (override.get('is_manual') is True or override.get('provenance') in {'human', 'human_confirmed'}):
            continue
        try:
            box = list(face_rectangle(override).values())
            ranked = sorted(((iou(box, face['box']), index) for index, face in enumerate(faces)), reverse=True)
            if not ranked or ranked[0][0] < .65 or (len(ranked) > 1 and ranked[1][0] > .5):
                unmatched = True
                continue
            faces[ranked[0][1]].update(identity=override['identity'], confidence=100,
                                     is_manual=True, provenance='human_confirmed')
        except (TypeError, ValueError, KeyError):
            unmatched = True
    return unmatched


def replace_with_retry(source, destination):
    for attempt in range(20):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.1)


def atomic_pickle(path, value):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, delete=False) as file:
            temp_path = Path(file.name)
            pickle.dump(value, file, protocol=pickle.HIGHEST_PROTOCOL)
        replace_with_retry(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    from app.globals import APP_DIR, RESULTADOS_DIR, CACHE_FILE, FACES_CACHE_FILE
    from app.utils.files import get_file_key, load_overrides
    from app.utils.file_ops import safe_move_file
    from app.services.content_analysis_service import content_sha256, model_version, load_analysis, save_analysis
    job = APP_DIR / 'scratch' / 'revisadas-ia'
    job.mkdir(parents=True, exist_ok=True)
    import msvcrt
    lock = (job / 'run.lock').open('a+b')
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    cv2.setNumThreads(1)
    source = RESULTADOS_DIR / 'Dudosos' / 'Revisado por IA'
    with (APP_DIR / 'centroids.pkl').open('rb') as file:
        centroids = {k: v for k, v in pickle.load(file).items() if isinstance(k, tuple)
                     and k[0] in {'Conocidos', 'Familia', 'YO', 'Profesores'} and not is_group_album(k[1])}
    categories = {key[1]: key[0] for key in centroids}
    with CACHE_FILE.open('rb') as file:
        profiles = pickle.load(file)
    original_profile = CACHE_FILE.stat().st_mtime_ns
    cache = {}
    for path in (APP_DIR / 'faces_cache.pkl', FACES_CACHE_FILE.with_suffix('.pkl.bak'), FACES_CACHE_FILE):
        if path.exists():
            with path.open('rb') as file:
                cache.update(pickle.load(file))
    overrides = load_overrides()
    profiles, recovered = recover_confirmed_samples(profiles, overrides, cache, categories)
    cache.clear()
    gc.collect()
    if args.apply and recovered:
        if CACHE_FILE.stat().st_mtime_ns != original_profile:
            raise RuntimeError('Los perfiles cambiaron durante la recuperación; reintentar sin sobrescribirlos')
        if not (job / 'profiles-before.pkl').exists():
            shutil.copy2(CACHE_FILE, job / 'profiles-before.pkl')
        atomic_pickle(CACHE_FILE, profiles)
    profile = 'reviewed-local-v1:' + model_version(APP_DIR)
    revision = profile + ':' + hashlib.sha256(pickle.dumps(profiles)).hexdigest()
    journal = job / ('moves.jsonl' if args.apply else 'preview.jsonl')
    completed, updates = {}, {}
    counts = Counter()
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get('revision') == revision and record.get('status') != 'error':
                completed[record['source']] = record
            if (record.get('status') in {'prepared', 'moved'} and record.get('destination')
                    and Path(record['destination']).is_file()
                    and content_sha256(record['destination']) == record.get('content_sha256')):
                updates[record['file_key']] = record['faces']
    paths = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'})
    detector = cv2.FaceDetectorYN.create(str(APP_DIR / 'models/face_detection_yunet.onnx'), '', (320, 320), .8, .3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(APP_DIR / 'models/face_recognition_sface.onnx'), '')

    def status(state, current=''):
        temp = job / 'status.tmp'
        temp.write_text(json.dumps(dict(status=state, total=len(paths), processed=sum(counts.values()),
                                       counts=dict(counts), recovered_samples=recovered, current=current),
                                   ensure_ascii=False), encoding='utf-8')
        replace_with_retry(temp, job / 'status.json')

    status('running')
    with journal.open('a', encoding='utf-8', buffering=1) as log:
        for index, path in enumerate(paths):
            if args.limit and index >= args.limit:
                break
            stat = path.stat()
            previous = completed.get(str(path))
            if previous and previous.get('mtime_ns') == stat.st_mtime_ns and previous.get('size') == stat.st_size:
                counts['already_reviewed'] += 1
                continue
            record = dict(source=str(path), revision=revision, size=stat.st_size, mtime_ns=stat.st_mtime_ns)
            try:
                digest = content_sha256(path)
                analysis = load_analysis(str(path), digest, profile)
                if analysis is None:
                    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
                    if image is None:
                        raise ValueError('Imagen no legible')
                    h, w = image.shape[:2]
                    scale = min(1., 1280 / max(w, h))
                    dw, dh = max(160, int(w * scale) // 32 * 32), max(160, int(h * scale) // 32 * 32)
                    detector.setInputSize((dw, dh))
                    _, detected = detector.detect(cv2.resize(image, (dw, dh)))
                    raw = []
                    if detected is not None:
                        detected[:, :14:2] *= w / dw
                        detected[:, 1:14:2] *= h / dh
                        for face in detected:
                            feature = recognizer.feature(recognizer.alignCrop(image, face)).flatten()
                            raw.append(dict(box=face[:4].tolist(), feature=feature.tolist()))
                    analysis = {'faces': raw}
                    save_analysis(digest, profile, analysis)
                faces = classify_faces(analysis['faces'], centroids, profiles)
                file_key = get_file_key(str(path))
                unmatched_manual = apply_manual_labels(faces, overrides.get(file_key, []))
                target = None if unmatched_manual else destinations(faces, categories)
                record.update(content_sha256=digest, file_key=get_file_key(str(path)), faces=faces,
                              status='review' if target is None else 'proposed')
                current = path.stat()
                if (stat.st_size, stat.st_mtime_ns) != (current.st_size, current.st_mtime_ns):
                    raise OSError('La imagen cambió durante el análisis')
                if args.apply and target:
                    destination = RESULTADOS_DIR / target[0] / target[1] / path.name
                    if not destination.resolve().is_relative_to(RESULTADOS_DIR.resolve()):
                        raise ValueError('El destino sale de la galería')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    suffix = 1
                    while destination.exists():
                        destination = destination.with_name(f'{path.stem}_{suffix}{path.suffix}')
                        suffix += 1
                    record.update(destination=str(destination), status='prepared')
                    log.write(json.dumps(record, ensure_ascii=False) + '\n')
                    if not safe_move_file(path, destination):
                        raise OSError('No se pudo mover la imagen')
                    if content_sha256(destination) != digest:
                        raise OSError('La verificación SHA-256 del destino falló')
                    load_analysis(str(destination), digest, profile)
                    record['status'] = 'moved'
                    updates[record['file_key']] = faces
                counts[record['status']] += 1
            except Exception as error:
                record.update(status='error', error=str(error))
                counts['error'] += 1
            log.write(json.dumps(record, ensure_ascii=False) + '\n')
            status('running', str(path))
    if args.apply and updates:
        with FACES_CACHE_FILE.open('rb') as file:
            cache = pickle.load(file)
        cache.update(updates)
        if not (job / 'faces-before.pkl').exists():
            shutil.copy2(FACES_CACHE_FILE, job / 'faces-before.pkl')
        atomic_pickle(FACES_CACHE_FILE, cache)
        from app.globals import clear_gallery_cache
        clear_gallery_cache()
    status('completed' if not args.limit else 'batch_completed')
    print(json.dumps(dict(counts), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
