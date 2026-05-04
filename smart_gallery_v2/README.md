# 🖼️ Smart AI Gallery Organizer · v2.0 Comercial

> **Supera a Apple Photos y Google Photos** en control, privacidad y personalización.  
> YOLOv8 · ArcFace · CLIP · Sistema de Triaje · Etiquetado Faceless · Symlinks de Grupos

---

## 🏗️ Arquitectura

```
smart_gallery_v2/
│
├── app.py                       ← Entry point Streamlit
│
├── core/
│   ├── config.py                ← Configuración única (rutas, umbrales, ONNX paths)
│   ├── database.py              ← DatabaseManager: WAL, 6 tablas, Undo/Redo, Triage
│   ├── watchdog_engine.py       ← FileSystemWatcher: eventos del SO en tiempo real
│   ├── symlink_manager.py       ← Symlinks multiplataforma para fotos grupales
│   ├── ai_engines.py            ← YOLOEngine · ArcFaceEngine · CLIPEngine · FaissIndex
│   ├── video_processor.py       ← VideoKeyframeExtractor (SSIM + histograma)
│   └── worker.py                ← ProcessingEngine: máquina de estados, pause/resume exacto
│
├── ui/
│   ├── styles.py                ← CSS premium dark theme, masonry, triage badges
│   ├── tab_dashboard.py         ← Métricas triage, controles ▶⏸⏹, log terminal
│   ├── tab_gallery.py           ← Masonry grid, búsqueda CLIP, bulk actions
│   ├── tab_triage.py            ← 3 bandejas + faceless tagging + inspector BBox
│   └── tab_timeline.py          ← Cronología EXIF + mapa GPS
│
├── models/onnx/                 ← Modelos ONNX (opcional, fallback a librerías nativas)
├── Galería/
│   ├── Para Organizar/          ← ⬅ DRAG & DROP TUS FOTOS AQUÍ
│   ├── Resultados/              ← Organización automática con symlinks
│   └── Fotos/                   ← Fotos de referencia para identidades
│
├── .thumbnails/                 ← Cache WebP (auto)
├── .face_crops/                 ← Recortes faciales para HITL (auto)
├── gallery.db                   ← SQLite WAL (auto)
└── requirements.txt
```

---

## 🗃️ Esquema de Base de Datos

```sql
PRAGMA journal_mode=WAL;   -- Lecturas concurrentes sin bloqueo

KnownFaces      -- Identidades: embedding ArcFace O NULL para faceless
FileQueue       -- Cola de trabajo: status, triage_tier, EXIF, GPS, retries
Detections      -- Caras detectadas: bbox, confidence, triage_tier, is_faceless
FileIdentities  -- Relación N:M archivo ↔ persona → ruta del symlink
ClipEmbeddings  -- Embeddings CLIP para búsqueda semántica
TxHistory       -- Historial de transacciones (Undo/Redo)
FsEvents        -- Log de eventos del watchdog
```

### Máquina de Estados

```
PENDING ──► PROCESSING ──► DONE   (triage_tier: safe | review | unclassified)
                │
                ├──► PENDING  (retry < 3)
                └──► ERROR    (retry ≥ 3)
```

### Sistema de Triaje (Tiers de Confianza)

| Tier | Confianza | Bandeja | Acción |
|------|-----------|---------|--------|
| `safe` | > 85% | ✅ Seguros | Auto-clasificado, sin intervención |
| `review` | 40–85% | 🔶 Revisar | La IA propone, 1 clic para confirmar/denegar |
| `unclassified` | < 40% | ❓ Sin Clasificar | Manual o faceless tagging |

---

## 🚀 Instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Arrancar
streamlit run app.py --server.port 8501 --server.maxUploadSize 500
```

### (Opcional) Exportar modelos ONNX para máxima velocidad

```bash
# YOLOv8
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx', opset=17)"
mv yolov8n.onnx models/onnx/

# CLIP
python -c "
import open_clip, torch
model, _, prep = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
model.eval()
dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(model.visual, dummy, 'models/onnx/clip_visual.onnx', opset_version=14)
"
```

---

## ⚙️ Flujo de Procesamiento Completo

```
📁 Para Organizar/
       │
       ▼  Watchdog detecta en tiempo real (drag & drop)
