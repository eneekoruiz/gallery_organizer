import os
os.environ['SMART_GALLERY_BACKGROUND_TASKS'] = '0'
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import cv2
from app import create_app
from app.services import face_service as service


class LearningApiTests(unittest.TestCase):
    def test_confirmation_and_reconfirmation_use_one_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'sample.jpg'
            cv2.imwrite(str(image), np.zeros((100, 100, 3), dtype=np.uint8))
            identities = {}
            overrides = {}
            with patch.multiple(service, APP_DIR=root, FOTOS_DIR=root, RESULTADOS_DIR=root,
                                CACHE_FILE=root/'centroids.pkl', FACES_CACHE_FILE=root/'faces.pkl',
                                known_faces=identities, faces_cache={}, detector=object(), recognizer=object()), \
                 patch.object(service, 'find_relocated_file', return_value=str(image)), \
                 patch.object(service, 'load_overrides', return_value=overrides), \
                 patch.object(service, 'reload_known_faces'), \
                 patch.object(service, 'save_overrides'), \
                 patch.object(service, 'clear_gallery_cache'), \
                 patch.object(service, 'aligned_feature', return_value=np.ones(128)/np.sqrt(128)), \
                 patch('threading.Thread.start'):
                client = create_app({'TESTING': True}).test_client()
                payload = {'path': str(image), 'new_categoria': 'Test', 'new_identidad': 'Sample',
                           'face': {'box': [10, 10, 30, 30]}}
                for _ in range(2):
                    response = client.post('/api/correct', json=payload)
                    self.assertEqual(response.status_code, 200, response.json)
                self.assertEqual(len(identities['Sample']['confirmed_samples']), 1)
                self.assertTrue(image.exists())
                self.assertTrue((root/'centroids.pkl').exists())


if __name__ == '__main__':
    unittest.main()
