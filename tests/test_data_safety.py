import os
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.file_ops import safe_move_file, safe_remove_file

class TestDataSafety(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        self.src_dir = self.root / "source"
        self.dst_dir = self.root / "destination"
        self.src_dir.mkdir()
        self.dst_dir.mkdir()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_safe_move_file_integrity(self):
        test_content = b"CRITICAL_USER_PHOTO_DATA_123456789" * 1000
        src_file = self.src_dir / "photo1.jpg"
        src_file.write_bytes(test_content)
        original_hash = hashlib.sha256(test_content).hexdigest()

        dst_file = self.dst_dir / "photo1.jpg"
        result = safe_move_file(str(src_file), str(dst_file))
        
        self.assertTrue(result)
        self.assertFalse(src_file.exists())
        self.assertTrue(dst_file.exists())
        
        dst_hash = hashlib.sha256(dst_file.read_bytes()).hexdigest()
        self.assertEqual(original_hash, dst_hash)

    def test_safe_move_large_file(self):
        large_content = os.urandom(2 * 1024 * 1024)
        src_file = self.src_dir / "video1.mov"
        src_file.write_bytes(large_content)
        orig_hash = hashlib.sha256(large_content).hexdigest()

        dst_file = self.dst_dir / "video1.mov"
        safe_move_file(str(src_file), str(dst_file))

        self.assertTrue(dst_file.exists())
        self.assertEqual(dst_file.stat().st_size, 2 * 1024 * 1024)
        self.assertEqual(hashlib.sha256(dst_file.read_bytes()).hexdigest(), orig_hash)

    def test_safe_remove_file(self):
        test_file = self.src_dir / "delete_me.tmp"
        test_file.write_text("temporary data")
        
        self.assertTrue(test_file.exists())
        success = safe_remove_file(str(test_file))
        self.assertTrue(success)
        self.assertFalse(test_file.exists())

    def test_safe_remove_nonexistent_file(self):
        non_existent = self.src_dir / "does_not_exist.jpg"
        success = safe_remove_file(str(non_existent))
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main()