import json
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import numpy as np

from scripts.reconcile_reviewed_photos import recover_confirmed_samples, classify_faces, destinations, apply_manual_labels, atomic_pickle, main


class ReviewedPhotosTests(unittest.TestCase):
    def test_windows_reader_lock_is_retried_and_permanent_failure_preserves_data(self):
        import scripts.reconcile_reviewed_photos as audit
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.pkl'
            real_replace = audit.os.replace
            attempts = []

            def temporarily_locked(source, destination):
                attempts.append(1)
                if len(attempts) == 1:
                    raise PermissionError('Reader is still open')
                real_replace(source, destination)

            with patch.object(audit.os, 'replace', side_effect=temporarily_locked), patch.object(audit.time, 'sleep'):
                atomic_pickle(path, {'saved': True})
            self.assertEqual(len(attempts), 2)
            previous = path.read_bytes()
            with patch.object(audit.os, 'replace', side_effect=PermissionError('Permanent')), patch.object(audit.time, 'sleep'):
                with self.assertRaises(PermissionError):
                    atomic_pickle(path, {'saved': False})
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(list(Path(temp).iterdir()), [path])

    def setUp(self):
        self.vector = np.eye(128, dtype=np.float32)[0]
        self.other = np.eye(128, dtype=np.float32)[1]

    def test_recovery_requires_human_confirmation_and_unique_box_match(self):
        face = dict(x=20, y=30, width=40, height=50, identity='F. Ana', provenance='human_confirmed')
        feature = dict(box=[20, 30, 40, 50], feature=self.vector.tolist())
        profiles, count = recover_confirmed_samples({}, {'photo': [face]}, {'photo': [feature]}, {'F. Ana': 'Familia'})
        self.assertEqual(count, 1)
        self.assertEqual(profiles['F. Ana']['provenance'], 'human_confirmed')
        self.assertEqual(profiles['F. Ana']['cat'], 'Familia')
        _, again = recover_confirmed_samples(profiles, {'photo': [face]}, {'photo': [feature]}, {'F. Ana': 'Familia'})
        self.assertEqual(again, 0)
        _, ambiguous = recover_confirmed_samples({}, {'photo': [face]}, {'photo': [feature, feature]}, {'F. Ana': 'Familia'})
        self.assertEqual(ambiguous, 0)
        face['provenance'] = 'automatic'
        self.assertEqual(recover_confirmed_samples({}, {'photo': [face]}, {'photo': [feature]}, {'F. Ana': 'Familia'})[1], 0)

    def test_ambiguity_does_not_move_or_train(self):
        raw = [dict(box=[0, 0, 40, 40], feature=self.vector.tolist())]
        centroids = {('Familia', 'F. Ana'): self.vector, ('Conocidos', 'C. Ane'): self.vector}
        profiles = {}
        faces = classify_faces(raw, centroids, profiles)
        self.assertEqual(faces[0]['identity'], 'Desconocido')
        self.assertIsNone(destinations(faces, {'F. Ana': 'Familia', 'C. Ane': 'Conocidos'}))
        self.assertEqual(profiles, {})

    def test_human_correction_wins_and_missing_face_blocks_move(self):
        faces = [dict(box=[20, 30, 40, 50], identity='C. Wrong', confidence=99)]
        manual = dict(x=20, y=30, width=40, height=50, identity='F. Ana', is_manual=True)
        self.assertFalse(apply_manual_labels(faces, [manual]))
        self.assertEqual(faces[0]['identity'], 'F. Ana')
        self.assertTrue(faces[0]['is_manual'])
        manual['x'] = 2000
        self.assertTrue(apply_manual_labels(faces, [manual]))

    def test_apply_moves_verified_file_preserves_unknown_and_resumes(self):
        import app.globals as g
        from app.services import content_analysis_service as content
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            results = root / 'Resultados'
            source = results / 'Dudosos' / 'Revisado por IA'
            source.mkdir(parents=True)
            known, unknown = source / 'known.jpg', source / 'unknown.jpg'
            known.write_bytes(b'known original')
            unknown.write_bytes(b'unknown original')
            for name, value in [('centroids.pkl', {('Familia', 'F. Ana'): self.vector}),
                                ('profiles.pkl', {}), ('faces.pkl', {})]:
                with (root / name).open('wb') as file:
                    pickle.dump(value, file)

            def analysis(path, *args):
                vector = self.vector if Path(path).name == 'known.jpg' else self.other
                return {'faces': [dict(box=[10, 20, 40, 50], feature=vector.tolist())]}

            with patch.multiple(g, APP_DIR=root, RESULTADOS_DIR=results, CACHE_FILE=root / 'profiles.pkl',
                                FACES_CACHE_FILE=root / 'faces.pkl'), \
                 patch('app.utils.files.load_overrides', return_value={}), \
                 patch.object(g, 'clear_gallery_cache'), \
                 patch.object(content, 'model_version', return_value='test-model'), \
                 patch.object(content, 'load_analysis', side_effect=analysis), \
                 patch('scripts.reconcile_reviewed_photos.cv2.FaceDetectorYN.create', return_value=Mock()), \
                 patch('scripts.reconcile_reviewed_photos.cv2.FaceRecognizerSF.create', return_value=Mock()), \
                 patch('sys.argv', ['audit', '--apply']):
                main()
                destination = results / 'Familia' / 'F. Ana' / 'known.jpg'
                self.assertEqual(destination.read_bytes(), b'known original')
                self.assertFalse(known.exists())
                self.assertEqual(unknown.read_bytes(), b'unknown original')
                main()
            self.assertEqual(len(list((results / 'Familia' / 'F. Ana').iterdir())), 1)
            with (root / 'profiles.pkl').open('rb') as file:
                self.assertEqual(pickle.load(file), {})
            state = json.loads((root / 'scratch/revisadas-ia/status.json').read_text())
            self.assertEqual(state['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
