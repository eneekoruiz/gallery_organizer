import sys

# 1. Add API endpoints to app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

dup_endpoints = """
@app.route('/api/purge_exact_duplicates', methods=['POST'])
def api_purge_exact_duplicates():
    global _GALLERY_CACHE, faces_cache
    import hashlib
    size_map = {}
    base_dir = Path(r'C:\\Users\\User\\Desktop\\Galeria Eneko NO ABRIR')
    
    for root, dirs, files in os.walk(str(base_dir)):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
                p = Path(root) / f
                try:
                    sz = p.stat().st_size
                    if sz not in size_map: size_map[sz] = []
                    size_map[sz].append(p)
                except: pass
                
    hash_map = {}
    for sz, paths in size_map.items():
        if len(paths) > 1:
            for p in paths:
                try:
                    with open(p, 'rb') as f:
                        md5 = hashlib.md5(f.read()).hexdigest()
                    if md5 not in hash_map: hash_map[md5] = []
                    hash_map[md5].append(p)
                except: pass
                
    purged_count = 0
    for md5, paths in hash_map.items():
        if len(paths) > 1:
            def score_path(p):
                p_str = str(p)
                score = 0
                if 'Resultados' in p_str: score += 10
                if 'Conocidos' in p_str or 'Familia' in p_str or 'YO' in p_str: score += 10
                if '_Dudosos' in p_str: score -= 5
                return score
            sorted_paths = sorted(paths, key=score_path, reverse=True)
            for rem in sorted_paths[1:]:
                try:
                    safe_remove_file(rem)
                    purged_count += 1
                except: pass
                
    _GALLERY_CACHE = None
    return jsonify({"success": True, "purged_count": purged_count})
"""

if 'def api_purge_exact_duplicates' not in app_content:
    app_content = app_content.replace("@app.route('/api/metadata')", dup_endpoints + "\n\n@app.route('/api/metadata')")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched app.py with api_purge_exact_duplicates")

# 2. Add button & handler in index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

sidebar_target = """                    <button class="sidebar-btn" onclick="runMassCleanup()" style="background: linear-gradient(135deg, #30d158 0%, #1b8a37 100%); margin-top: 10px;">
                        🧹 Limpieza Global
                    </button>"""

sidebar_replacement = """                    <button class="sidebar-btn" onclick="runMassCleanup()" style="background: linear-gradient(135deg, #30d158 0%, #1b8a37 100%); margin-top: 10px;">
                        🧹 Limpieza Global
                    </button>
                    <button class="sidebar-btn" onclick="purgeExactDuplicates()" style="background: linear-gradient(135deg, #ff9f0a 0%, #c67900 100%); margin-top: 8px;">
                        👯 Limpieza de Duplicados
                    </button>"""

if sidebar_target in html_content:
    html_content = html_content.replace(sidebar_target, sidebar_replacement)

js_dup_purge = """
async function purgeExactDuplicates() {
    if (!confirm("¿Deseas escanear y eliminar automáticamente todos los duplicados exactos (archivos idénticos en disco)? Conservaremos siempre la mejor copia.")) return;
    
    showToast("⏳ Escaneando y eliminando duplicados idénticos...", false);
    
    try {
        const res = await fetch('/api/purge_exact_duplicates', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ Limpieza completada: Se eliminaron ${data.purged_count} copias duplicadas idénticas.`);
            await loadIdentities();
            await loadGallery();
        } else {
            showToast("Error limpiando duplicados: " + (data.error || "Desconocido"), true);
        }
    } catch(err) {
        showToast("Error de conexión al purgar duplicados", true);
    }
}
"""

if 'function purgeExactDuplicates()' not in html_content:
    html_content = html_content.replace("</script>", js_dup_purge + "\n</script>")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Injected Purge Exact Duplicates button into sidebar in index.html")
