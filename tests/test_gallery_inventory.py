from contextlib import nullcontext
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.gallery_inventory import inventory


class GalleryInventoryTests(unittest.TestCase):
    def test_nested_files_empty_folders_and_unicode_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'Familia' / 'Álbum'
            folder.mkdir(parents=True)
            (root / 'Vacía').mkdir()
            (folder / 'foto.jpg').write_bytes(b'photo')
            self.assertEqual(inventory(root), {'Familia': None, str(Path('Familia/Álbum')): None,
                                             str(Path('Familia/Álbum/foto.jpg')): 5, 'Vacía': None})

    def test_junctions_are_rejected_without_traversing_them(self):
        entry = SimpleNamespace(path=str(Path('root/junction')),
                                stat=lambda **_: SimpleNamespace(st_reparse_tag=0xA0000003),
                                is_symlink=lambda: False)
        with patch('scripts.gallery_inventory.os.scandir', return_value=nullcontext([entry])) as scan:
            with self.assertRaises(OSError):
                inventory(Path('root'))
        self.assertEqual(scan.call_count, 1)

    def test_enumeration_failures_are_not_silently_ignored(self):
        with patch('scripts.gallery_inventory.os.scandir', side_effect=PermissionError('unreadable')):
            with self.assertRaises(PermissionError):
                inventory(Path('root'))


if __name__ == '__main__':
    unittest.main()
