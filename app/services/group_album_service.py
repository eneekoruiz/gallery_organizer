"""Group membership comes from face evidence, never from the containing folder."""
import math
import re
import unicodedata


def is_group_album(name):
    name = ''.join(c for c in unicodedata.normalize('NFD', name.lower())
                   if unicodedata.category(c) != 'Mn')
    return name in {f'{kind} {suffix}' for kind in
                    ('familia', 'familiares', 'conocidos', 'amigos', 'mascotas')
                    for suffix in ('conmigo', 'sin mi')}


def trusted_identities(faces, categories):
    identities = set()
    unresolved = not bool(faces)
    for face in faces:
        if not isinstance(face, dict) or not isinstance(face.get('identity'), str):
            unresolved = True
            continue
        identity = face.get('identity', '')
        category = categories.get(identity)
        if identity == 'YO':
            category = 'YO'
        elif identity.startswith('F. '):
            category = 'Familia'
        elif identity.startswith('C. '):
            category = 'Conocidos'
        elif identity.startswith('M. ') or identity in {'Perro', 'Gato', 'Ney', 'Sua'}:
            category = 'Mascotas'
        manual = face.get('is_manual') is True or face.get('provenance') in {'human', 'human_confirmed'}
        try:
            confidence = float(face.get('confidence', 0))
        except (ValueError, TypeError):
            label = str(face.get('confidence', ''))
            match = re.search(r'\((\d+(?:\.\d+)?)%\)', label)
            confidence = float(match[1]) if match and not any(
                word in label.lower() for word in ('dudoso', 'sugerencia', 'pendiente')) else 0
        if (is_group_album(identity) or category not in
                {'YO', 'Familia', 'Familiares', 'Conocidos', 'Amigos', 'Mascotas'}
                or (not manual and (not math.isfinite(confidence) or confidence < 65))
                or face.get('is_dudoso') or 'dudoso' in str(face.get('status', '')).lower()):
            unresolved = True
            continue
        identities.add(identity)
    return identities, unresolved


def group_albums(faces, categories):
    identities, unresolved = trusted_identities(faces, categories)
    has_yo = 'YO' in identities
    family = {i for i in identities if i.startswith('F. ') or categories.get(i) in {'Familia', 'Familiares'}}
    friends = {i for i in identities if i.startswith('C. ') or categories.get(i) in {'Conocidos', 'Amigos'}}
    pets = {i for i in identities if i.startswith('M. ') or categories.get(i) == 'Mascotas'
            or i in {'Perro', 'Gato', 'Ney', 'Sua'}}
    albums = []
    suffix = 'conmigo' if has_yo else 'sin mí'
    # A missed/unknown face cannot establish that YO is absent.
    if has_yo or not unresolved:
        if len(family) >= 2:
            albums.append(('Familia', f'Familia {suffix}'))
        if len(friends) >= 2 and not family:
            albums.append(('Conocidos', f'Conocidos {suffix}'))
        if len(pets) >= (1 if has_yo else 2):
            albums.append(('Mascotas', f'Mascotas {suffix}'))
    return albums
