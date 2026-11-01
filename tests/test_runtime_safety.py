import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from types import ModuleType

from flask import Blueprint
from app import create_app

ROOT = Path(__file__).resolve().parent.parent


class RuntimeSafetyTests(unittest.TestCase):
    def factory(self, config=None):
        modules = {}
        for name in ('views', 'api_gallery', 'api_faces', 'api_tools',
                     'api_sharing', 'api_events', 'api_config'):
            module = ModuleType('app.routes.' + name)
            setattr(module, name + '_bp', Blueprint(name, __name__))
            modules[module.__name__] = module
        with patch.dict(sys.modules, modules), patch('threading.Thread.start') as start:
            app = create_app(config)
        return app, start.call_count

    def test_classification_disabled_by_default(self):
        with patch.dict(os.environ, {'SMART_GALLERY_BACKGROUND_TASKS': '1'}):
            app, started = self.factory()
        self.assertFalse(app.config['AUTO_CLASSIFY'])
        self.assertEqual(started, 1)  # Thumbnail worker only.

    def test_testing_disables_workers_even_if_classification_requested(self):
        app, started = self.factory({'TESTING': True, 'AUTO_CLASSIFY': True})
        self.assertEqual(started, 0)

    def test_environment_disables_workers(self):
        with patch.dict(os.environ, {'SMART_GALLERY_BACKGROUND_TASKS': '0'}):
            app, started = self.factory({'AUTO_CLASSIFY': True})
        self.assertEqual(started, 0)

    def test_globals_import_does_not_start_workers_or_load_models_in_tests(self):
        code = """
from unittest.mock import patch
with patch('threading.Thread.start') as start, patch('cv2.FaceDetectorYN.create') as detector:
    import app.globals as g
    assert not g.BACKGROUND_TASKS_ENABLED
    assert g.wait_for_boot(timeout=0)
    start.assert_not_called()
    detector.assert_not_called()
"""
        env = dict(os.environ, SMART_GALLERY_BACKGROUND_TASKS='0')
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
