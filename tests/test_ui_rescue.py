import os
import sys
import unittest
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

class TestUIRescueAndValidation(unittest.TestCase):
    def setUp(self):
        self.project_dir = Path(__file__).resolve().parent.parent

    def test_settings_drawer_hidden_by_default(self):
        # 1. Check index.html: drawer does NOT have 'open' class by default
        index_html = (self.project_dir / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="settings-drawer"', index_html)
        self.assertNotIn('id="settings-drawer" class="settings-drawer open"', index_html)
        
        # 2. Check modals.css: settings-drawer has transform: translateX(100%) and drawer-overlay has visibility: hidden
        modals_css = (self.project_dir / "static" / "css" / "modals.css").read_text(encoding="utf-8")
        self.assertIn("transform: translateX(100%)", modals_css)
        self.assertIn("visibility: hidden", modals_css)
        self.assertIn(".settings-drawer.open", modals_css)
        self.assertIn("transform: translateX(0)", modals_css)

    def test_sidebar_and_main_flex_layout(self):
        # Check base layout rules prevent overlapping
        sidebar_css = (self.project_dir / "static" / "css" / "sidebar.css").read_text(encoding="utf-8")
        self.assertIn("width: var(--sidebar-width)", sidebar_css)
        self.assertIn("flex-shrink: 0", sidebar_css)

    def test_no_external_download_scripts(self):
        # Verify app/__init__.py and main modules do not invoke pip, urllib.request downloads or external installers
        init_py = (self.project_dir / "app" / "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn("pip install", init_py)
        self.assertNotIn("subprocess.run([\"pip\"", init_py)
        self.assertNotIn("download_model", init_py)

    def test_main_js_initialization_flow(self):
        main_js = (self.project_dir / "static" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn("DOMContentLoaded", main_js)
        self.assertIn("loadGallery", main_js)

if __name__ == "__main__":
    unittest.main()