# Guía de Mejora: Reducción de Excepciones Amplias

Este documento guía el refactoring futuro de `except Exception` amplios en `core/worker.py` y `core/ai_engines.py` para mejor rastreabilidad y debugging.

## Estrategia Recomendada

### Fase 1: Categorización (implementar gradualmente)
En lugar de capturar todo con `except Exception`, especificar por categoría:

```python
# ❌ Evitar (demasiado amplio)
try:
    result = process_image(path)
except Exception:
    log.error("Failed")
    pass

# ✅ Mejor (específico y logueable)
try:
    result = process_image(path)
except (IOError, OSError) as e:
    log.warning("File read error: %s", e)
    # Fallback: usar placeholder
except ValueError as e:
    log.error("Invalid image format: %s", e)
    # Fallback: skip file
except Exception as e:
    log.exception("Unexpected error during processing: %s", e)
    # Fallback: skip and continue
```

### Fase 2: Patrones por Módulo

#### `core/worker.py` - Thumbnail Processing
- **IOError/OSError**: Fallos de I/O (disco, permisos) → log.warning + fallback
- **ValueError**: Datos inválidos → log.info + skip
- **Exception**: Errores inesperados → log.exception + metrics

#### `core/worker.py` - ONNX Inference
- **RuntimeError**: Errores de ONNX Runtime → log.error + fallback a CPU
- **MemoryError**: OOM durante inferencia → log.critical + skip batch
- **Exception**: Inesperados → log.exception + retry

#### `core/ai_engines.py` - Model Loading
- **FileNotFoundError**: Modelo no encontrado → log.error + fallback
- **torch.cuda.OutOfMemoryError**: GPU OOM → log.warning + CPU fallback
- **Exception**: Inesperados → log.exception

### Fase 3: Prioridades

1. **Alta**: Bloques que silencian errores críticamente (ej. inferencia YOLO)
2. **Media**: Procesamiento de archivos (thumbnails, OCR)
3. **Baja**: Operaciones opcionales (tags, duplicate detection)

## Casos Actuales en `worker.py`

| Línea | Contexto | Tipo | Prioridad | Acción Sugerida |
|-------|----------|------|-----------|-----------------|
| 74 | Thumbnail I/O | IOError → ImageProcessingError | Alta | Especificar OSError |
| 92 | PIL thumbnail | ValueError → FormatError | Media | Especificar Image.DecompressionBombError |
| 121 | YOLO inference | RuntimeError/CUDA | Alta | Especificar OnnxRuntimeError |
| 174 | ArcFace processing | RuntimeError → RuntimeError | Alta | Especificar con fallback |
| 193 | CLIP processing | RuntimeError → RuntimeError | Alta | Especificar |
| 206 | OCR fallback | pytesseract.TesseractNotFoundError | Media | Especificar |
| 225 | DB insert | IntegrityError → DatabaseError | Alta | Especificar sqlite3.IntegrityError |

## Implementación Gradual

**Recomendación**: refactorizar 2-3 bloques por semana, agregando métricas con cada cambio.

```python
# Ejemplo de refactoring con métricas
from core.metrics import metrics

try:
    result = ai_engines.run_yolo(frame)
except RuntimeError as e:
    log.warning("YOLO inference failed: %s, using fallback", e)
    metrics.increment("yolo_failures")
    result = fallback_detection()
except Exception as e:
    log.exception("Unexpected error in YOLO: %s", e)
    metrics.increment("yolo_errors_unexpected")
    result = None
```

## Testing

Cada refactoring debe incluir:
1. Test que fuerza el error específico
2. Validación que el fallback funciona
3. Validación que las métricas se registran correctamente

Ejemplo:
```python
def test_yolo_inference_fallback():
    # Mock RuntimeError
    with patch('ai_engines.onnx_session.run') as mock:
        mock.side_effect = RuntimeError("CUDA out of memory")
        result = worker._process_frame_yolo(frame)
        assert result is not None  # Fallback applied
        assert metrics.get("yolo_failures") > 0
```

---

**Nota**: Este refactoring mantiene backward-compatibility y mejora debugging sin sacrificar resiliencia.
