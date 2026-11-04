import json
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from app.services import apple_service, icloud_sync_service


class ICloudSyncTests(unittest.TestCase):
    def test_checkpoint_roundtrip_and_encoding_failure_preserve_previous_index(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'apple_db.json'
            entries = {'C:\\Fotos\\familia "sí".jpg': {'faces': [{'feature': [.1, .2], 'identity': 'Ána'}]}}
            with patch.multiple(apple_service, APPLE_DB_FILE=path, _apple_db=entries):
                apple_service.save_apple_db()
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), entries)
                previous = path.read_bytes()
                entries['invalid'] = {'feature': object()}
                with self.assertRaises(TypeError):
                    apple_service.save_apple_db()
                self.assertEqual(path.read_bytes(), previous)
                self.assertEqual(list(Path(folder).iterdir()), [path])
            with patch.multiple(apple_service, APPLE_DB_FILE=path, _apple_db={}):
                apple_service.save_apple_db()
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {})

    def test_checkpoint_preserves_previous_index_when_write_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "apple_db.json"
            path.write_text('{"old": {}}', encoding="utf-8")
            with patch.multiple(apple_service, APPLE_DB_FILE=path, _apple_db={"new": {}}):
                with patch.object(apple_service.os, "replace", side_effect=OSError("locked")):
                    with self.assertRaises(OSError):
                        apple_service.save_apple_db()
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"old": {}})
                self.assertEqual(list(Path(folder).iterdir()), [path])
                apple_service.save_apple_db()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": {}})

    def test_slow_read_does_not_block_ready_file_and_failed_read_is_isolated(self):
        release = Event()

        def read(path):
            if path == "slow":
                release.wait(5)
            if path == "broken":
                raise OSError("offline")
            return path

        with patch.object(icloud_sync_service, "_read_icloud_media", side_effect=read):
            media = icloud_sync_service._prefetch_icloud_media(
                ["slow", "ready", "broken"], Event(), workers=2
            )
            try:
                self.assertEqual(next(media), ("ready", "ready"))
            finally:
                release.set()
            self.assertEqual(dict(media), {"slow": "slow", "broken": None})
