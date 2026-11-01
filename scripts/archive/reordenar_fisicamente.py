import os
import shutil
from pathlib import Path
import json

FOTOS_DIR = Path("Fotos")
RESULTADOS_DIR = Path("Resultados")

def get_file_key(filepath):
    try:
        return str(os.stat(filepath).st_ino)
    except:
        return str(filepath)

def ensure_physical_paths():
    try:
        with open('gallery.json', 'r', encoding='utf-8') as f:
            gallery = json.load(f)
    except:
        print("No se encontró gallery.json. Ejecuta la app y carga la galería primero.")
        return

    moved = 0
    for cat, idents in gallery.items():
        for ident, items in idents.items():
            for item in items:
                source_path = item.get('path')
                if not source_path or not os.path.exists(source_path):
                    continue
                
                source_path_obj = Path(source_path)
                
                # Determine target directory
                if "Dataset" in item.get('source', ''):
                    target_dir = FOTOS_DIR / cat / ident
                else:
                    target_dir = RESULTADOS_DIR / cat / ident
                    
                target_dir.mkdir(parents=True, exist_ok=True)
                
                if source_path_obj.parent.resolve() == target_dir.resolve():
                    continue
                    
                target_path = target_dir / source_path_obj.name
                
                # Verify if hardlink exists
                exists = False
                source_ino = os.stat(source_path).st_ino
                for f in target_dir.iterdir():
                    if f.is_file() and os.stat(str(f)).st_ino == source_ino:
                        exists = True
                        break
                        
                if not exists:
                    counter = 1
                    while target_path.exists():
                        target_path = target_dir / f"{source_path_obj.stem}_{counter}{source_path_obj.suffix}"
                        counter += 1
                    try:
                        os.link(source_path, str(target_path))
                        moved += 1
                    except Exception:
                        try:
                            shutil.copy2(source_path, str(target_path))
                            moved += 1
                        except:
                            pass
                            
    print(f"Archivos sincronizados/creados físicamente: {moved}")
    
    # Cleanup empty directories
    for base in [FOTOS_DIR, RESULTADOS_DIR]:
        for root, dirs, files in os.walk(str(base), topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except:
                    pass
    print("Limpieza de directorios vacíos completada.")

if __name__ == '__main__':
    ensure_physical_paths()
