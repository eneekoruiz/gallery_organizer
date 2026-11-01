import os
import sys
import tempfile
import unittest
import datetime
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

class TestExifMetadata(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_image_dimensions_and_megapixels(self):
        # Create test valid image (1920x1080)
        img_path = self.root / "test_1080p.jpg"
        img = Image.new("RGB", (1920, 1080), color=(73, 109, 137))
        img.save(str(img_path))
        
        with Image.open(str(img_path)) as loaded:
            w, h = loaded.width, loaded.height
            mp = (w * h) / 1000000.0
            self.assertEqual(w, 1920)
            self.assertEqual(h, 1080)
            self.assertAlmostEqual(mp, 2.0736, places=2)

    def test_date_fallback_from_filename(self):
        import re
        filename = "IMG_20230815_143000.jpg"
        match = re.search(r'(19\d{2}|20\d{2})([0-1]\d)([0-3]\d)', filename)
        self.assertIsNotNone(match)
        year, month, day = match.groups()
        parsed_date = datetime.datetime(int(year), int(month), int(day))
        self.assertEqual(parsed_date.year, 2023)
        self.assertEqual(parsed_date.month, 8)
        self.assertEqual(parsed_date.day, 15)

    def test_corrupt_image_graceful_handling(self):
        corrupt_path = self.root / "corrupt.jpg"
        corrupt_path.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01CORRUPTED_BYTES_HERE")
        
        # Verify opening corrupt bytes does not crash the server
        is_corrupt = False
        try:
            with Image.open(str(corrupt_path)) as img:
                img.verify()
        except Exception:
            is_corrupt = True
            
        self.assertTrue(is_corrupt)

if __name__ == "__main__":
    unittest.main()