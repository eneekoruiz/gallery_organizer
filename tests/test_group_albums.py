import unittest
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from app.services.group_album_service import group_albums, is_group_album


def face(identity, **kwargs):
    return dict(identity=identity, confidence=90, **kwargs)


class GroupAlbumTests(unittest.TestCase):
    def test_audit_uses_human_samples_and_rejects_ties(self):
        import numpy as np
        from scripts.audit_group_albums import second_opinion
        vector = np.zeros(128)
        vector[0] = 1
        detected = dict(identity='F. Wrong', confidence=99, feature=vector.tolist())
        result = second_opinion([detected], np.stack([vector]), ['F. Ana'])
        self.assertEqual(result[0]['identity'], 'F. Ana')
        self.assertEqual(result[0]['confidence'], 100)
        self.assertEqual(detected['identity'], 'F. Wrong')
        ambiguous = second_opinion([detected], np.stack([vector, vector]), ['F. Ana', 'YO'])
        self.assertEqual(ambiguous[0]['confidence'], 0)
        self.assertEqual(second_opinion([detected], None, [])[0]['confidence'], 0)
        manual = dict(identity='YO', is_manual=True)
        self.assertEqual(second_opinion([manual], None, []), [manual])

    def test_gallery_uses_faces_for_local_and_icloud_groups(self):
        from flask import Flask
        from app.services import gallery_service as gs
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            folder = root / 'Fotos' / 'Familia' / 'Familia conmigo'
            folder.mkdir(parents=True)
            pair = folder / 'pair.jpg'
            group = folder / 'group.jpg'
            unknown = folder / 'unknown.jpg'
            for path in (pair, group, unknown):
                path.write_bytes(b'fixture')
            family = [face('YO'), face('F. Ana'), face('F. Jon')]
            cached = {str(pair): family[:2], str(group): family}
            for name, value in dict(FOTOS_DIR=root / 'Fotos', RESULTADOS_DIR=root / 'Resultados',
                                    CONFIG_FILE=root / 'config.json', faces_cache=cached).items():
                stack.enter_context(patch.object(gs, name, value))
            stack.enter_context(patch.object(gs, 'get_gallery_cache', return_value=None))
            stack.enter_context(patch.object(gs, 'set_gallery_cache'))
            stack.enter_context(patch.object(gs, 'process_pending_deletions'))
            stack.enter_context(patch.object(gs, 'load_overrides', return_value={}))
            stack.enter_context(patch.object(gs, 'get_file_key', side_effect=str))
            stack.enter_context(patch.object(gs, 'get_all_identities', return_value=[]))
            cloud = {'cloud.jpg': dict(cloud_source='icloud', category='Familia', identity='F. Ana', faces=family)}
            stack.enter_context(patch('app.services.apple_service.load_apple_db', return_value=cloud))
            with Flask(__name__).test_request_context('/api/gallery?force=true'):
                gallery = gs.get_gallery().get_json()
            groups = {item['path'] for item in gallery['Familia']['Familia conmigo']}
            self.assertEqual(groups, {str(group), 'cloud.jpg'})
            personal = {item['path'] for item in gallery['Familia']['F. Ana']}
            self.assertIn(str(pair), personal)
            pending = gallery['📋 Revisión / Por Organizar']['⚠️ Grupos por confirmar']
            self.assertEqual([item['path'] for item in pending], [str(unknown)])

    def test_pairs_stay_in_person_album(self):
        for other in ('F. Ana', 'C. Ane'):
            self.assertEqual(group_albums([face('YO'), face(other)], {}), [])

    def test_distinct_people_and_yo(self):
        self.assertEqual(group_albums([face('YO'), face('C. Ane'), face('C. Jon')], {}),
                         [('Conocidos', 'Conocidos conmigo')])
        self.assertEqual(group_albums([face('YO'), face('F. Ana'), face('F. Jon')], {}),
                         [('Familia', 'Familia conmigo')])
        self.assertEqual(group_albums([face('YO'), face('C. Ane'), face('C. Ane')], {}), [])

    def test_without_yo_requires_no_unresolved_faces(self):
        family = [face('F. Ana'), face('F. Jon')]
        self.assertEqual(group_albums(family, {}), [('Familia', 'Familia sin mí')])
        for unknown in (face('Desconocido'), dict(identity='YO', confidence=55)):
            self.assertEqual(group_albums([*family, unknown], {}), [])
        for invalid in (None, {}, {'identity': None}, dict(identity='YO', confidence=float('nan'))):
            self.assertEqual(group_albums([*family, invalid], {}), [])

    def test_manual_and_legacy_evidence(self):
        friends = [dict(identity='C. Ane', confidence='🤖 IA (80.0%)'),
                   dict(identity='C. Jon', confidence='✏️ Corrección Manual', is_manual=True)]
        self.assertEqual(group_albums(friends, {}), [('Conocidos', 'Conocidos sin mí')])
        friends[0]['confidence'] = '⚠️ Dudoso (80.0%)'
        self.assertEqual(group_albums(friends, {}), [])
        self.assertEqual(group_albums([face('Familia conmigo'), face('YO')], {}), [])

    def test_aliases_mixed_family_and_pets(self):
        self.assertTrue(is_group_album('Amigos sin mí'))
        self.assertTrue(is_group_album('Familiares conmigo'))
        self.assertFalse(is_group_album('F. Ana'))
        self.assertEqual(group_albums([face('YO'), face('Ane'), face('Jon')],
                                     {'Ane': 'Amigos', 'Jon': 'Amigos'}),
                         [('Conocidos', 'Conocidos conmigo')])
        self.assertEqual(group_albums([face('C. Ane'), face('C. Jon'), face('F. Ana')], {}), [])
        self.assertEqual(group_albums([face('YO'), face('Ney')], {}),
                         [('Mascotas', 'Mascotas conmigo')])


if __name__ == '__main__':
    unittest.main()
