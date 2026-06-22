import logging
import re
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

log = logging.getLogger(__name__)


class DateExtractor:
    @staticmethod
    def extract(
        filepath: Path | str,
    ) -> tuple[
        str | None,
        str | None,
        str | None,
        str,
        str,
        str,
        str,
    ]:
        """Extrae la fecha y hora de un archivo multimedia usando múltiples fuentes en cascada.

        Retorna:
            (exif_datetime, filename_datetime, folder_datetime, filesystem_datetime,
             best_datetime, date_source, date_confidence)
            - exif_datetime: ISO 8601 string or None
            - filename_datetime: ISO 8601 string or None
            - folder_datetime: ISO 8601 string or None
            - filesystem_datetime: ISO 8601 string
            - best_datetime: ISO 8601 string
            - date_source: 'exif' | 'filename' | 'folder' | 'filesystem'
            - date_confidence: 'exact' | 'month' | 'year' | 'low' | 'unknown'
        """
        filepath = Path(filepath)

        # 1. Intentar EXIF
        exif_datetime = DateExtractor._extract_exif(filepath)

        # 2. Intentar nombre de archivo
        filename_datetime = DateExtractor._extract_from_string(filepath.name)

        # 3. Intentar nombres de carpetas contenedoras con heurísticas avanzadas
        folder_datetime, folder_conf = DateExtractor._extract_from_folder_structure(filepath)

        # 4. Fallback del sistema de archivos (siempre disponible)
        filesystem_datetime = DateExtractor._extract_filesystem(filepath)

        # Determinar el mejor candidato
        if exif_datetime:
            best_datetime = exif_datetime
            date_source = "exif"
            date_confidence = "exact"
        elif filename_datetime:
            best_datetime = filename_datetime
            date_source = "filename"
            date_confidence = "exact"
        elif folder_datetime:
            best_datetime = folder_datetime
            date_source = "folder"
            date_confidence = folder_conf
        else:
            best_datetime = filesystem_datetime
            date_source = "filesystem"
            date_confidence = "low"

        return (
            exif_datetime,
            filename_datetime,
            folder_datetime,
            filesystem_datetime,
            best_datetime,
            date_source,
            date_confidence,
        )

    @staticmethod
    def _extract_from_folder_structure(filepath: Path) -> tuple[str | None, str]:
        """Analiza la estructura de directorios para extraer fechas inteligentes."""
        for parent in filepath.parents:
            if parent.name == "" or parent.name == filepath.anchor:
                break
            name = parent.name.strip()

            # 1. Comprobar fecha exacta YYYY-MM-DD o YYYY_MM_DD
            match_exact = re.search(
                r"\b(19\d\d|20\d\d)[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])\b",
                name,
            )
            if match_exact:
                y, m, d = match_exact.groups()
                if DateExtractor._is_valid_date(int(y), int(m), int(d)):
                    return f"{y}-{m}-{d}T00:00:00", "exact"

            # 2. Comprobar temporadas tipo "verano 2018" o "summer 2018"
            seasons = {
                "verano": "07",
                "summer": "07",
                "primavera": "04",
                "spring": "04",
                "otono": "10",
                "otoño": "10",
                "autumn": "10",
                "fall": "10",
                "invierno": "01",
                "winter": "01",
            }
            for season_name, month_val in seasons.items():
                pat1 = rf"\b{season_name}\s+(19\d\d|20\d\d)\b"
                pat2 = rf"\b(19\d\d|20\d\d)\s+{season_name}\b"
                m1 = re.search(pat1, name, re.IGNORECASE)
                m2 = re.search(pat2, name, re.IGNORECASE)
                matched_year = None
                if m1:
                    matched_year = m1.group(1)
                elif m2:
                    matched_year = m2.group(1)

                if matched_year:
                    y = int(matched_year)
                    if DateExtractor._is_valid_date(y, int(month_val), 1):
                        return f"{matched_year}-{month_val}-01T00:00:00", "month"

            # 3. Comprobar año-mes YYYY-MM o YYYY_MM
            match_ym = re.search(r"\b(19\d\d|20\d\d)[-_](0[1-9]|1[0-2])\b", name)
            if match_ym:
                y, m = match_ym.groups()
                if DateExtractor._is_valid_date(int(y), int(m), 1):
                    return f"{y}-{m}-01T00:00:00", "month"

            # 4. Comprobar estructura de subcarpetas tipo YYYY/MM (ej: parent = '07', grandparent = '2016')
            if re.match(r"^(0[1-9]|1[0-2])$", name):
                grandparent_name = parent.parent.name.strip()
                if re.match(r"^(19\d\d|20\d\d)$", grandparent_name):
                    y = int(grandparent_name)
                    m = int(name)
                    if DateExtractor._is_valid_date(y, m, 1):
                        return f"{grandparent_name}-{name}-01T00:00:00", "month"

            # 5. Comprobar solo año YYYY
            match_y = re.search(r"\b(19\d\d|20\d\d)\b", name)
            if match_y:
                y = int(match_y.group(1))
                if DateExtractor._is_valid_date(y, 1, 1):
                    return f"{y}-01-01T00:00:00", "year"

        return None, "unknown"

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
