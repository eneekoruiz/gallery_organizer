import sys

# 1. Patch api_analyze in app.py to force re-analysis on video frames
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

old_cache_check = """    if filepath in faces_cache:
        # Check if file modification time changed? Or just trust it.
        # Actually, let's just return it for max speed
        return jsonify({"faces": faces_cache[filepath]})"""

new_cache_check = """    force_reanalyze = data.get('force', False) or is_video or (data.get('timestamp') is not None)
    if not force_reanalyze and filepath in faces_cache:
        return jsonify({"faces": faces_cache[filepath]})"""

if old_cache_check in app_code:
    app_code = app_code.replace(old_cache_check, new_cache_check)
    print("Patched api_cache_check to bypass cache on video frame analysis in app.py")
else:
    print("Could not match old_cache_check in app.py")

# Ensure image dimensions are included in returned face data
old_return_faces = "return jsonify({\"faces\": faces_data})"
new_return_faces = """for f_d in faces_data:
            if 'img_width' not in f_d: f_d['img_width'] = w
            if 'img_height' not in f_d: f_d['img_height'] = h
        return jsonify({"faces": faces_data})"""

if old_return_faces in app_code:
    app_code = app_code.replace(old_return_faces, new_return_faces)
    print("Patched img_width/img_height inclusion in api_analyze in app.py")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

# 2. Patch runAnalysis in templates/index.html to pass force: true and handle video dimensions cleanly
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

old_fetch_body = "body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp })"
new_fetch_body = "body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp, force: true })"

if old_fetch_body in html_code:
    html_code = html_code.replace(old_fetch_body, new_fetch_body)
    print("Patched force: true in runAnalysis in index.html")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)
