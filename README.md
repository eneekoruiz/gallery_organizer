# Smart AI Gallery Organizer (Local)

Herramienta personal para organizar y buscar en tu galería local utilizando modelos de Inteligencia Artificial (YOLO, ArcFace, CLIP) sin depender de la nube.

## 🌟 Características Reales
- **Detección de Objetos**: Clasificación automática (personas, mascotas, vehículos, etc.) mediante YOLOv8.
- **Reconocimiento Facial**: Agrupación de rostros y búsqueda por identidad con ArcFace.
- **Búsqueda Semántica**: Encuentra fotos con descripciones naturales ("playa al atardecer") gracias a CLIP.
- **Privacidad Total**: Todo el procesamiento es local. Tus datos no salen de tu máquina.
- **Gestión de Errores**: Registro detallado de fallos para depuración técnica.
- **Mantenimiento**: Herramientas integradas para limpiar caché y reconstruir índices.

## ⚠️ Limitaciones y Notas
- **Hardware**: El rendimiento depende de tu CPU/GPU. La primera indexación puede ser lenta en equipos modestos.
- **Precisión**: Los modelos de IA pueden cometer errores. El sistema incluye una bandeja de "Revisión" para ajustes manuales.
- **Personal**: Diseñado para uso individual, no es una plataforma multiusuario ni enterprise.
- **Formatos**: Soporta los formatos de imagen y vídeo más comunes (JPG, PNG, WEBP, MP4, MOV).

## 🚀 Instalación Rápida
1. Instala las dependencias: `pip install -r requirements.txt`
2. Los modelos ONNX deben colocarse en `models/onnx/` (ver guía de descarga).
3. Lanza la app: `streamlit run app.py`

## 🛠️ Desarrollo e Higiene
- Formateado con **Black**.
- Linting con **Ruff**.
- Tests unitarios con **Pytest**.
- CI integrado en GitHub Actions.
