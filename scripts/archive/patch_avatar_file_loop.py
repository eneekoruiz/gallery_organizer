import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_avatar_loop = """    # Find first valid image
    first_img_path = None
    valid_exts = {".jpg", ".jpeg", ".png"}
    for f in target_dir.iterdir():
        if f.is_file() and f.suffix.lower() in valid_exts:
            first_img_path = str(f.resolve())
            break"""

new_avatar_loop = """    # Find first valid image
    first_img_path = None
    valid_exts = {".jpg", ".jpeg", ".png"}
    if target_dir.is_file():
        if target_dir.suffix.lower() in valid_exts:
            first_img_path = str(target_dir.resolve())
    elif target_dir.is_dir():
        for f in target_dir.iterdir():
            if f.is_file() and f.suffix.lower() in valid_exts:
                first_img_path = str(f.resolve())
                break"""

if old_avatar_loop in content:
    content = content.replace(old_avatar_loop, new_avatar_loop)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched target_dir.is_file vs is_dir in api_person_avatar")
else:
    print("Could not match old_avatar_loop in app.py")
