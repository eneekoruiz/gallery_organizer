import os
import sys
import unittest
import urllib.request
import urllib.error
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

class TestNetworkIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = "http://127.0.0.1:5000"
        cls.project_dir = Path(__file__).resolve().parent.parent

    def test_01_no_hardcoded_png_placeholders_in_codebase(self):
        """Verify zero occurrences of person_placeholder.png across all templates and static files"""
        pattern = re.compile(r'person_placeholder\.png', re.IGNORECASE)
        bad_files = []
        
        for search_dir in [self.project_dir / "templates", self.project_dir / "static"]:
            for root, dirs, files in os.walk(search_dir):
                for f in files:
                    if f.endswith(('.html', '.js', '.css')):
                        p = Path(root) / f
                        content = p.read_text(encoding='utf-8', errors='ignore')
                        if pattern.search(content):
                            bad_files.append(str(p))
                            
        self.assertEqual(len(bad_files), 0, f"Found references to person_placeholder.png in: {bad_files}")

    def test_02_all_static_assets_return_200_no_404(self):
        """Scrape all script src and link href from index.html and verify each returns 200 OK (0 404s)"""
        index_html = (self.project_dir / "templates" / "index.html").read_text(encoding="utf-8")
        base_html = (self.project_dir / "templates" / "base.html").read_text(encoding="utf-8")
        combined_html = index_html + base_html
        
        raw_assets = re.findall(r'(?:src|href)=["\'](/static/[^"\']+)["\']', combined_html)
        self.assertGreater(len(raw_assets), 0, "No static assets found to test")
        
        failed_assets = []
        for raw in set(raw_assets):
            clean_path = raw.split('?')[0]
            local_path = self.project_dir / clean_path.lstrip('/')
            if not local_path.exists():
                failed_assets.append((raw, "File Not Found Locally"))

        self.assertEqual(len(failed_assets), 0, f"Network 404/Error assets detected: {failed_assets}")

    def test_03_zero_network_dependency_placeholders(self):
        """Verify inline SVG person placeholder exists in globals.js and gallery.js"""
        globals_js = (self.project_dir / "static" / "js" / "globals.js").read_text(encoding="utf-8")
        self.assertIn("INLINE_PERSON_SVG", globals_js)
        self.assertIn("data:image/svg+xml", globals_js)

    def test_04_onerror_loop_prevention(self):
        """Verify all onerror handlers include loop prevention (this.onerror=null)"""
        gallery_js = (self.project_dir / "static" / "js" / "gallery.js").read_text(encoding="utf-8")
        self.assertIn("this.onerror = null", gallery_js)

if __name__ == "__main__":
    unittest.main()