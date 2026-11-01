import sys

# 1. Patch app.py to include safe_move_file and safe_remove_file
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

safe_file_helpers = """
import gc, time, shutil

def safe_move_file(src, dst):
    src_str, dst_str = str(src), str(dst)
    gc.collect()
    for attempt in range(5):
        try:
            shutil.move(src_str, dst_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    try:
        shutil.copy2(src_str, dst_str)
        try:
            os.remove(src_str)
        except:
            pass
        return True
    except Exception as e:
        raise e

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False
"""

if 'def safe_move_file' not in app_content:
    app_content = app_content.replace('import json', safe_file_helpers + '\nimport json')
    # Replace shutil.move calls with safe_move_file
    app_content = app_content.replace('shutil.move(str(source_path), str(target_path))', 'safe_move_file(source_path, target_path)')
    app_content = app_content.replace('shutil.move(str(p_obj), str(target_path))', 'safe_move_file(p_obj, target_path)')
    app_content = app_content.replace('shutil.move(str(file_path), str(target_file))', 'safe_move_file(file_path, target_file)')
    app_content = app_content.replace('shutil.move(str(file_path), str(target_path))', 'safe_move_file(file_path, target_path)')
    app_content = app_content.replace('os.remove(str(orig_path))', 'safe_remove_file(orig_path)')
    app_content = app_content.replace('os.remove(str(file_path))', 'safe_remove_file(file_path)')
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched app.py with safe_move_file and safe_remove_file")

# 2. Patch index.html to release media before actions
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

release_media_js = """
function releaseMediaElement() {
    try {
        const mediaEl = document.querySelector('.lb-media-element');
        if (mediaEl) {
            mediaEl.pause();
            mediaEl.removeAttribute('src');
            mediaEl.load();
        }
    } catch(e){}
}
"""

if 'function releaseMediaElement()' not in html_content:
    html_content = html_content.replace("</script>", release_media_js + "\n</script>")

if 'releaseMediaElement();' not in html_content:
    html_content = html_content.replace('async function removeFromFolder() {', 'async function removeFromFolder() {\n    releaseMediaElement();')
    html_content = html_content.replace('async function inlineCorrect(', 'async function inlineCorrect(\n    releaseMediaElement();')
    html_content = html_content.replace('async function deleteCurrentFile() {', 'async function deleteCurrentFile() {\n    releaseMediaElement();')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Patched index.html with releaseMediaElement")
