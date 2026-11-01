import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_rename_loop = """                try:
                    os.link(str(file_path), str(target_file))
                    safe_remove_file(file_path)
                    moved_count += 1
                except:
                    try:
                        import shutil
                        safe_move_file(file_path, target_file)
                        moved_count += 1
                    except:
                        pass"""

new_rename_loop = """                try:
                    shutil.move(str(file_path), str(target_file))
                    moved_count += 1
                except Exception as e:
                    try:
                        safe_move_file(file_path, target_file)
                        moved_count += 1
                    except:
                        pass"""

if old_rename_loop in content:
    content = content.replace(old_rename_loop, new_rename_loop)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched fast file moving in api_rename_group")
else:
    print("Could not match old_rename_loop in app.py")
