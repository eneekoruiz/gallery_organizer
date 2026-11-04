"""Read-only second opinion on identity albums. Run with py -m scripts.audit_identity_assignments."""
import csv
import json
import pickle
from collections import Counter
from pathlib import Path

import numpy as np

from app.services.face_learning import HUMAN, normalized_feature

IDENTITY_CATEGORIES = {"Conocidos", "Familia", "Profesores", "YO"}
MEDIA = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".avi", ".mkv"}


def vector(value):
    try:
        return normalized_feature(value)
    except (TypeError, ValueError):
        return None


def review(identity, faces, references):
    if any((f.get("is_manual") or f.get("provenance") == HUMAN)
           and f.get("identity") == identity for f in faces):
        return "confirmada_manualmente", "", "", ""
    if identity not in references:
        return "sin_referencia", "", "", ""
    features = [v for f in faces if (v := vector(f.get("feature"))) is not None]
    if not features:
        return "sin_evidencia_facial", "", "", ""

    # The album owner can be any face in a group photo.
    embeddings = np.stack(features)
    owner = float((embeddings @ references[identity].T).max())
    alternatives = ((float((embeddings @ samples.T).max()), name)
                    for name, samples in references.items() if name != identity)
    other, candidate = max(alternatives, default=(-1.0, ""))
    if owner < 0.40 and other >= 0.55 and other - owner >= 0.15:
        status = "posible_album_erroneo"
    elif owner < 0.55:
        status = "evidencia_debil"
    else:
        status = "compatible"
    return status, candidate, round(owner, 3), round(other, 3)


def main():
    from app.globals import APP_DIR, CACHE_FILE, FACES_CACHE_FILE, FOTOS_DIR, RESULTADOS_DIR

    from app.utils.files import get_file_key, load_overrides

    overrides = load_overrides()
    with (APP_DIR / "centroids.pkl").open("rb") as file:
        centroids = pickle.load(file)
    references = {}
    for key, value in centroids.items():
        if isinstance(key, tuple) and len(key) == 2 and key[0] in IDENTITY_CATEGORIES:
            if (embedding := vector(value)) is not None:
                references.setdefault(key[1], []).append(embedding)
    if CACHE_FILE.is_file():
        with CACHE_FILE.open("rb") as file:
            for identity, record in pickle.load(file).items():
                if not isinstance(record, dict) or record.get("provenance") != HUMAN:
                    continue
                human = [v for sample in record.get("confirmed_samples", {}).values()
                         if (v := vector(sample)) is not None]
                if human:
                    references[identity] = human
    references = {name: np.stack(samples) for name, samples in references.items()}
    if not references:
        raise RuntimeError("No hay referencias faciales utilizables")

    print(f"{len(references)} identidades de referencia", flush=True)
    cache = {}
    for path in (APP_DIR / "faces_cache.pkl", FACES_CACHE_FILE.with_suffix(".pkl.bak"), FACES_CACHE_FILE):
        if path.is_file():
            try:
                with path.open("rb") as file:
                    cache.update(pickle.load(file))
            except (EOFError, pickle.UnpicklingError) as error:
                print(f"Caché no legible ({path.name}): {error}", flush=True)

    print(f"{len(cache)} entradas de caché cargadas", flush=True)
    items = {}
    with (APP_DIR / "apple_db.json").open(encoding="utf-8") as file:
        for path, info in json.load(file).items():
            if info.get("category") in IDENTITY_CATEGORIES and info.get("identity"):
                items[Path(path)] = (info["identity"], info.get("faces") or [], "icloud")
    for root in (FOTOS_DIR, RESULTADOS_DIR):
        for category in sorted(IDENTITY_CATEGORIES):
            album = root / category
            for path in album.rglob("*"):
                if path.suffix.lower() not in MEDIA or not path.is_file():
                    continue
                relative = path.relative_to(album)
                if len(relative.parts) > 1 or category == "YO":
                    identity = relative.parts[0] if len(relative.parts) > 1 else category
                    key = get_file_key(path)
                    faces = cache.get(str(path)) or cache.get(key) or []
                    items[path] = (identity, [*faces, *overrides.get(key, [])], root.name)

    print(f"{len(items)} archivos en álbumes de identidad", flush=True)
    counts = Counter()
    report = APP_DIR / "scratch" / "audit_identity_assignments.csv"
    report.parent.mkdir(exist_ok=True)
    with report.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(("origen", "ruta", "album", "resultado", "candidato", "sim_album", "sim_candidato"))
        for path, (identity, faces, source) in items.items():
            result = review(identity, [face for face in faces if isinstance(face, dict)], references)
            counts[result[0]] += 1
            writer.writerow((source, str(path), identity, *result))
    print(f"{len(items)} archivos: {dict(counts)}", flush=True)
    print(report, flush=True)


if __name__ == "__main__":
    main()
