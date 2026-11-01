import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

sidebar_str = """
        <div style="margin-top: 10px; margin-bottom: 20px; font-weight: bold; color: #0a84ff; text-align: center; border: 1px solid #0a84ff; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(10,132,255,0.1);" onclick="openIntelligentCleanup()">
            🧠 Limpieza Inteligente
        </div>
"""

sidebar_replacement = """
        <div style="margin-top: 10px; margin-bottom: 10px; font-weight: bold; color: #0a84ff; text-align: center; border: 1px solid #0a84ff; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(10,132,255,0.1);" onclick="openIntelligentCleanup()">
            🧠 Limpieza Inteligente
        </div>
        <div style="margin-bottom: 20px; font-weight: bold; color: #30d158; text-align: center; border: 1px solid #30d158; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(48,209,88,0.1);" onclick="runMassCleanup()">
            🧹 Limpieza Global
        </div>
"""

if sidebar_str in content:
    content = content.replace(sidebar_str, sidebar_replacement)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added global cleanup button to sidebar")
else:
    print("Could not find sidebar injection point")
