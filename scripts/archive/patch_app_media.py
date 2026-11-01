import sys

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

if 'return send_file(filepath)' in app_content:
    app_content = app_content.replace('return send_file(filepath)', 'return send_file(filepath, conditional=True)')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)
    print("Patched app.py send_file")
