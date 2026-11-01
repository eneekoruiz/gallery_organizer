# ðŸ”® Smart Gallery AI â€” Pro Edition

Organizador y visor inteligente de fotografÃ­as y vÃ­deos con inteligencia artificial local (100% privado, sin nube externa), reconocimiento facial de alta precisiÃ³n, eliminaciÃ³n de duplicados exactos y visor interactivo estilo Apple Photos.

---

## ðŸš€ CÃ³mo Iniciar la AplicaciÃ³n

### MÃ©todo 1: Doble Clic (Recomendado)
- Haz doble clic sobre **`Iniciar_SmartGallery.bat`** (o **`Iniciar_SmartGallery_Silencioso.vbs`**).
- La aplicaciÃ³n se iniciarÃ¡ y abrirÃ¡ automÃ¡ticamente tu navegador en `http://127.0.0.1:5000`.

### MÃ©todo 2: Desde la Terminal
```bash
# Con el launcher de Python
py app.py

# O con python directo
python app.py
```

---

## ðŸ§  Â¿CÃ³mo Funciona por Debajo?

### 1. DetecciÃ³n y Reconocimiento Facial (YuNet + SFace)
- **DetecciÃ³n UltrarrÃ¡pida (YuNet ONNX):** Localiza todos los rostros en milisegundos con coordenadas bounding box y 5 puntos de referencia facial.
- **Reconocimiento y Embeddings (SFace ONNX):** Extrae un vector matemÃ¡tico de 128 dimensiones por cada rostro.
- **Centroides DinÃ¡micos:** Calcula el centroide matemÃ¡tico de cada persona (*YO, Familia, Conocidos*). La similitud coseno agrupa automÃ¡ticamente las fotos con confianza estadÃ­stica (> 50% alta, 38-50% media, < 38% revisiÃ³n).

### 2. DetecciÃ³n de Duplicados y RÃ¡fagas
- **Duplicados Exactos (SHA-256):** Compara el hash criptogrÃ¡fico byte a byte de los archivos. Si dos fotos son idÃ©nticas, permite purgar rÃ©plicas sin tocar la original.
- **RÃ¡fagas y Similitud Perceptual (dHash + Varianza Laplaciana):** Compara la diferencia de gradientes y calcula la nitidez mediante la varianza del operador de Laplace. Identifica automÃ¡ticamente fotos repetidas y destaca la toma mÃ¡s nÃ­tida para conservar.

### 3. Soporte Completo Apple iCloud & Android
- Distingue fotos provenientes de Apple iCloud (`ðŸŽ`) y fotos locales/Android (`ðŸ¤–`).
- Soporta *Live Photos* con previsualizaciÃ³n en movimiento al pasar el cursor.
- Extrae metadatos EXIF completos: modelo de cÃ¡mara, lente, apertura (`f/1.8`), velocidad (`1/120s`), ISO, resoluciÃ³n, megapÃ­xeles y coordenadas GPS.

---

## ðŸ“¸ Formatos Soportados

| Tipo | Extensiones |
| :--- | :--- |
| **FotografÃ­a** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`, `.bmp`, `.tiff` |
| **VÃ­deo y Live Photos** | `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v` |

---

## âŒ¨ï¸ Atajos de Teclado del Visor (Lightbox)

| Tecla | AcciÃ³n |
| :--- | :--- |
| `â†’` / `â†` | Foto siguiente / Foto anterior |
| `Espacio` | Reproducir / Pausar vÃ­deo |
| `1` â€“ `5` | Asignar persona sugerida al instante (Modo Triage) |
| `+` / `-` / `0` | Acercar / Alejar / Reiniciar zoom |
| `I` | Abrir Inspector de metadatos EXIF y GPS |
| `B` | Mostrar / Ocultar recuadros de detecciÃ³n facial |
| `Ctrl + K` | BÃºsqueda global Spotlight |
| `Supr` / `Del` | Eliminar archivo |
| `Esc` | Cerrar visor o modal |
| `?` | Abrir panel de ayuda de atajos |

---

## ðŸ§ª BaterÃ­a de Pruebas Automatizadas (TDD)

El proyecto incluye un entorno de testing aislado con mocks en `tests/`:

```bash
py tests/run_all_tests.py
```
- âœ… Integridad atÃ³mica de archivos y protecciÃ³n contra sobreescritura.
- âœ… ExtracciÃ³n de metadatos EXIF y mitigaciÃ³n de archivos corruptos.
- âœ… DetecciÃ³n de duplicados por hash SHA-256.
- âœ… Prueba de estrÃ©s con 1.000 archivos simulados.
- ðŸ›¡ï¸ **Riesgo de pÃ©rdida de datos: 0%.**