from core.date_extractor import DateExtractor
from core.review_decider import ReviewDecider
from core.status import QueueStatus


def test_queue_status_enum():
    """Verifica que el enum de estados tenga todos los valores esperados."""
    assert QueueStatus.PENDING == "PENDING"
    assert QueueStatus.PROCESSING == "PROCESSING"
    assert QueueStatus.AUTO_CLASSIFIED == "AUTO_CLASSIFIED"
    assert QueueStatus.NEEDS_REVIEW == "NEEDS_REVIEW"
    assert QueueStatus.VERIFIED == "VERIFIED"
    assert QueueStatus.ERROR == "ERROR"
    assert QueueStatus.IGNORED == "IGNORED"


def test_date_extractor_patterns():
    """Verifica los patrones regex del extractor de fechas."""
    # Patrón 1: YYYYMMDD_HHMMSS
    res = DateExtractor._extract_from_string("IMG_20231005_123045.jpg")
    assert res == "2023-10-05T12:30:45"

    # Patrón 2: YYYY-MM-DD HH:MM:SS
    res = DateExtractor._extract_from_string("trip_2021-08-15 14_05_30_res.png")
    assert res == "2021-08-15T14:05:30"

    # Patrón 3: YYYY-MM-DD
    res = DateExtractor._extract_from_string("album_2020-05-20")
    assert res == "2020-05-20T00:00:00"

    # Patrón 4: YYYYMMDD
    res = DateExtractor._extract_from_string("backup_20191225.tar")
    assert res == "2019-12-25T00:00:00"

    # Fecha inválida (mes o día incorrecto)
    assert DateExtractor._extract_from_string("IMG_20231345_123045.jpg") is None


def test_date_extractor_cascade(tmp_path):
    """Verifica la cascada completa del extractor de fechas."""
    # 1. Fallback del sistema de archivos
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("dummy")

    best_date, source, confidence = DateExtractor.extract(test_file)
    assert source == "filesystem"
    assert confidence == "low"

    # 2. Nombre de archivo
    dated_file = tmp_path / "IMG_20220618_183000.jpg"
    dated_file.write_text("dummy")
    best_date, source, confidence = DateExtractor.extract(dated_file)
    assert best_date == "2022-06-18T18:30:00"
    assert source == "filename"
    assert confidence == "medium"

    # 3. Nombre de carpeta
    folder_path = tmp_path / "2021-04-12" / "no_date.jpg"
    folder_path.parent.mkdir()
    folder_path.write_text("dummy")
    best_date, source, confidence = DateExtractor.extract(folder_path)
    assert best_date == "2021-04-12T00:00:00"
    assert source == "folder"
    assert confidence == "low"


def test_review_decider():
    """Verifica la lógica del tomador de decisiones de revisión."""
    # Todo perfecto: caras de alta confianza, fecha media/alta, buena calidad
    status = ReviewDecider.decide(
        face_confidences=[0.92, 0.88], date_confidence="medium", quality_score=0.85
    )
    assert status == QueueStatus.AUTO_CLASSIFIED

    # Sin caras detectadas
    status = ReviewDecider.decide(face_confidences=[], date_confidence="high", quality_score=0.9)
    assert status == QueueStatus.AUTO_CLASSIFIED

    # Una cara con confianza media/baja
    status = ReviewDecider.decide(
        face_confidences=[0.95, 0.72], date_confidence="high", quality_score=0.8
    )
    assert status == QueueStatus.NEEDS_REVIEW

    # Confianza de fecha baja (ej. filesystem fallback)
    status = ReviewDecider.decide(face_confidences=[0.90], date_confidence="low", quality_score=0.8)
    assert status == QueueStatus.NEEDS_REVIEW

    # Calidad extremadamente baja
    status = ReviewDecider.decide(face_confidences=[], date_confidence="high", quality_score=0.15)
    assert status == QueueStatus.NEEDS_REVIEW


def test_db_schema_version(temp_db):
    """Verifica que el schema version se inicialice y trackee como propiedad."""
    assert temp_db.schema_version == 2
