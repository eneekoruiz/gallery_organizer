import os
import sys
import tempfile
import unittest
import hashlib
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.file_ops import safe_move_file

class TestStressSimulation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_batch_processing_1000_simulated_files(self):
        # Generate 1,000 simulated files with unique hashes
        inbox = self.root / "inbox"
        outbox = self.root / "organized"
        inbox.mkdir()
        outbox.mkdir()

        total_files = 1000
        hashes = {}
        for i in range(total_files):
            data = f"SIMULATED_PHOTO_DATA_INDEX_{i}_{time.time_ns()}".encode('utf-8')
            f_path = inbox / f"img_{i:04d}.jpg"
            f_path.write_bytes(data)
            hashes[f"img_{i:04d}.jpg"] = hashlib.sha256(data).hexdigest()

        # Batch organize all 1,000 files
        start_time = time.time()
        for i in range(total_files):
            src = inbox / f"img_{i:04d}.jpg"
            # Organize into 10 buckets (100 files each)
            bucket = outbox / f"Bucket_{i % 10:02d}"
            bucket.mkdir(exist_ok=True)
            dst = bucket / src.name
            safe_move_file(str(src), str(dst))

        duration = time.time() - start_time
        
        # Verify 100% integrity of all 1,000 files
        verified_count = 0
        for bucket in outbox.iterdir():
            for f in bucket.glob("*.jpg"):
                content = f.read_bytes()
                f_hash = hashlib.sha256(content).hexdigest()
                self.assertEqual(f_hash, hashes[f.name])
                verified_count += 1

        self.assertEqual(verified_count, total_files)
        self.assertLess(duration, 15.0)  # Processing 1,000 files should take under 15 seconds

if __name__ == "__main__":
    unittest.main()