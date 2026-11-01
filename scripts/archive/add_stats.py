import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

stats_code = '''
@app.route('/api/stats')
def api_stats():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        return jsonify({"error": "La galería aún no se ha cargado"}), 400
        
    total = 0
    clasificadas = 0
    pendientes = 0
    
    for cat, idents in _GALLERY_CACHE.items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            if cat == 'Personas Sin Nombre' or cat == 'Resultados':
                pendientes += count
            else:
                clasificadas += count
                
    return jsonify({
        "total": total,
        "clasificadas": clasificadas,
        "pendientes": pendientes
    })
'''

end_idx = content.find("if __name__ == '__main__':")
if end_idx != -1:
    content = content[:end_idx] + stats_code + '\n' + content[end_idx:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added /api/stats to app.py")
else:
    print("Could not find main block")
