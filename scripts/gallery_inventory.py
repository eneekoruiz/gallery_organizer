"""Inventory a gallery tree without following links or losing enumeration errors."""
import os
from pathlib import Path


def inventory(root):
    root = Path(root)
    result = {}

    def visit(folder):
        with os.scandir(folder) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(info, 'st_reparse_tag', 0) == 0xA0000003:
                    raise OSError(f'Enlace o unión requiere revisión: {entry.path}')
                directory = entry.is_dir(follow_symlinks=False)
                result[str(Path(entry.path).relative_to(root))] = None if directory else info.st_size
                if directory:
                    visit(entry.path)

    visit(root)
    return result
