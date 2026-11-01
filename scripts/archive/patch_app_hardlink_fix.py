import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardlink management block in api_correct
old_hardlink_block = """    # File Management (Hardlinks)
    target_path = orig_path
    if new_categoria != "Ignorar":
        target_dir = RESULTADOS_DIR / new_categoria / new_identidad
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / orig_path.name
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
            counter += 1
            
        try:
            # Crear enlace duro en la nueva carpeta
            os.link(str(orig_path), str(target_path))"""

new_hardlink_block = """    # File Management (Hardlinks Sin Duplicados)
    target_path = orig_path
    if new_categoria != "Ignorar":
        target_dir = RESULTADOS_DIR / new_categoria / new_identidad
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # SI LA FOTO YA ESTÁ EN LA CARPETA DESTINO, NO CREAR NINGÚN ENLACE NI COPIA NUEVA!
        if orig_path.parent.resolve() == target_dir.resolve():
            target_path = orig_path
        else:
            # Comprobar si ya existe un enlace duro a este mismo inodo en la carpeta destino
            orig_ino = os.stat(str(orig_path)).st_ino
            existing_link = None
            for f in target_dir.iterdir():
                if f.is_file() and os.stat(str(f)).st_ino == orig_ino:
                    existing_link = f
                    break
                    
            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))"""

content = content.replace(old_hardlink_block, new_hardlink_block)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado: se ha eliminado la generación de hardlinks duplicados en la misma carpeta.")
