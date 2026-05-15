# 📸 Smart Gallery AI (v2.0)

**Smart Gallery AI** is a professional-grade local media organizer powered by state-of-the-art AI models. It classifies, deduplicates, and searches your local photo and video collection using advanced Computer Vision, without ever uploading data to the cloud.

---

## 🚀 Key Features

- **Advanced Face Recognition**: Uses **ArcFace** (via ONNX) for high-precision face identification.
- **Object Detection**: Powered by **YOLOv8** for tagging over 80 categories of objects.
- **Semantic Search (CLIP)**: Search your gallery with natural language (e.g., "sunset at the beach", "people eating pizza").
- **Real-time Watchdog**: Automatically detects and processes new files as they arrive in the monitored directory.
- **Content-based Deduplication**: Identifies identical files using SHA256 and perceptual hashes (pHash).
- **Video Intelligence**: Extracts keyframes from videos based on scene changes (SSIM + Histogram) to detect people and objects without redundant processing.
- **Multi-platform Symlinks**: Organizes files into virtual folders (Resultados/) using symbolic links, keeping your original files untouched.
- **Human-in-the-Loop (HITL)**: A dedicated triage interface to verify and correct AI predictions, with real-time model learning.

---

## 🏗 Architecture

The system is built with a decoupled architecture for maximum stability:

1.  **Scanner & Watchdog**: Monitors the input directory and feeds the SQLite queue.
2.  **Processing Engine**: A robust background worker that orchestrates AI models and persistence.
3.  **SQLite WAL Database**: Ensures ACID compliance and handles high-concurrency between the worker and the UI.
4.  **Streamlit UI**: A modern dashboard for monitoring, searching, and managing the gallery.

---

## 🛠 Installation

### Prerequisites
- Python 3.9+
- Tesseract OCR (optional, for document scanning)

### Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/eneekoruiz/gallery_organizer.git
    cd gallery_organizer
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure paths:**
    Edit `smart_gallery_v2/core/config.py` to set your `DIR_ENTRADA` and `DIR_RESULT`.

4.  **Run the application:**
    ```bash
    streamlit run smart_gallery_v2/app.py
    ```

---

## ⚖️ License
This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔬 Audit Status
- **Security**: Local-only processing. No external API calls.
- **Stability**: Atomic transactions and automatic session locking.
- **Integrity**: SHA256 content verification.
