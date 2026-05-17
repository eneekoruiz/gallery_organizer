# 📸 Smart Gallery AI (Local Personal Organizer)

**Smart Gallery AI** is a local, personal media organizer designed to help you index, search, and manage your private photo and video collection directly on your computer. It uses local AI models (such as YOLOv8 and ArcFace) to run all processing completely offline, ensuring total privacy.

> [!NOTE]
> This is a **local, personal tool** for individual users. It is NOT an enterprise product, nor is it a commercial application.

---

## 🛠️ Honest Design & Technical Scope

Unlike cloud-based services, this application runs entirely on your local hardware.

### Real-world Limitations:
1. **Hardware Dependent Performance**: The speed of the initial scanning and AI indexing depends heavily on your local CPU/GPU. Running this on modest or older equipment will take significant time for large galleries.
2. **AI Model Accuracy**: Local object detection (YOLOv8) and facial recognition (ArcFace) models are highly efficient but are not infallible. They can produce false positives or miss detections, which is why a **Triage Interface (HITL)** is built-in to let you manually review, name, or correct predictions.
3. **Single-User Architecture**: Built as a personal dashboard utilizing a local SQLite database in WAL mode and Streamlit. It is not designed to support concurrent multi-user environments or remote team workflows.
4. **Format Constraints**: Best optimized for common formats (JPEG, PNG, WEBP, MP4, MOV). Advanced raw camera formats or proprietary high-efficiency video formats (HEVC/H.265) may require additional local codecs.

---

## 📅 Heurísticas Inteligentes de Fechas (Smart Date Cascade)

El extractor de fechas analiza cada archivo de forma recursiva a través de una cascada de alta precisión para establecer `best_datetime`, `date_source` y `date_confidence` (`exact`, `month`, `year`, `low`, `unknown`):

1. **Metadatos EXIF (`exact`)**: Lee los metadatos integrados de fecha y hora original.
2. **Nombre de archivo (`exact`)**: Analiza patrones como `IMG_YYYYMMDD_HHMMSS`, `YYYY-MM-DD HH_MM_SS`, `album_YYYY-MM-DD` o `backup_YYYYMMDD`.
3. **Estructura de Directorios (`folder`)**:
   - **Fechas exactas (`exact`)**: Carpetas con patrones `YYYY-MM-DD` o `YYYY_MM_DD`.
   - **Temporadas (`month`)**: Carpetas que contengan estaciones/temporadas, por ejemplo: `verano 2018`, `invierno 2017`, `primavera 2015`, `otoño 2019`.
   - **Estructura anidada año/mes (`month`)**: Subcarpetas de un solo mes de dos dígitos dentro de una carpeta que es un año de 4 dígitos (ej: `/2016/07/`).
   - **Año único (`year`)**: Carpetas nombradas solo con un año de 4 dígitos (ej: `/2014/`).
4. **Sistema de Archivos (`low`)**: Si todo lo demás falla, se usa la fecha de modificación física de disco, marcada estrictamente con confianza baja (`low`).

---

## ⚖️ Decisor Automático de Revisión (ReviewDecider)

Para evitar la falsa sensación de infalibilidad de la IA, cada archivo procesado se analiza bajo **7 criterios avanzados de conflicto** para decidir si va a **`AUTO_CLASSIFIED`** o requiere atención humana en **`NEEDS_REVIEW`**:

*   **unknown_person**: Caras detectadas que no coinciden con ninguna conocida.
*   **multiple_people**: Múltiples rostros en una imagen (pérdida de foco principal).
*   **low_face_confidence**: Caras con confianza por debajo del 85%.
*   **date_uncertain**: Cuando la fecha solo se extrae de metadatos del filesystem de baja confianza.
*   **folder_date_conflict**: Cuando la fecha extraída de la estructura de directorios no coincide con la fecha EXIF/nombre.
*   **duplicate_conflict**: Identificación de duplicados o similares.
*   **ai_disagreement**: Discrepancias entre modelos (por ejemplo, YOLO detecta personas pero no se extraen caras, o se detecta un documento/captura pero contiene rostros).

---

## 🚀 Key Features

- **Local Face Clustering**: Groups detected faces using ArcFace embeddings. Includes a Human-in-the-Loop (HITL) interface to assign names and verify groups.
- **Object & Scene Tagging**: Powered by YOLOv8, automatically tagging files with over 80 standard categories (people, vehicles, pets, furniture, etc.).
- **Semantic Local Search**: Search your gallery using open-source CLIP models with natural language queries (e.g., "beach sunset" or "family dinner") entirely offline.
- **Offline Perceptual Deduplication**: Detects exact duplicates (via SHA256) and similar media (via perceptual pHash) to save local disk space.
- **Video Keyframe Extraction**: Scans videos and extracts only meaningful keyframes for AI processing to avoid duplicate frames.

---

## 🏗 Decoupled Architecture

1. **Scanner & Watchdog**: Recursively scans the input folder and detects new additions in real-time, feeding a serial SQLite queue.
2. **Background Processing Engine**: Processes batches from the queue using ONNX Runtime (running on CPU by default for portability).
3. **SQLite Persistence**: Thread-safe single-file persistence with automatic WAL write-locking. Supports migration versioning (idempotent DB version 3).
4. **Streamlit Triage UI**: Premium web dashboard running locally for curation, semantic search, and manual identity reviews.

---

## 🛠 Installation & Tests

### Prerequisites
- Python 3.9+
- Tesseract OCR (optional, for text detection)

### Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/eneekoruiz/gallery_organizer.git
   cd gallery_organizer
   ```

2. **Install local dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure paths:**
   Configure your input and results directory variables in `smart_gallery_v2/core/config.py`.

4. **Model Downloads**:
   Ensure the required ONNX models are placed in the `models/onnx/` directory before starting.

5. **Run the local dashboard:**
   ```bash
   streamlit run smart_gallery_v2/app.py
   ```

### Running Tests
Para validar que el extractor inteligente de fechas, el decisor de revisión, el motor de la base de datos y la cola de procesamiento están en perfecto estado, ejecuta la suite de pruebas unitarias:
```bash
pytest
```
*Las pruebas simulan las llamadas pesadas de los motores de IA y los tiempos del sistema de archivos mediante mocks para ser seguras, deterministas y súper rápidas.*

---

## ⚖️ License
Licensed under the MIT License.
