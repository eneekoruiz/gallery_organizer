"""
MEGA-PATCH V4: Dissolve _Dudosos by removing original file, and dynamically create Conmigo/Sin Mi virtual folders.
"""
import sys, re, os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except: pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

changes = 0

# ============================================================
# FIX 1: Dissolve _Dudosos in apply_correction_to_file
# ============================================================
old_file_mgmt = """            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))
                except Exception:
                    try:
                        import shutil
                        shutil.copy2(str(orig_path), str(target_path))
                    except Exception:
                        pass"""

new_file_mgmt = """            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))
                except Exception:
                    try:
                        import shutil
                        shutil.copy2(str(orig_path), str(target_path))
                    except Exception:
                        pass
                        
            # DISSOLVE DUDOSOS: If the original file was in a dudosos folder, remove it
            orig_str = str(orig_path)
            if "_Dudosos" in orig_str or "Desconocidos" in orig_str or "Personas Sin Nombre" in orig_str:
                try:
                    if os.path.exists(orig_str):
                        os.remove(orig_str)
                except Exception as e:
                    print("Could not dissolve dudosos file:", e)"""

if old_file_mgmt in app_code:
    app_code = app_code.replace(old_file_mgmt, new_file_mgmt)
    changes += 1
    print("[1] Added logic to dissolve _Dudosos in apply_correction_to_file")

# ============================================================
# FIX 2: Dynamic "Conmigo / Sin Mí" folders in get_gallery
# ============================================================
# We need to insert this logic right after the virtual multi-person inclusion loop.
pattern = r"if not any\(x\['path'\] == item\['path'\] for x in gallery\[other_cat\]\[clean_other_id\]\):\s*gallery\[other_cat\]\[clean_other_id\]\.append\(item\)"
match = re.search(pattern, app_code)
if match:
    dynamic_group_logic = match.group(0) + r"""
        
        # --- DYNAMIC GROUP FOLDERS: Conmigo / Sin Mi ---
        known_ids_in_file = set()
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                known_ids_in_file.add(other_id)
        
        if len(known_ids_in_file) > 1:
            has_yo = 'YO' in known_ids_in_file
            has_fam = any(x.startswith('F. ') for x in known_ids_in_file)
            has_con = any(x.startswith('C. ') for x in known_ids_in_file)
            
            grp_cat = None
            grp_ident = None
            
            if has_yo:
                if has_fam:
                    grp_cat = 'Familia'
                    grp_ident = 'Familiares conmigo'
                elif has_con:
                    grp_cat = 'Conocidos'
                    grp_ident = 'Conocidos conmigo'
            else:
                if has_fam:
                    grp_cat = 'Familia'
                    grp_ident = 'Familiares sin mí'
                elif has_con:
                    grp_cat = 'Conocidos'
                    grp_ident = 'Conocidos sin mí'
                    
            if grp_cat and grp_ident:
                if grp_cat not in gallery: gallery[grp_cat] = {}
                if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
                if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                    gallery[grp_cat][grp_ident].append(item)
"""
    app_code = app_code.replace(match.group(0), dynamic_group_logic)
    changes += 1
    print("[2] Added dynamic group folders logic (Conmigo / Sin Mi)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print(f"\n=== Backend: {changes} patches applied ===")
