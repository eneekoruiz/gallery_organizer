"""Audit saved group-folder decisions without downloading or moving originals."""
import csv
import json
import os
import pickle
from collections import Counter
from pathlib import Path

os.environ['SMART_GALLERY_BACKGROUND_TASKS'] = '0'

from app.services.group_album_service import group_albums, is_group_album, trusted_identities


def second_opinion(faces, matrix, names):
    from app.services.face_learning import HUMAN, normalized_feature
    result = []
    for original in faces:
        face = dict(original)
        if not (face.get('is_manual') or face.get('provenance') in {'human', HUMAN}):
            try:
                feature = normalized_feature(face.get('feature'))
            except (ValueError, TypeError):
                face['confidence'] = 0
            else:
                scores = {}
                if matrix is not None:
                    for name, score in zip(names, matrix @ feature):
                        scores[name] = max(scores.get(name, -1), float(score))
                ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
                if ranked and ranked[0][1] >= .65 and (len(ranked) == 1 or ranked[0][1] - ranked[1][1] >= .08):
                    face.update(identity=ranked[0][0], confidence=ranked[0][1] * 100)
                else:
                    face['confidence'] = 0
        result.append(face)
    return result


def main():
    from app.globals import APP_DIR, FOTOS_DIR, RESULTADOS_DIR, FACES_CACHE_FILE, CACHE_FILE
    from app.utils.files import get_file_key, load_overrides
    from app.services.face_learning import HUMAN, normalized_feature
    import numpy as np

    cache = {}
    for path in (APP_DIR / 'faces_cache.pkl', FACES_CACHE_FILE.with_suffix('.pkl.bak'), FACES_CACHE_FILE):
        if path.is_file():
            with path.open('rb') as file:
                cache.update(pickle.load(file))
    overrides = load_overrides()
    apple = json.loads((APP_DIR / 'apple_db.json').read_text(encoding='utf-8'))
    categories = {}
    with (APP_DIR / 'centroids.pkl').open('rb') as file:
        for key in pickle.load(file):
            if isinstance(key, tuple) and len(key) == 2 and not is_group_album(key[1]):
                categories[key[1]] = key[0]
    references = []
    names = []
    with CACHE_FILE.open('rb') as file:
        for name, record in pickle.load(file).items():
            if not isinstance(record, dict) or record.get('provenance') != HUMAN or is_group_album(name):
                continue
            for sample in record.get('confirmed_samples', {}).values():
                try:
                    references.append(normalized_feature(sample))
                    names.append(name)
                except (ValueError, TypeError):
                    continue
    matrix = np.stack(references) if references else None

    items = []
    for root in (FOTOS_DIR, RESULTADOS_DIR):
        for category in root.iterdir():
            if not category.is_dir():
                continue
            for folder in category.iterdir():
                if not folder.is_dir() or not is_group_album(folder.name):
                    continue
                for path in folder.rglob('*'):
                    if not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.heic', '.webp', '.mov', '.mp4', '.avi', '.url'}:
                        continue
                    key = get_file_key(str(path))
                    faces = overrides.get(key) or cache.get(key) or cache.get(str(path), [])
                    items.append((str(path), folder.name, faces))
    for path, info in apple.items():
        if not info.get('deleted_locally'):
            items.append((path, info.get('identity', ''), info.get('faces') or []))

    output = APP_DIR / 'scratch' / 'auditoria-grupos.csv'
    counts = Counter()
    with output.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(('ruta', 'carpeta_actual', 'grupos_por_etiquetas', 'grupos_por_referencias_humanas', 'personas_verificables', 'resultado'))
        for path, folder, faces in items:
            proposed = group_albums(faces, categories)
            verified_faces = second_opinion(faces, matrix, names)
            verified = group_albums(verified_faces, categories)
            if not is_group_album(folder) and not proposed and not verified:
                continue
            identities, unresolved = trusted_identities(verified_faces, categories)
            result = ('necesita_confirmacion' if unresolved else
                      'grupo_compatible' if verified else 'carpeta_individual')
            counts[result] += 1
            writer.writerow((path, folder, ' | '.join(i for c, i in proposed),
                             ' | '.join(i for c, i in verified), ' | '.join(sorted(identities)), result))
    print(json.dumps(dict(counts), ensure_ascii=False), flush=True)
    print(output, flush=True)


if __name__ == '__main__':
    main()
