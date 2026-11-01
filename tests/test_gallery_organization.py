import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.file_ops import safe_move_file

class TestGalleryOrganization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        self.gallery_root = self.root / "Galeria"
        self.gallery_root.mkdir()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_batch_organize_into_person_folders(self):
        # Create unorganized files
        unorganized = self.root / "Unorganized"
        unorganized.mkdir()
        
        files = []
        for i in range(10):
            f = unorganized / f"person_sample_{i}.jpg"
            f.write_bytes(f"PERSON_PHOTO_DATA_{i}".encode('utf-8'))
            files.append(f)

        # Target person folder
        target_person_dir = self.gallery_root / "Conocidos" / "C. Juan Garcia"
        target_person_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            dst = target_person_dir / f.name
            success = safe_move_file(str(f), str(dst))
            self.assertTrue(success)
            self.assertTrue(dst.exists())

        # Verify all files arrived intact
        moved_count = len(list(target_person_dir.glob("*.jpg")))
        self.assertEqual(moved_count, 10)

    def test_no_overwrite_on_collision(self):
        target_dir = self.gallery_root / "YO" / "YO"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        existing = target_dir / "photo.jpg"
        existing.write_bytes(b"ORIGINAL_PHOTO_CONTENT")

        # Attempt to move new photo with collision
        incoming = self.root / "incoming_photo.jpg"
        incoming.write_bytes(b"NEW_PHOTO_CONTENT")

        # Resolve destination path with collision avoidance
        dst = target_dir / "photo.jpg"
        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            dst = target_dir / f"{stem}_1{suffix}"

        safe_move_file(str(incoming), str(dst))
        
        # Verify BOTH files exist and original was NOT overwritten
        self.assertTrue((target_dir / "photo.jpg").exists())
        self.assertEqual((target_dir / "photo.jpg").read_bytes(), b"ORIGINAL_PHOTO_CONTENT")
        self.assertTrue((target_dir / "photo_1.jpg").exists())
        self.assertEqual((target_dir / "photo_1.jpg").read_bytes(), b"NEW_PHOTO_CONTENT")

    def test_rename_group_virtual_category_resolution(self):
        import app.globals as g
        import app.services.face_service as fs
        from app import create_app
        import json

        old_res = g.RESULTADOS_DIR
        old_fotos = g.FOTOS_DIR
        old_fs_res = fs.RESULTADOS_DIR
        old_fs_fotos = fs.FOTOS_DIR
        try:
            temp_res = self.gallery_root / "Resultados"
            temp_fotos = self.gallery_root / "Fotos"
            temp_res.mkdir(parents=True, exist_ok=True)
            temp_fotos.mkdir(parents=True, exist_ok=True)

            g.RESULTADOS_DIR = temp_res
            g.FOTOS_DIR = temp_fotos
            fs.RESULTADOS_DIR = temp_res
            fs.FOTOS_DIR = temp_fotos

            source_dir = temp_res / "Personas Sin Nombre" / "Persona Nueva #99"
            source_dir.mkdir(parents=True, exist_ok=True)
            sample_img = source_dir / "test_face.jpg"
            sample_img.write_bytes(b"FACE_IMG_DATA")

            flask_app = create_app()
            client = flask_app.test_client()

            # Call rename_group with virtual UI category '📋 Revisión / Por Organizar'
            res = client.post('/api/rename_group',
                              data=json.dumps({
                                  "cat": "📋 Revisión / Por Organizar",
                                  "ident": "Persona Nueva #99",
                                  "new_name": "YO",
                                  "new_cat": "YO"
                              }),
                              content_type='application/json')

            self.assertEqual(res.status_code, 200, f"Error: {res.get_json()}")
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("count"), 1)

            target_file = temp_res / "YO" / "YO" / "test_face.jpg"
            self.assertTrue(target_file.exists())
            self.assertEqual(target_file.read_bytes(), b"FACE_IMG_DATA")
            self.assertFalse(source_dir.exists())
        finally:
            g.RESULTADOS_DIR = old_res
            g.FOTOS_DIR = old_fotos
            fs.RESULTADOS_DIR = old_fs_res
            fs.FOTOS_DIR = old_fs_fotos

    def test_person_dudosos_included_in_person_album(self):
        import json
        import app.globals as g
        import app.services.gallery_service as gs
        from app.globals import clear_gallery_cache
        from app.services.gallery_service import get_gallery
        from app import create_app

        temp_root = self.root / "gallery_dudosos_root"
        temp_fotos = temp_root / "Fotos"
        temp_res = temp_root / "Resultados"
        temp_fotos.mkdir(parents=True, exist_ok=True)
        temp_res.mkdir(parents=True, exist_ok=True)

        old_res = g.RESULTADOS_DIR
        old_fotos = g.FOTOS_DIR
        old_gs_res = gs.RESULTADOS_DIR
        old_gs_fotos = gs.FOTOS_DIR
        old_gs_cfg = gs.CONFIG_FILE

        temp_cfg = temp_root / "config.json"
        temp_cfg.write_text(json.dumps({"mode": "local", "local_path": str(temp_root)}), encoding="utf-8")

        try:
            g.RESULTADOS_DIR = temp_res
            g.FOTOS_DIR = temp_fotos
            gs.RESULTADOS_DIR = temp_res
            gs.FOTOS_DIR = temp_fotos
            gs.CONFIG_FILE = temp_cfg

            # 1. Foto normal en el album de la persona
            person_dir = temp_res / "Conocidos" / "C. Test Person"
            person_dir.mkdir(parents=True, exist_ok=True)
            (person_dir / "normal.jpg").write_bytes(b"NORMAL_PHOTO")

            # 2. Foto dudosa en la subcarpeta _Dudosos de esa misma persona
            dudoso_dir = person_dir / "_Dudosos"
            dudoso_dir.mkdir(parents=True, exist_ok=True)
            (dudoso_dir / "doubtful.jpg").write_bytes(b"DOUBTFUL_PHOTO")

            clear_gallery_cache()
            flask_app = create_app()
            with flask_app.test_request_context('/api/gallery?force=true'):
                res = get_gallery()
                gal = res.get_json()

            # La persona debe existir en Conocidos
            self.assertIn("Conocidos", gal)
            self.assertIn("C. Test Person", gal["Conocidos"])
            items = gal["Conocidos"]["C. Test Person"]
            self.assertEqual(len(items), 2, f"Expected 2 items in C. Test Person album, got: {items}")

            names = {it["name"]: it for it in items}
            self.assertIn("normal.jpg", names)
            self.assertIn("doubtful.jpg", names)

            # La foto dudosa debe tener is_dudoso = True y status = "Dudoso"
            dudoso_item = names["doubtful.jpg"]
            self.assertTrue(dudoso_item.get("is_dudoso"))
            self.assertEqual(dudoso_item.get("status"), "Dudoso")
            self.assertIn("⚠️ Por Confirmar", dudoso_item.get("source", ""))

            # Y la normal no debe ser dudosa
            normal_item = names["normal.jpg"]
            self.assertFalse(normal_item.get("is_dudoso"))
        finally:
            g.RESULTADOS_DIR = old_res
            g.FOTOS_DIR = old_fotos
            gs.RESULTADOS_DIR = old_gs_res
            gs.FOTOS_DIR = old_gs_fotos
            gs.CONFIG_FILE = old_gs_cfg
            clear_gallery_cache()

    def test_is_genuine_manual_override_validation(self):
        from app.services.gallery_service import is_genuine_manual_override

        # Automated prediction from familia script must be rejected
        self.assertFalse(is_genuine_manual_override([
            {'x': 100, 'y': 100, 'width': 200, 'height': 200, 'identity': 'C. Alba', 'is_manual': False, 'from_familia_conmigo_analysis': True}
        ]))

        # is_manual: False must be rejected even with good coordinates
        self.assertFalse(is_genuine_manual_override([
            {'x': 50, 'y': 50, 'width': 120, 'height': 150, 'identity': 'C. Test', 'is_manual': False}
        ]))

        # Dummy full-screen bounding box must be rejected
        self.assertFalse(is_genuine_manual_override([
            {'x': 100.0, 'y': 100.0, 'width': 100.0, 'height': 100.0, 'identity': 'C. Paula'}
        ]))

        # Genuine human confirmed override must be accepted
        self.assertTrue(is_genuine_manual_override([
            {'x': 120, 'y': 80, 'width': 150, 'height': 200, 'identity': 'C. Naia Varas', 'provenance': 'human_confirmed'}
        ]))

    def test_rename_group_idempotent_on_double_click(self):
        import app.globals as g
        import app.services.face_service as fs
        from app import create_app
        import json

        old_res = g.RESULTADOS_DIR
        old_fotos = g.FOTOS_DIR
        old_fs_res = fs.RESULTADOS_DIR
        old_fs_fotos = fs.FOTOS_DIR
        try:
            temp_res = self.gallery_root / "Resultados"
            temp_fotos = self.gallery_root / "Fotos"
            temp_res.mkdir(parents=True, exist_ok=True)
            temp_fotos.mkdir(parents=True, exist_ok=True)

            g.RESULTADOS_DIR = temp_res
            g.FOTOS_DIR = temp_fotos
            fs.RESULTADOS_DIR = temp_res
            fs.FOTOS_DIR = temp_fotos

            # Target directory already exists (as if moved in 1st request of a double click)
            target_dir = temp_res / "YO" / "YO"
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "already_moved.jpg").write_bytes(b"DATA")

            flask_app = create_app()
            client = flask_app.test_client()

            # Second call for the same merge
            res = client.post('/api/rename_group',
                              data=json.dumps({
                                  "cat": "📋 Revisión / Por Organizar",
                                  "ident": "Persona Nueva #88",
                                  "new_name": "YO",
                                  "new_cat": "YO"
                              }),
                              content_type='application/json')

            # Must return 200 with already_merged: True, NEVER 404!
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("already_merged"))
        finally:
            g.RESULTADOS_DIR = old_res
            g.FOTOS_DIR = old_fotos
            fs.RESULTADOS_DIR = old_fs_res
            fs.FOTOS_DIR = old_fs_fotos

if __name__ == "__main__":
    unittest.main()

