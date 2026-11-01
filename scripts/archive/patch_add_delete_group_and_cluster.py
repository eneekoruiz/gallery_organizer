import os
import re

# 1. Add /api/delete_group to app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

delete_endpoint_code = """
@app.route('/api/delete_group', methods=['POST'])
def api_delete_group():
    try:
        data = request.json
        cat = data.get('cat')
        ident = data.get('ident')
        if not cat or not ident:
            return jsonify({"error": "Parámetros insuficientes"}), 400
            
        group_dir = RESULTADOS_DIR / cat / ident
        if group_dir.exists() and group_dir.is_dir():
            import shutil
            shutil.rmtree(str(group_dir), ignore_errors=True)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Carpeta no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""

if '/api/delete_group' not in app_code:
    app_code = app_code.replace("if __name__ == '__main__':", delete_endpoint_code + "\n\nif __name__ == '__main__':")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("app.py actualizado con endpoint /api/delete_group.")

# 2. Add '💥 Disolver este Grupo' button in templates/index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

old_group_header = """            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1.5rem;">
                <div>
                    <h1 id="grid-title" style="font-size:2rem; font-weight:800; tracking:-0.03em;">Galería</h1>
                    <p id="grid-subtitle" style="color:var(--text-dim); font-size:0.9rem; margin-top:4px;"></p>
                </div>
                <button id="btn-rename-group" onclick="renameCurrentGroup()" style="display:none; background:var(--accent-green); color:white; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; font-size:0.9rem; box-shadow:0 4px 12px rgba(48,209,88,0.3);">🏷️ Renombrar todo este Grupo</button>
            </div>"""

new_group_header = """            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1.5rem;">
                <div>
                    <h1 id="grid-title" style="font-size:2rem; font-weight:800; tracking:-0.03em;">Galería</h1>
                    <p id="grid-subtitle" style="color:var(--text-dim); font-size:0.9rem; margin-top:4px;"></p>
                </div>
                <div style="display:flex; gap:10px;">
                    <button id="btn-rename-group" onclick="renameCurrentGroup()" style="display:none; background:var(--accent-green); color:white; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; font-size:0.9rem; box-shadow:0 4px 12px rgba(48,209,88,0.3);">🏷️ Renombrar todo este Grupo</button>
                    <button id="btn-delete-group" onclick="deleteCurrentGroup()" style="display:none; background:#ff453a; color:white; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; font-size:0.9rem; box-shadow:0 4px 12px rgba(255,69,58,0.3);">💥 Disolver este Grupo</button>
                </div>
            </div>"""

html_code = html_code.replace(old_group_header, new_group_header)

# Show/Hide btn-delete-group in renderGrid
old_render_grid_btn = """            const btnRename = document.getElementById('btn-rename-group');
            if (cat === 'Personas Sin Nombre') {
                btnRename.style.display = 'block';
            } else {
                btnRename.style.display = 'none';
            }"""

new_render_grid_btn = """            const btnRename = document.getElementById('btn-rename-group');
            const btnDelete = document.getElementById('btn-delete-group');
            if (cat === 'Personas Sin Nombre') {
                btnRename.style.display = 'block';
                btnDelete.style.display = 'block';
            } else {
                btnRename.style.display = 'none';
                btnDelete.style.display = 'none';
            }"""

html_code = html_code.replace(old_render_grid_btn, new_render_grid_btn)

# Add deleteCurrentGroup JS function
delete_fn_code = """
        async function deleteCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            if (!confirm(`¿Seguro que quieres disolver el grupo '${currentIdent}'? Las fotos no se borrarán de tus álbumes.`)) return;
            
            showToast(`⏳ Disolviendo grupo '${currentIdent}'...`);
            const res = await fetch('/api/delete_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ cat: currentCat, ident: currentIdent })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🗑️ Grupo '${currentIdent}' disuelto con éxito.`);
                await loadIdentities();
                await loadGallery();
                renderGrid('Resultados', 'Conocidos');
            } else {
                showToast(data.error || "No se pudo disolver el grupo.", true);
            }
        }
"""

if 'function deleteCurrentGroup()' not in html_code:
    html_code = html_code.replace('async function submitMergeGroup() {', delete_fn_code + '\n        async function submitMergeGroup() {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

print("templates/index.html actualizado con botón '💥 Disolver este Grupo'.")
