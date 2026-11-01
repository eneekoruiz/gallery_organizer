import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update detector creation score_threshold to 0.20
content = content.replace(
    "0.4,  # umbral sensible para no perder caras reales",
    "0.20,  # umbral ultra-sensible a 0.20 para capturar fotos con sombras/piercings/ángulos"
)

# 2. Update api_analyze detector score_threshold and fallback box
old_analyze_detect = """        if img is not None and detector is not None and recognizer is not None:
            height, width, _ = img.shape
            detector.setInputSize((width, height))
            _, faces = detector.detect(img)"""

new_analyze_detect = """        if img is not None and detector is not None and recognizer is not None:
            height, width, _ = img.shape
            detector.setInputSize((width, height))
            detector.setScoreThreshold(0.20)
            _, faces = detector.detect(img)"""

content = content.replace(old_analyze_detect, new_analyze_detect)

# 3. Update fallback box in api_analyze
old_fallback_block = """            if best_idx != -1:
                                faces_data[best_idx]["identity"] = folder_owner
                                faces_data[best_idx]["confidence"] = "✨ 100.0% (Propietario del Álbum)" """

new_fallback_block = """            if best_idx != -1:
                                faces_data[best_idx]["identity"] = folder_owner
                                faces_data[best_idx]["confidence"] = "✨ 100.0% (Propietario del Álbum)"
        elif is_valid_owner and len(faces_data) == 0:
            # Recuadro de rescate automático para fotos sin caras detectadas dentro de un álbum
            faces_data.append({
                "x": int(width * 0.15),
                "y": int(height * 0.15),
                "width": int(width * 0.70),
                "height": int(height * 0.70),
                "img_width": width,
                "img_height": height,
                "identity": folder_owner,
                "confidence": "✨ Recuadro de Rescate (Álbum)"
            })"""

content = content.replace(old_fallback_block, new_fallback_block)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado: YuNet en umbral ultra-sensible 0.20 y recuadro de rescate en álbumes.")
