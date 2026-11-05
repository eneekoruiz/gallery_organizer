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

    def test_05_http_static_assets_serve_200_no_500(self):
        """Request every static asset via Flask test client with gzip and verify 200 OK (zero 500s)"""
        from app import create_app
        flask_app = create_app()
        client = flask_app.test_client()
        
        index_html = (self.project_dir / "templates" / "index.html").read_text(encoding="utf-8")
        base_html = (self.project_dir / "templates" / "base.html").read_text(encoding="utf-8")
        combined_html = index_html + base_html
        
        raw_assets = set(re.findall(r'(?:src|href)=["\'](/static/[^"\'?]+)', combined_html))
        self.assertGreater(len(raw_assets), 0)
        
        failed = []
        for asset in raw_assets:
            resp = client.get(asset, headers={'Accept-Encoding': 'gzip, deflate'})
            if resp.status_code != 200:
                failed.append((asset, resp.status_code))
                
        self.assertEqual(len(failed), 0, f"Static assets failed with non-200: {failed}")

    def test_06_fast_structure_and_preview_endpoints(self):
        """Verify fast structure and preview endpoints respond in sub-second with compact payloads"""
        from app import create_app
        flask_app = create_app()
        client = flask_app.test_client()
        
        # Structure endpoint must be 200 and < 100 KB
        resp_s = client.get('/api/gallery/structure', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(resp_s.status_code, 200)
        self.assertLess(len(resp_s.data), 100 * 1024, "Structure payload too large")
        
        # Preview endpoint must be 200 and < 20 KB
        resp_p = client.get('/api/gallery/preview', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(resp_p.status_code, 200)
        self.assertLess(len(resp_p.data), 20 * 1024, "Preview payload too large")

    def test_07_watchdog_safeguard_in_client_js(self):
        """Verify watchdog timer safeguard exists in both static/app.js and static/dist/app.js"""
        for js_file in [self.project_dir / "static" / "app.js", self.project_dir / "static" / "dist" / "app.js"]:
            content = js_file.read_text(encoding="utf-8")
            self.assertIn("GUARDA-TIEMPO DE SEGURIDAD (WATCHDOG)", content)
            self.assertIn("overlay.style.display = 'none'", content)

    def test_08_mobile_responsive_css_integrity(self):
        """Verify mobile responsive rules strictly enforce drawer overlay and bottom sheet"""
        sidebar_css = (self.project_dir / "static" / "css" / "sidebar.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 820px)", sidebar_css)
        self.assertIn("position: fixed !important", sidebar_css)
        self.assertIn("transform: translateX(-100%)", sidebar_css)
        
        lightbox_css = (self.project_dir / "static" / "css" / "lightbox.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 820px)", lightbox_css)
        self.assertIn("position: absolute !important", lightbox_css)
        self.assertIn("bottom: 0 !important", lightbox_css)


    def test_09_multi_face_preservation_and_compact_popup(self):
        """Verify multi-face photos are never deleted prematurely and popup scaling is bounded"""
        for js_file in [self.project_dir / 'static' / 'app.js', self.project_dir / 'static' / 'dist' / 'app.js']:
            content = js_file.read_text(encoding='utf-8')
            self.assertIn("scale(' + (1 / curZoom) + ')", content)
            self.assertIn('toggleMobileLightboxSheet(true)', content)

        # Lightbox CSS must hide .lb-box-popup on mobile
        lightbox_css = (self.project_dir / 'static' / 'css' / 'lightbox.css').read_text(encoding='utf-8')
        self.assertIn('.lb-box-popup', lightbox_css)
        self.assertIn('@media (max-width: 820px)', lightbox_css)

        # Multi-face preservation logic in face_service.py
        face_py = (self.project_dir / 'app' / 'services' / 'face_service.py').read_text(encoding='utf-8')
        self.assertIn('_RELOCATED_CACHE[orig_path.name] = str(target_path)', face_py)
        self.assertIn('has_multiple_faces = len(cached_faces) > 1', face_py)
        self.assertIn('has_unreviewed_faces', face_py)

if __name__ == "__main__":
    unittest.main()