┌──────────────────────────────────────────────────────────────────────────┐
│                        ProcessingEngine                                   │
│  1. ThumbnailWorker (hilo dedicado) → WebP 512×512 asíncrono             │
│  2. EXIF → fecha ISO-8601 + coordenadas GPS                               │
│  3. YOLOv8 ONNX batch → tags de objetos (persona, perro, coche…)         │
│  4. ArcFace ONNX + RetinaFace → embeddings faciales                      │
│  5. FAISS search:                                                         │
│     · dist < 0.65 y conf > 85% → tier=safe    (auto-clasificado)         │
│     · dist < 0.65 y conf 40-85% → tier=review (pide validación)          │
│     · dist ≥ 0.65 → Desconocido, tier=unclassified → HITL queue          │
│  6. CLIP → embedding visual (búsqueda semántica en lenguaje natural)      │
│  7. Multi-tag grupos → crear N symlinks (1 por persona identificada)      │
│  8. DB update → status=DONE, triage_tier, tags, EXIF, GPS                │
└──────────────────────────────────────────────────────────────────────────┘
       │
       ▼
📁 Resultados/
   ├── Ana_García/     ← symlink de foto_001.jpg (Ana aparece en ella)
   ├── Carlos/         ← symlink de foto_001.jpg (Carlos también aparece)
   ├── perro/          ← copia de foto_002.jpg
   └── SinClasificar/  ← archivos sin detección
```

**Sin duplicación de disco**: la foto grupal `foto_001.jpg` tiene un symlink en la carpeta de Ana Y en la de Carlos, pero el archivo físico existe solo una vez.

---

## 👤 Etiquetado Faceless (Novedad)

Permite taggear personas sin rostro visible (de espaldas, siluetas, parcialmente ocultas):

1. Ve a **⚖️ Triaje → Etiquetado Manual**
2. Selecciona la foto
3. Asigna un nombre (existente o nuevo)
4. Opcionalmente define el bounding box del cuerpo
5. El sistema crea el symlink y registra la identidad **sin embedding facial**

La identidad se almacena en `KnownFaces` con `is_faceless=TRUE` y `embedding=NULL`.

---

## 🎛️ Controles de la UI

| Tab | Función |
|-----|---------|
| **Dashboard** | 7 métricas incluyendo triage · ▶⏸⏹ con pause/resume exacto · Log terminal · Watchdog toggle |
| **Galería** | Masonry grid · Búsqueda semántica CLIP · Bulk rename/asignar · Inspector con BBoxes |
| **Triaje** | 3 bandejas por confianza · 1-clic confirmar/denegar · Faceless tagging · Bulk actions |
| **Línea de Tiempo** | Bar chart por día · Filtro de rango · Miniaturas del período · Mapa GPS |

---

## 🔧 Parámetros clave (`core/config.py`)

```python
CONF_HIGH   = 0.85   # > 85% → bandeja Segura (auto)
CONF_MEDIUM = 0.40   # 40-85% → bandeja Revisar
FAISS_THRESHOLD = 0.65  # Distancia máxima para reconocer
BATCH_SIZE  = 8      # Imágenes por lote de inferencia
THUMB_SIZE  = (512, 512)
THUMB_FORMAT = "WEBP"
```

---

## 🛡️ Resiliencia y Producción

- **WAL mode**: UI lee mientras el motor IA escribe. Sin bloqueos.
- **Pause/Resume exacto**: el estado vive en la DB. Al pausar y reanudar, continúa desde el mismo archivo.
- **3 reintentos**: archivos que fallan se reintentan automáticamente antes de marcarse como ERROR.
- **Graceful shutdown**: `stop()` espera a que el archivo actual termine limpiamente.
- **Undo/Redo**: `TxHistory` permite revertir renombrados masivos en un clic.
- **Symlinks seguros**: detección de duplicados, fallback a hardlinks en Windows sin permisos.
- **gc.collect()**: limpieza de memoria tras cada archivo para evitar leaks en sesiones largas.
- **Thread-safe**: `threading.Lock()` explícito en todas las escrituras SQLite.
