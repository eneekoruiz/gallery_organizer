import sys

# 1. Fix app.py imports to include Response from flask
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

old_flask_import = "from flask import Flask, render_template, request, jsonify, send_file"
new_flask_import = "from flask import Flask, render_template, request, jsonify, send_file, Response"

if old_flask_import in app_code:
    app_code = app_code.replace(old_flask_import, new_flask_import)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("Fixed Flask Response import in app.py")

# 2. Fix index.html String(face.confidence).includes
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

old_js_line = ": (face.confidence ? (face.confidence.includes('Manual') ? '✏️ Editado a Mano' : face.confidence) : '🤖 IA (Pendiente)')}"
new_js_line = ": (face.confidence ? (String(face.confidence).includes('Manual') ? '✏️ Editado a Mano' : face.confidence) : '🤖 IA (Pendiente)')}"

if old_js_line in html_code:
    html_code = html_code.replace(old_js_line, new_js_line)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_code)
    print("Fixed String(face.confidence).includes in index.html")
