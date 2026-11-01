import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

stats_endpoint = '''
@app.route('/api/stats')
def api_stats():
    global _GALLERY_CACHE, known_faces
    if _GALLERY_CACHE is None:
        return jsonify({"error": "Galería no cargada"})
        
    stats = {
        "total_conocidos": 0,
        "total_pendientes": 0,
        "total_dudosos": 0,
        "identidades_unicas": len(known_faces) if known_faces else 0
    }
    
    for cat, idents in _GALLERY_CACHE.items():
        for ident, items in idents.items():
            count = len(items)
            if cat == 'Conocidos' or cat == 'Familiares':
                stats['total_conocidos'] += count
            elif cat == 'Personas Sin Nombre':
                stats['total_pendientes'] += count
            elif cat == 'Resultados':
                if ident == '_Dudosos':
                    stats['total_dudosos'] += count
                else:
                    stats['total_conocidos'] += count
                    
    return jsonify(stats)
'''

if 'def api_stats' not in content:
    content = content.replace("if __name__ == '__main__':", stats_endpoint + "\nif __name__ == '__main__':")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched /api/stats!")
else:
    print("Already patched.")
