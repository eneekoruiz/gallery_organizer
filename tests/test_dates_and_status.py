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
    """Verifica los patrones regex del extractor de fechas en nombres de archivo."""
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

    # Fecha inválida
    assert DateExtractor._extract_from_string("IMG_20231345_123045.jpg") is None


def test_date_extractor_cascade(tmp_path):
    """Verifica la cascada completa del extractor de fechas."""
    # 1. Fallback del sistema de archivos
    test_file = tmp_path / "test_file.jpg"
    test_file.write_text("dummy")

    exif, filename, folder, fs, best, source, confidence = DateExtractor.extract(test_file)
    assert exif is None
    assert filename is None
    assert folder is None
    assert source == "filesystem"
    assert confidence == "low"

    # 2. Nombre de archivo
    dated_file = tmp_path / "IMG_20220618_183000.jpg"
    dated_file.write_text("dummy")
    exif, filename, folder, fs, best, source, confidence = DateExtractor.extract(dated_file)
    assert best == "2022-06-18T18:30:00"
    assert source == "filename"
    assert confidence == "exact"


def test_date_extractor_folder_heuristics(tmp_path):
    """Verifica las heurísticas inteligentes para extraer fechas de directorios."""
    # A) Carpeta con año tipo "2014"
    file_y = tmp_path / "2014" / "photo.jpg"
    file_y.parent.mkdir()
    file_y.write_text("dummy")
    exif, filename, folder, fs, best, source, confidence = DateExtractor.extract(file_y)
    assert best == "2014-01-01T00:00:00"
    assert source == "folder"
    assert confidence == "year"

    # B) Estructura anidada "2016/07"
    file_ym_nested = tmp_path / "2016" / "07" / "photo.jpg"
    file_ym_nested.parent.mkdir(parents=True)
    file_ym_nested.write_text("dummy")
    exif, filename, folder, fs, best, source, confidence = DateExtractor.extract(file_ym_nested)
    assert best == "2016-07-01T00:00:00"
    assert source == "folder"
    assert confidence == "month"

    # C) Carpeta tipo temporada "verano 2018"
    file_season = tmp_path / "verano 2018" / "photo.jpg"
    file_season.parent.mkdir(parents=True, exist_ok=True)
    file_season.write_text("dummy")
    exif, filename, folder, fs, best, source, confidence = DateExtractor.extract(file_season)
    assert best == "2018-07-01T00:00:00"
    assert source == "folder"
    assert confidence == "month"


def test_review_decider():
    """Verifica la lógica del tomador de decisiones de revisión."""
    # Caso 1: Todo perfecto (sin caras, fecha perfecta, buena calidad)
    review, reasons, score = ReviewDecider.decide(
        face_confidences=[], date_confidence="exact", quality_score=0.9
    )
    assert review is False
    assert len(reasons) == 0
    assert score == 1.0

    # Caso 2: Cara de baja confianza
    review, reasons, score = ReviewDecider.decide(
        face_confidences=[0.95, 0.72], date_confidence="exact", quality_score=0.8
    )
    assert review is True
    assert "low_face_confidence" in reasons
    assert score < 1.0

    # Caso 3: Fecha incierta (filesystem fallback)
    review, reasons, score = ReviewDecider.decide(
        face_confidences=[], date_confidence="low", quality_score=0.8
    )
    assert review is True
    assert "date_uncertain" in reasons

    # Caso 4: Calidad extremadamente baja
    review, reasons, score = ReviewDecider.decide(
        face_confidences=[], date_confidence="exact", quality_score=0.15
    )
    assert review is True
    assert "low_quality" in reasons

    # Caso 5: Banderas avanzadas (Persona desconocida + conflicto de fecha de carpeta)
    review, reasons, score = ReviewDecider.decide(
        face_confidences=[0.92],
        date_confidence="exact",
        quality_score=0.8,
        has_unknown_person=True,
        has_folder_date_conflict=True,
    )
    assert review is True
    assert "unknown_person" in reasons
    assert "folder_date_conflict" in reasons


def test_db_schema_version(temp_db):
    """Verifica que el schema version se inicialice y trackee en la versión 4."""
    assert temp_db.schema_version == 4


def test_numpy_dbscan_fallback(temp_db):
    """Verifica que el fallback determinista de DBSCAN en NumPy funcione perfectamente."""
    from unittest.mock import patch

    import numpy as np
    from core.clustering import FaceClustering

    # Insertar algunas caras desconocidas ficticias
    # Queremos 3 puntos cercanos en el espacio (un cluster) y 1 alejado (ruido)
    emb1 = np.zeros(512, dtype=np.float32)
    emb1[0] = 1.0

    emb2 = np.zeros(512, dtype=np.float32)
    emb2[0] = 0.99
    emb2[1] = 0.01

    emb3 = np.zeros(512, dtype=np.float32)
    emb3[0] = 0.98
    emb3[1] = 0.02

    emb_noise = np.zeros(512, dtype=np.float32)
    emb_noise[10] = 1.0  # Ortogonal, muy alejado

    # Registrar en DB
    fid, _ = temp_db.upsert_file("f1.jpg", "f1.jpg")
    temp_db.add_detection(
        fid,
        emb1,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Desconocido",
    )
    temp_db.add_detection(
        fid,
        emb2,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Desconocido",
    )
    temp_db.add_detection(
        fid,
        emb3,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Desconocido",
    )
    temp_db.add_detection(
        fid,
        emb_noise,
        bbox={"top": 0, "right": 10, "bottom": 10, "left": 0},
        assigned_name="Desconocido",
    )

    # Ejecutar clustering forzando HAS_SKLEARN=False
    with patch("core.clustering.HAS_SKLEARN", False):
        fc = FaceClustering(temp_db, eps=0.3, min_samples=3)
        n_clusters = fc.run()

    assert n_clusters == 1

    # Verificar que las detecciones del cluster se actualizaron y el ruido no
    with temp_db._read() as c:
        rows = c.execute("SELECT id, cluster_id FROM Detections ORDER BY id").fetchall()
        assert rows[0]["cluster_id"] == 1
        assert rows[1]["cluster_id"] == 1
        assert rows[2]["cluster_id"] == 1
        assert rows[3]["cluster_id"] is None
