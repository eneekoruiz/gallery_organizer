import re

# 1. Restore the Modal in index.html and add Avatar to Grid Header
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

modal_html = '''
    <!-- Modal de Fusión / Renombrado de Grupo -->
    <div id="modal-merge" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.85); backdrop-filter:blur(15px); z-index:9999; align-items:center; justify-content:center;">
        <div style="background:rgba(28,28,30,0.95); border:1px solid rgba(255,255,255,0.2); border-radius:18px; padding:25px; width:440px; max-width:90%; box-shadow:0 20px 50px rgba(0,0,0,0.8); color:white;">
            <h2 style="margin-top:0; font-size:1.25rem;">🤝 Fusionar o Renombrar Grupo</h2>
            <p style="font-size:0.85rem; color:#aaa; margin-bottom:20px;">
                Asigna las <strong id="merge-count-span">3</strong> fotos de '<span id="merge-group-name">Persona Nueva</span>' a una persona de tu galería para mejorar el aprendizaje IA:
            </p>
            
            <div style="margin-bottom:15px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#30d158;">
                    🔗 Opción A: Fusionar con persona ya existente
                </label>
                <select id="merge-existing-select" style="width:100%; padding:10px; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem;">
                    <option value="">-- Selecciona persona --</option>
                </select>
            </div>
            
            <div style="text-align:center; font-size:0.8rem; color:#666; margin:10px 0;">— O BIEN —</div>
            
            <div style="margin-bottom:20px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#0a84ff;">
                    ✨ Opción B: Crear una persona nueva
                </label>
                <input type="text" id="merge-new-input" placeholder="Nombre de la nueva persona..." style="width:100%; padding:10px; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem; box-sizing:border-box;">
            </div>
            
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="closeMergeModal()" style="background:transparent; border:none; color:#aaa; padding:10px 16px; font-size:0.9rem; cursor:pointer;">Cancelar</button>
                <button onclick="submitMergeGroup()" style="background:#30d158; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:0.9rem; cursor:pointer;">🚀 Aplicar Fusión / Guardar</button>
            </div>
        </div>
    </div>
    
    <div id="floating-action-bar" class="floating-action-bar">
        <span class="fab-count" id="fab-count">0 seleccionadas</span>
        <select id="fab-reassign-select" class="fab-select">
            <option value="">-- Reasignar a... --</option>
        </select>
        <button class="fab-btn" onclick="applyBulkReassign()" style="color:#0a84ff; font-weight:bold;">Aplicar</button>
        <button class="fab-btn" onclick="applyBulkIgnore()" style="color:#ff453a;">Ignorar Todo</button>
        <div style="width:1px; height:20px; background:rgba(255,255,255,0.2);"></div>
        <button class="fab-btn" onclick="clearSelection()">Cancelar</button>
    </div>
</body>'''

if 'id="modal-merge"' not in html:
    html = html.replace('</body>', modal_html)
    print("Restored modal")

old_header = '''                <div style="flex:1;">
                    <h2 style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.5px;">${currentCat} / ${currentIdent}</h2>
                    <p style="margin:5px 0 0 0; color:#888; font-size:0.9rem;">${currentFolderItems.length} elementos</p>
                </div>'''
new_header = '''                <div style="display:flex; align-items:center; gap:20px; flex:1;">
                    <img id="person-avatar-img" src="/api/person_avatar?cat=${encodeURIComponent(currentCat)}&ident=${encodeURIComponent(currentIdent)}" style="width:70px; height:70px; border-radius:50%; object-fit:cover; border:2px solid #30d158; box-shadow:0 0 15px rgba(0,0,0,0.4);" onerror="this.style.display='none'">
                    <div>
                        <h2 style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.5px;">${currentCat} / ${currentIdent}</h2>
                        <p style="margin:5px 0 0 0; color:#888; font-size:0.9rem;">${currentFolderItems.length} elementos</p>
                    </div>
                </div>'''
if old_header in html:
    html = html.replace(old_header, new_header)
    print("Added avatar header")
    
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)


# 2. Add /api/person_avatar to app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_py = f.read()

avatar_endpoint = '''
@app.route('/api/person_avatar')
def api_person_avatar():
    cat = request.args.get('cat')
    ident = request.args.get('ident')
    if not cat or not ident:
        return "Missing params", 400
        
    target_dir = FOTOS_DIR / cat / ident
    if not target_dir.exists():
        return "Not found", 404
        
    # Find first valid image
    first_img_path = None
    valid_exts = {".jpg", ".jpeg", ".png"}
    for f in target_dir.iterdir():
        if f.is_file() and f.suffix.lower() in valid_exts:
            first_img_path = str(f.resolve())
            break
            
    if not first_img_path:
        return "No image found", 404
        
    # Look up face in cache
    face_box = None
    overrides = load_overrides()
    file_key = get_file_key(first_img_path)
    
    if file_key in overrides:
        for ov in overrides[file_key]:
            if ov.get('identity') == ident:
                face_box = ov
                break
                
    if not face_box and first_img_path in faces_cache:
        for fc in faces_cache[first_img_path]:
            if fc.get('identity') == ident:
                face_box = fc
                break
                
    try:
        file_bytes = np.fromfile(first_img_path, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: return "Bad image", 500
        
        if face_box:
            x, y, w, h = int(face_box['x']), int(face_box['y']), int(face_box['width']), int(face_box['height'])
            # Expand box slightly for a better avatar
            pad_x = int(w * 0.2)
            pad_y = int(h * 0.2)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(img.shape[1], x + w + pad_x)
            y2 = min(img.shape[0], y + h + pad_y)
            cropped = img[y1:y2, x1:x2]
        else:
            # Fallback to center crop if no face box found
            h, w = img.shape[:2]
            sz = min(h, w)
            cropped = img[h//2 - sz//2 : h//2 + sz//2, w//2 - sz//2 : w//2 + sz//2]
            
        _, buf = cv2.imencode('.jpg', cropped)
        return Response(buf.tobytes(), mimetype='image/jpeg')
    except Exception as e:
        print("Avatar error:", e)
        return str(e), 500
'''
if 'def api_person_avatar()' not in app_py:
    app_py += avatar_endpoint
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_py)
    print("Added /api/person_avatar endpoint")

