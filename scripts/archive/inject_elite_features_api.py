import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

elite_routes = """
import elite_features

@app.route('/api/search/semantic')
def api_search_semantic():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"results": []})
        
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    results = elite_features.search_semantic_keywords(_GALLERY_CACHE, query)
    return jsonify({"query": query, "count": len(results), "results": results})

@app.route('/api/timeline')
def api_timeline():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    timeline = elite_features.build_timeline_groups(_GALLERY_CACHE)
    return jsonify({"timeline": timeline})

@app.route('/api/person/evolution')
def api_person_evolution():
    identity = request.args.get('identity', 'YO')
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    items = elite_features.build_face_evolution_reel(_GALLERY_CACHE, identity)
    return jsonify({"identity": identity, "count": len(items), "items": items})

@app.route('/api/map/locations')
def api_map_locations():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    all_paths = []
    for cat, idents in _GALLERY_CACHE.items():
        for ident, items in idents.items():
            for it in items:
                all_paths.append(it['path'])
                
    locations = elite_features.get_exif_gps_locations(all_paths)
    return jsonify({"locations": locations, "count": len(locations)})

@app.route('/api/share/<token>/download_zip')
def api_share_download_zip(token):
    info = magic_links.get_magic_link_info(token)
    if not info:
        return jsonify({"error": "Enlace no válido"}), 404
        
    category = info['category']
    identity = info['identity']
    
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    paths = []
    if category in _GALLERY_CACHE and identity in _GALLERY_CACHE[category]:
        paths = [it['path'] for it in _GALLERY_CACHE[category][identity]]
        
    zip_stream = elite_features.create_zip_stream(paths)
    return send_file(
        zip_stream,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"Album_{identity}.zip"
    )
"""

if "import elite_features" not in app_code:
    pos = app_code.find("if __name__ == '__main__':")
    if pos != -1:
        app_code = app_code[:pos] + elite_routes + "\n" + app_code[pos:]

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("✓ Inyectadas rutas de Funcionalidades de Élite en app.py!")
