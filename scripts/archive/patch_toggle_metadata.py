import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

js_func = """
function toggleMetadata() {
    const sidebar = document.getElementById('lb-sidebar');
    if (sidebar.style.display === 'none' || sidebar.style.display === '') {
        sidebar.style.display = 'block';
    } else {
        sidebar.style.display = 'none';
    }
}
"""

if 'function toggleMetadata()' not in content:
    content = content.replace('// Funciones Auxiliares', js_func + '\n// Funciones Auxiliares')
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added toggleMetadata")
else:
    print("toggleMetadata already exists")
