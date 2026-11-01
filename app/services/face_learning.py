"""Learning contracts: predictions and legacy labels are never human evidence."""
import numpy as np

HUMAN = 'human_confirmed'

def normalized_feature(value):
    vector = np.asarray(value, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if vector.size != 128 or not np.isfinite(vector).all() or not np.isfinite(norm) or norm <= 0:
        raise ValueError('Invalid SFace embedding')
    return vector / norm

def face_rectangle(face):
    values = face.get('box') if 'box' in face else [face.get(k) for k in ('x', 'y', 'width', 'height')]
    box = np.asarray(values, dtype=float).reshape(-1)
    if len(box) != 4 or not np.isfinite(box).all() or box[0] < 0 or box[1] < 0 or min(box[2:]) <= 0:
        raise ValueError('Invalid face rectangle')
    return dict(zip(('x', 'y', 'width', 'height'), box.tolist()))

def aligned_feature(image, rectangle, detector, recognizer, overlap):
    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)
    if faces is None:
        raise ValueError('Face could not be redetected')
    box = list(face_rectangle(rectangle).values())
    ranked = sorted(((overlap(box, f[:4]), f) for f in faces), key=lambda pair: pair[0], reverse=True)
    if not ranked or ranked[0][0] < 0.5 or (len(ranked) > 1 and ranked[1][0] > 0.4):
        raise ValueError('Face match is missing or ambiguous')
    return normalized_feature(recognizer.feature(recognizer.alignCrop(image, ranked[0][1])))

def confirmed_centroid(previous, feature):
    feature = normalized_feature(feature)
    if previous and previous.get('provenance') == HUMAN:
        return normalized_feature(normalized_feature(previous['centroid']) * .85 + feature * .15)
    return feature


def compute_appearance_centroids(samples, sim_threshold=0.70, max_centroids=4):
    """Clusters face samples of an identity into distinct appearance centroids (childhood vs adult, glasses, angles)."""
    if not samples:
        return []
    vectors = [normalized_feature(s) for s in samples]
    if len(vectors) <= 1:
        return [vectors[0]]

    clusters = []
    for v in vectors:
        matched = False
        for cl in clusters:
            sim = float(np.dot(v, cl['center']))
            if sim >= sim_threshold:
                cl['members'].append(v)
                cl['center'] = normalized_feature(np.mean(cl['members'], axis=0))
                matched = True
                break
        if not matched:
            clusters.append({'center': v, 'members': [v]})

    clusters.sort(key=lambda c: len(c['members']), reverse=True)
    return [cl['center'] for cl in clusters[:max_centroids]]


def update_confirmed_sample(identities, identity, sample_key, feature):
    """Reconfirming replaces a sample; relabeling removes its previous contribution."""
    import copy
    result = copy.deepcopy(identities)
    feature = normalized_feature(feature)
    for name, record in list(result.items()):
        samples = record.get('confirmed_samples', {})
        if sample_key in samples:
            del samples[sample_key]
            if samples:
                sample_list = list(samples.values())
                record['centroid'] = normalized_feature(np.mean(sample_list, axis=0))
                record['centroids'] = compute_appearance_centroids(sample_list)
            else:
                del result[name]
    record = result.get(identity, {})
    samples = dict(record.get('confirmed_samples', {}))
    samples[sample_key] = feature
    sample_list = list(samples.values())
    result[identity] = {
        'centroid': normalized_feature(np.mean(sample_list, axis=0)),
        'centroids': compute_appearance_centroids(sample_list),
        'confirmed_samples': samples,
        'provenance': HUMAN,
        'names': list(samples)
    }
    return result
