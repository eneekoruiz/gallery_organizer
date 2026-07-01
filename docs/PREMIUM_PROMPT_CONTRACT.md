# PREMIUM PROMPT CONTRACT

## Directiva Principal: Riesgo Cero por Diseño (Erradicación Implacable)

Este documento es un contrato vinculante para cualquier agente o desarrollador que modifique la base de código `smart_gallery_v2`.

### 1. Tolerancia Cero al Silenciamiento
- **PROHIBIDO** el uso de `except Exception:` sin una causa justificada (como en la última capa de un worker thread para evitar crashear el loop principal), y aun así DEBE incluir log.exception() y reporte de métricas.
- Todo bloque `try-except` debe capturar la excepción **más específica** posible (`sqlite3.IntegrityError`, `OSError`, `torch.cuda.OutOfMemoryError`).

### 2. Aislamiento de Transacciones (Blast Radius)
- Las operaciones de base de datos no deben mezclarse en el mismo bloque `try-except` que las operaciones de inferencia de IA o de manipulación de archivos.
- Cada fase del pipeline de IA debe tener su propia validación y manejo de errores.

### 3. Fallbacks Semánticos
- Si una operación de IA falla (e.g. YOLO), el fallback debe ser explícito, reportado en logs como `WARNING` o `ERROR`, y el flujo debe continuar con un estado degradado controlado, no oculto.

### 4. Validaciones Redundantes (Fail Fast)
- Antes de invocar a motores en C/C++ (ONNX, PyTorch), los tensores, imágenes y rutas deben ser validados estrictamente (dimensiones, existencia, permisos) en Python puro.

**Cualquier PR o parche generado por IA que viole estas directivas será rechazado inmediatamente.**
