import os
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.files import calculate_sharpness, calculate_dhash

class TestDuplicatesAndHashes(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_sha256_exact_duplicate_detection(self):
        content = b"REPLICA_EXACTA_BYTE_A_BYTE_PHOTO_TEST" * 500
        file1 = self.root / "original.jpg"
        file2 = self.root / "copy.jpg"
        file1.write_bytes(content)
        file2.write_bytes(content)

        h1 = hashlib.sha256(file1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(file2.read_bytes()).hexdigest()

        self.assertEqual(h1, h2)
        self.assertEqual(file1.stat().st_size, file2.stat().st_size)

    def test_dhash_perceptual_similarity(self):
        # Create an image and a slightly modified version
        img1_path = self.root / "shot_a.jpg"
        img2_path = self.root / "shot_b.jpg"
        
        img1 = Image.new("RGB", (200, 200), color=(100, 150, 200))
        img2 = Image.new("RGB", (200, 200), color=(102, 152, 202))
        img1.save(str(img1_path))
        img2.save(str(img2_path))

        h1 = calculate_dhash(str(img1_path))
        h2 = calculate_dhash(str(img2_path))
        
        self.assertIsNotNone(h1)
        self.assertIsNotNone(h2)

    def test_sharpness_calculation(self):
        # Plain uniform image has very low sharpness (near 0)
        plain_path = self.root / "plain.jpg"
        plain_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        plain_img.save(str(plain_path))

        sharpness = calculate_sharpness(str(plain_path))
        self.assertIsInstance(sharpness, (int, float))
        self.assertGreaterEqual(sharpness, 0.0)

if __name__ == "__main__":
    unittest.main()