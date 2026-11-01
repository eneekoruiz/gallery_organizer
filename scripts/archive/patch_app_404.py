import sys

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

if 'return str(e), 500' in app_content:
    app_content = app_content.replace('return str(e), 500', 'return str(e), 404')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)
    print("Patched app.py error handler")
