import ast
import pickle
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
from app.services.face_learning import (
    HUMAN, aligned_feature, face_rectangle, normalized_feature, rank_known_identities, update_confirmed_sample,
)


class LearningTests(unittest.TestCase):
    def test_reloading_partial_manual_profiles_preserves_other_reference_people(self):
        import app.globals as g
        first, second = np.eye(128, dtype=np.float32)[:2]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / 'profiles.pkl'
            with cache.open('wb') as file:
                pickle.dump({'Ana': {'centroid': second, 'provenance': HUMAN,
                                     'confirmed_samples': {'manual': second}}}, file)
            with (root / 'centroids.pkl').open('wb') as file:
                pickle.dump({('Familia', 'Ana'): first, ('Conocidos', 'Bea'): first,
                             ('Familia', 'Familia conmigo'): first,
                             ('📋 Revisión / Por Organizar', 'Persona Nueva #1'): first,
                             ('Conocidos', 'Invalid'): np.zeros(128)}, file)
            with patch.multiple(g, APP_DIR=root, CACHE_FILE=cache, known_faces={}):
                g.reload_known_faces()
                self.assertEqual(set(g.known_faces), {'Ana', 'Bea'})
                self.assertEqual(g.known_faces['Ana']['provenance'], HUMAN)
                np.testing.assert_array_equal(g.known_faces['Ana']['centroid'], second)
                self.assertNotEqual(g.known_faces['Bea'].get('provenance'), HUMAN)
                self.assertEqual(g.known_faces['Bea']['cat'], 'Conocidos')

    def test_icloud_ranks_people_using_only_confirmed_appearance_profiles(self):
        first, second, other = np.eye(128, dtype=np.float32)[:3]
        centroids = {
            ("Familia", "Ana"): first,
            ("Conocidos", "Ana"): first,
            "Ana": first,
            ("Conocidos", "Bea"): other,
            ("Revision", "Persona Nueva #1"): second,
        }
        profiles = {
            "Ana": {"provenance": HUMAN, "centroids": [first, second]},
            "Bea": {"provenance": "auto", "centroids": [second]},
        }
        ranked = rank_known_identities(second, centroids, profiles)
        self.assertEqual([(score, key[1]) for score, key in ranked], [(1.0, "Ana"), (0.0, "Bea")])

    def test_box_coordinates_are_preserved(self):
        self.assertEqual(list(face_rectangle({'box': [240, 180, 80, 90]}).values()),
                         [240, 180, 80, 90])

    def test_invalid_embeddings_are_rejected(self):
        for vector in (np.zeros(128), np.ones(127), np.full(128, np.nan)):
            with self.assertRaises(ValueError):
                normalized_feature(vector)

    def test_reconfirmation_is_idempotent_and_relabel_removes_old_sample(self):
        v = np.arange(128)
        first = update_confirmed_sample({}, 'A', 'photo:face', v)
        second = update_confirmed_sample(first, 'A', 'photo:face', v)
        np.testing.assert_array_equal(first['A']['centroid'], second['A']['centroid'])
        changed = update_confirmed_sample(second, 'B', 'photo:face', v)
        self.assertNotIn('A', changed)
        self.assertEqual(changed['B']['provenance'], HUMAN)

    def test_legacy_centroid_is_not_training_evidence(self):
        result = update_confirmed_sample({'A': {'centroid': np.ones(128)}},
                                         'A', 'confirmed', np.arange(128))
        np.testing.assert_allclose(result['A']['centroid'], normalized_feature(np.arange(128)))

    def test_alignment_used_and_ambiguity_rejected(self):
        detector, recognizer = Mock(), Mock()
        face = np.array([1, 2, 30, 40] + [0] * 11)
        detector.detect.return_value = (None, [face])
        recognizer.feature.return_value = np.ones(128)
        image = np.zeros((100, 100, 3))
        aligned_feature(image, {'box': [1, 2, 30, 40]}, detector, recognizer, lambda a, b: 1)
        recognizer.alignCrop.assert_called_once()
        detector.detect.return_value = (None, [face, face])
        with self.assertRaises(ValueError):
            aligned_feature(image, {'box': [1, 2, 30, 40]}, detector, recognizer, lambda a, b: 1)

    def test_automatic_correction_only_suggests_without_io(self):
        source = Path(__file__).resolve().parents[1] / 'app/services/face_service.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_correction_to_file')
        scope = {'HUMAN': HUMAN}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), scope)
        face = {'box': [240, 180, 80, 90]}
        self.assertEqual(scope['apply_correction_to_file']('untouched.jpg', 'People', 'A', face), 'untouched.jpg')
        self.assertTrue(face['review_required'])
        self.assertNotIn('is_manual', face)


if __name__ == '__main__':
    unittest.main()
