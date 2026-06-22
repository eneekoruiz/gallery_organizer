"""Apertura explícita de carpetas solicitada desde presentación."""

from __future__ import annotations

import os
from pathlib import Path


class NativeFolderOpener:
    def open(self, path: Path) -> None:
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        os.startfile(str(resolved))  # type: ignore[attr-defined]
