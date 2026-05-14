import pytest
from unittest.mock import patch, MagicMock
from smart_gallery_v2.core.ai_engines import YOLOEngine, ArcFaceEngine

def test_yolo_lazy_loading():
    """Verifica que YOLO no se cargue hasta llamar a detect()."""
    # Resetear singleton para el test
    YOLOEngine._instance = None
    
    with patch("smart_gallery_v2.core.ai_engines._load_ort") as mock_load:
        engine = YOLOEngine()
        # No debería haberse cargado aún
        mock_load.assert_not_called()
        
        # Simular llamada que requiere el modelo
        try:
            engine._ensure_loaded()
        except:
            pass 
        
        assert mock_load.called

def test_singleton_behavior():
    """Verifica que múltiples instancias compartan el mismo estado."""
    YOLOEngine._instance = None
    e1 = YOLOEngine()
    e2 = YOLOEngine()
    assert e1 is e2
    
    ArcFaceEngine._instance = None
    a1 = ArcFaceEngine()
    a2 = ArcFaceEngine()
    assert a1 is a2
