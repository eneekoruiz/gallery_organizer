import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_stack = """        <div style="margin-bottom: 20px; font-weight: bold; color: #30d158; text-align: center; border: 1px solid #30d158; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(48,209,88,0.1);" onclick="runMassCleanup()">
            🧹 Limpieza Global
        </div>"""

new_stack = """        <div style="margin-bottom: 10px; font-weight: bold; color: #30d158; text-align: center; border: 1px solid #30d158; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(48,209,88,0.1);" onclick="runMassCleanup()">
            🧹 Limpieza Global
        </div>
        <div style="margin-bottom: 10px; font-weight: bold; color: #ff9f0a; text-align: center; border: 1px solid #ff9f0a; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(255,159,10,0.1);" onclick="openExactDuplicatesModal()">
            👯 Limpieza de Duplicados Exactos
        </div>
        <div style="margin-bottom: 20px; font-weight: bold; color: #bf5af2; text-align: center; border: 1px solid #bf5af2; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(191,90,242,0.1);" onclick="openSimilarPhotosModal()">
            📸 Fotos Parecidas y Ráfagas
        </div>"""

if old_stack in html:
    html = html.replace(old_stack, new_stack)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✓ Successfully placed cleaner buttons in sidebar top action stack!")
else:
    print("Could not match old_stack in index.html")
