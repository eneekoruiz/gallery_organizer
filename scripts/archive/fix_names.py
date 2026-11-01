import os
import shutil
from pathlib import Path

RESULTADOS_DIR = Path(r"D:\Galeria Eneko NO ABRIR\Resultados")
FOTOS_DIR = Path(r"D:\Galeria Eneko NO ABRIR\Fotos")

def get_identities():
    identities = []
    if FOTOS_DIR.exists():
        for cat in FOTOS_DIR.iterdir():
            if cat.is_dir():
                for ident in cat.iterdir():
                    if ident.is_dir():
                        identities.append({"categoria": cat.name, "identidad": ident.name})
    return identities

identities = get_identities()

def fix_directory(base_dir):
    if not base_dir.exists(): return 0
    
    # Sort identities by length descending so "Ibai Sanchez" matches before "Ibai"
    identities.sort(key=lambda x: len(x['identidad']), reverse=True)
    
    moved_count = 0
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_lower = file.lower().replace("_", " ").replace("-", " ")
            current_path = Path(root) / file
            
            for id_obj in identities:
                raw_ident = id_obj['identidad']
                # Eliminar prefijo como "C. ", "F. "
                clean_ident = raw_ident[3:] if raw_ident[1:3] == ". " else raw_ident
                clean_ident_lower = clean_ident.lower().replace("_", " ")
                
                words = clean_ident_lower.split()
                if not words: continue
                
                # Exigir que contenga todas las palabras del nombre limpio de identidad
                match = all(w in file_lower for w in words)
                
                if match:
                    correct_dir = base_dir / id_obj['categoria'] / raw_ident
                    
                    if current_path.parent != correct_dir:
                        print(f"[REUBICANDO] {file} -> {id_obj['categoria']}/{raw_ident}")
                        correct_dir.mkdir(parents=True, exist_ok=True)
                        correct_path = correct_dir / file
                        
                        if not correct_path.exists():
                            shutil.move(str(current_path), str(correct_path))
                        else:
                            import time
                            correct_path = correct_dir / f"{current_path.stem}_mov_{int(time.time() * 1000)}{current_path.suffix}"
                            shutil.move(str(current_path), str(correct_path))
                        moved_count += 1
                    break 
    return moved_count

REVISION_DIR = Path(r"D:\Galeria Eneko NO ABRIR\Revision_Interactiva")
print("Verificando nombres de archivo mal ubicados...")
c1 = fix_directory(RESULTADOS_DIR)
c2 = fix_directory(FOTOS_DIR)
c3 = fix_directory(REVISION_DIR)
print(f"Completado. Reubicados en Resultados: {c1}, Fotos: {c2}, Revision: {c3}")
