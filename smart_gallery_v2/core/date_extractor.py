import logging
import re
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

log = logging.getLogger(__name__)


class DateExtractor:
    @staticmethod
    def extract(filepath: Path | str) -> tuple[str, str, str]:
        """Extrae la fecha y hora de un archivo multimedia usando múltiples fuentes en cascada.

        Retorna:
            (best_datetime, date_source, date_confidence)
            - best_datetime: ISO 8601 string (ej. '2023-10-05T12:30:45')
            - date_source: 'EXIF' | 'filename' | 'folder' | 'filesystem'
            - date_confidence: 'high' | 'medium' | 'low'
        """
        filepath = Path(filepath)

        # 1. Intentar EXIF
        exif_date = DateExtractor._extract_exif(filepath)
        if exif_date:
            return exif_date, "EXIF", "high"

        # 2. Intentar nombre de archivo
        filename_date = DateExtractor._extract_from_string(filepath.name)
        if filename_date:
            return filename_date, "filename", "medium"

        # 3. Intentar nombres de carpetas contenedoras
        for parent in filepath.parents:
            if parent.name == "" or parent.name == filepath.anchor:
                break
            folder_date = DateExtractor._extract_from_string(parent.name)
            if folder_date:
                return folder_date, "folder", "low"

        # 4. Fallback: fecha de modificación del sistema de archivos
        fs_date = DateExtractor._extract_filesystem(filepath)
        return fs_date, "filesystem", "low"

    @staticmethod
    def _extract_exif(filepath: Path) -> str | None:
        """Intenta extraer DateTimeOriginal de los metadatos EXIF."""
        if filepath.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            return None
        try:
            with Image.open(filepath) as img:
                exif = img.getexif()
                if not exif:
                    return None
                for tag, value in exif.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                        if isinstance(value, str):
                            parsed = DateExtractor._parse_exif_format(value)
                            if parsed:
                                return parsed
        except Exception as e:
            log.debug(f"Failed to read EXIF for {filepath}: {e}")
        return None

    @staticmethod
    def _parse_exif_format(exif_str: str) -> str | None:
        exif_str = exif_str.strip()
        # Formato estándar de EXIF: 'YYYY:MM:DD HH:MM:SS'
        match = re.search(
            r"^(\d{4})[:-_](\d{2})[:-_](\d{2})\s+(\d{2})[:-_:](\d{2})[:-_:](\d{2})$",
            exif_str,
        )
        if match:
            y, m, d, hh, mm, ss = match.groups()
            if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                return f"{y}-{m}-{d}T{hh}:{mm}:{ss}"
        return None

    @staticmethod
    def _extract_from_string(s: str) -> str | None:
        """Busca patrones de fecha y hora dentro de una cadena de texto."""
        # Patrón 1: YYYYMMDD_HHMMSS
        match1 = re.search(
            r"(19\d\d|20\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[-_](0\d|1\d|2[0-3])(0\d|[1-5]\d)(0\d|[1-5]\d)",
            s,
        )
        if match1:
            y, m, d, hh, mm, ss = match1.groups()
            if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                return f"{y}-{m}-{d}T{hh}:{mm}:{ss}"

        # Patrón 2: YYYY-MM-DD HH:MM:SS o YYYY_MM_DD_HH_MM_SS
        match2 = re.search(
            r"(19\d\d|20\d\d)[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])[-_\s](0\d|1\d|2[0-3])[-_:]?(0\d|[1-5]\d)[-_:]?(0\d|[1-5]\d)",
            s,
        )
        if match2:
            y, m, d, hh, mm, ss = match2.groups()
            if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                return f"{y}-{m}-{d}T{hh}:{mm}:{ss}"

        # Patrón 3: YYYY-MM-DD o YYYY_MM_DD
        match3 = re.search(
            r"(19\d\d|20\d\d)[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])",
            s,
        )
        if match3:
            y, m, d = match3.groups()
            if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                return f"{y}-{m}-{d}T00:00:00"

        # Patrón 4: YYYYMMDD (8 dígitos compactos)
        match4 = re.search(
            r"(19\d\d|20\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])",
            s,
        )
        if match4:
            y, m, d = match4.groups()
            if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                return f"{y}-{m}-{d}T00:00:00"

        return None

    @staticmethod
    def _is_valid_date(y: int, m: int, d: int) -> bool:
        if not (1900 <= y <= datetime.now().year + 5):
            return False
        try:
            datetime(y, m, d)
            return True
        except ValueError:
            return False

    @staticmethod
    def _extract_filesystem(filepath: Path) -> str:
        try:
            mtime = filepath.stat().st_mtime
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            from datetime import timezone

            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
