import os
os.environ["SMART_GALLERY_BACKGROUND_TASKS"] = "0"
import shutil
import json
import pickle
from threading import Event
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np

from app import create_app
from app.services import content_analysis_service as content, vector_index
from app.services import face_service, icloud_sync_service
from app.services.face_learning import HUMAN


class ContentAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.db = patch.object(vector_index, "DB_PATH", self.root / "index.db")
        self.db.start()

    def tearDown(self):
        self.db.stop()
        self.folder.cleanup()

    def test_renamed_copy_reuses_persistent_detections_and_preserves_locations(self):
        first, second = self.root / "local.jpg", self.root / "Drive" / "renamed.jpg"
        first.write_bytes(b"same original bytes")
        second.parent.mkdir()
        shutil.copy2(first, second)
        digest = content.content_sha256(first)
        self.assertIsNone(content.load_analysis(first, digest, "model-1"))
        payload = {"faces": [], "features": {}}
        content.save_analysis(digest, "model-1", payload)
        self.assertEqual(content.load_analysis(second, content.content_sha256(second), "model-1"), payload)
        self.assertEqual(content.find_content_duplicates(), {digest: [str(second), str(first)]})
        self.assertIsNone(content.load_analysis(second, digest, "model-2"))

    def test_complete_hash_distinguishes_tail_even_with_same_size_and_timestamp(self):
        first, second = self.root / "first.jpg", self.root / "second.jpg"
        prefix = b"x" * (1024 * 1024)
        first.write_bytes(prefix + b"A")
        second.write_bytes(prefix + b"B")
        os.utime(second, ns=(first.stat().st_atime_ns, first.stat().st_mtime_ns))
        self.assertNotEqual(content.content_sha256(first), content.content_sha256(second))

    def test_changed_path_updates_alias_without_erasing_other_copy(self):
        first, second = self.root / "one", self.root / "two"
        first.write_bytes(b"original")
        second.write_bytes(b"original")
        original = content.content_sha256(first)
        for path in (first, second):
            content.load_analysis(path, original, "v1")
        second.write_bytes(b"changed")
        content.load_analysis(second, content.content_sha256(second), "v1")
        self.assertEqual(content.find_content_duplicates(), {})

    def test_api_reuses_features_but_reapplies_current_human_corrections(self):
        model_dir = self.root / "models"
        model_dir.mkdir()
        for name in ("face_detection_yunet.onnx", "face_recognition_sface.onnx"):
            (model_dir / name).write_bytes(name.encode())
        first, second = self.root / "local" / "one.jpg", self.root / "Drive" / "copy.jpg"
        first.parent.mkdir()
        second.parent.mkdir()
        cv2.imwrite(str(first), np.zeros((128, 128, 3), dtype=np.uint8))
        shutil.copy2(first, second)
        detector = Mock()
        detector.detect.return_value = (1, np.array([
            [10, 10, 50, 50, 25, 25, 45, 25, 35, 35, 25, 45, 45, 45, .99]
        ], dtype=np.float32))
        recognizer = Mock()
        embedding = np.zeros((1, 128), dtype=np.float32)
        embedding[0, 0] = 1
        recognizer.feature.return_value = embedding
        profiles = {"Ana": {"centroid": embedding[0], "provenance": HUMAN}}
        overrides = {}
        with patch.multiple(face_service, APP_DIR=self.root, detector=detector,
                            recognizer=recognizer, known_faces=profiles, faces_cache={}), \
             patch.object(face_service, "load_overrides", return_value=overrides):
            client = create_app({"TESTING": True}).test_client()
            initial = client.post("/api/analyze", json={"path": str(first)})
            self.assertEqual(initial.status_code, 200, initial.json)
            repeated = client.post("/api/analyze", json={"path": str(second)})
            self.assertEqual(repeated.status_code, 200, repeated.json)
            self.assertFalse(initial.json["analysis_reused"])
            self.assertTrue(repeated.json["analysis_reused"])
            self.assertEqual(initial.json["content_sha256"], repeated.json["content_sha256"])
            self.assertEqual(detector.detect.call_count, 1)
            self.assertEqual(recognizer.feature.call_count, 1)
            face = repeated.json["faces"][0]
            overrides[face_service.get_file_key(str(second))] = [
                {**face, "identity": "Bea", "is_manual": True, "provenance": HUMAN}
            ]
            corrected = client.post("/api/analyze", json={"path": str(second)})
            self.assertEqual(corrected.json["faces"][0]["identity"], "Bea")
            self.assertEqual(detector.detect.call_count, 1)
            forced = client.post("/api/analyze", json={"path": str(second), "force": True})
            self.assertEqual(forced.status_code, 200, forced.json)
            self.assertFalse(forced.json["analysis_reused"])
            self.assertEqual(detector.detect.call_count, 2)

    def test_worker_reuses_copy_resumes_and_reaudits_after_file_changes(self):
        from app.services import apple_service, supervisor_service
        source = self.root / "source"
        source.mkdir()
        first, second = source / "one.jpg", source / "renamed.jpg"
        cv2.imwrite(str(first), np.zeros((128, 128, 3), dtype=np.uint8))
        shutil.copy2(first, second)
        model_dir = self.root / "models"
        model_dir.mkdir()
        for name in ("face_detection_yunet.onnx", "face_recognition_sface.onnx"):
            (model_dir / name).write_bytes(name.encode())
        vector = np.eye(128, dtype=np.float32)[0]
        (self.root / "centroids.pkl").write_bytes(pickle.dumps({("Familia", "Ana"): vector}))
        (self.root / "profiles.pkl").write_bytes(pickle.dumps({}))
        detector, recognizer = Mock(), Mock()
        raw = np.array([[10, 10, 50, 50, 25, 25, 45, 25, 35, 35, 25, 45, 45, 45, .99]], dtype=np.float32)
        detector.detect.side_effect = lambda _: (1, raw.copy())
        recognizer.feature.return_value = vector[None, :]
        db = {}
        sync = icloud_sync_service
        state = dict(sync._SYNC_STATE)
        state["reused_analysis"] = 0
        with patch.multiple(apple_service, APPLE_DB_FILE=self.root/"apple.json", _apple_db=db),              patch.multiple(sync, APP_DIR=self.root, CENTROIDS_FILE=self.root/"centroids.pkl",
                            CACHE_FILE=self.root/"profiles.pkl", ICLOUD_PHOTOS_DIR=source,
                            PROGRESS_FILE=self.root/"progress.json", _SYNC_STATE=state,
                            _STOP_REQUESTED=Event()),              patch.object(sync.cv2.FaceDetectorYN, "create", return_value=detector),              patch.object(sync.cv2.FaceRecognizerSF, "create", return_value=recognizer),              patch.object(sync, "_ensure_icloud_client_running"),              patch.object(sync, "_create_windows_url_shortcut"),              patch.object(sync, "generate_thumbnail", return_value=None),              patch.object(sync, "save_supervisor_state"),              patch.object(sync, "supervise_and_adapt_decision",
                          wraps=supervisor_service.supervise_and_adapt_decision) as audit:
            sync._run_icloud_worker()
            self.assertEqual(detector.detect.call_count, 1)
            self.assertEqual(recognizer.feature.call_count, 1)
            self.assertEqual(audit.call_count, 2)
            self.assertEqual(state["reused_analysis"], 1)
            self.assertEqual(state["status"], "completed")
            self.assertEqual(len(json.loads((self.root/"apple.json").read_text())), 2)
            self.assertEqual(apple_service._apple_db[str(first)]["content_sha256"], apple_service._apple_db[str(second)]["content_sha256"])
            sync._run_icloud_worker()
            self.assertEqual(audit.call_count, 2)
            cv2.imwrite(str(second), np.full((128, 128, 3), 200, dtype=np.uint8))
            os.utime(second, ns=(second.stat().st_atime_ns, second.stat().st_mtime_ns+1_000_000_000))
            sync._run_icloud_worker()
            self.assertEqual(detector.detect.call_count, 2)
            self.assertEqual(audit.call_count, 3)
            self.assertNotEqual(apple_service._apple_db[str(first)]["content_sha256"], apple_service._apple_db[str(second)]["content_sha256"])

    def test_duplicate_purge_checks_entire_content_before_deleting(self):
        from app.services import file_service
        album = self.root / "Resultados"
        album.mkdir()
        first, duplicate, distinct = [album / name for name in ("one.jpg", "copy.jpg", "different.jpg")]
        prefix = b"x" * (1024 * 1024)
        first.write_bytes(prefix + b"A")
        duplicate.write_bytes(prefix + b"A")
        distinct.write_bytes(prefix + b"B")
        prior = Path.cwd()
        try:
            os.chdir(self.root)
            with patch.object(file_service, "RESULTADOS_DIR", album),                  patch.object(file_service, "clear_gallery_cache"):
                app = create_app({"TESTING": True})
                with app.test_request_context():
                    result = file_service.api_purge_exact_duplicates()
                    self.assertEqual(result.json["purged_count"], 1)
            self.assertTrue(distinct.is_file())
            self.assertEqual(sum(p.is_file() for p in (first, duplicate)), 1)
        finally:
            os.chdir(prior)

    def test_worker_hash_is_for_the_decoded_bytes(self):
        path = self.root / "input.jpg"
        cv2.imwrite(str(path), np.zeros((64, 64, 3), dtype=np.uint8))
        image, digest, revision = icloud_sync_service._read_icloud_media(str(path))
        self.assertEqual(image.shape[:2], (64, 64))
        self.assertEqual(digest, content.content_sha256(path))
        self.assertEqual(revision, (path.stat().st_size, path.stat().st_mtime_ns))
