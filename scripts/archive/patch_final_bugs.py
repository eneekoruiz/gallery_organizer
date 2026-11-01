import re

# 1. FIX APP.PY 500 ERROR (UnboundLocalError target_path)
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()
    
old_apply = '''def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    if not filepath or not os.path.exists(filepath):
        return None
    orig_path = Path(filepath)
    is_manual_source = False'''
new_apply = '''def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    if not filepath or not os.path.exists(filepath):
        return None
    orig_path = Path(filepath)
    target_path = orig_path
    is_manual_source = False'''
if old_apply in app_content:
    app_content = app_content.replace(old_apply, new_apply)
    print("Fixed target_path UnboundLocalError in app.py")
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

# 2. FIX CSS RESIZE HANDLES OVERLAP
with open('static/style.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

old_resize = '''.resize-handle {
    position: absolute;
    width: 14px;
    height: 14px;
    background: #fff;'''
new_resize = '''.resize-handle {
    position: absolute;
    width: 10px;
    height: 10px;
    background: #fff;
    display: none;
}
.lb-bounding-box.active .resize-handle {
    display: block;'''
if '.lb-bounding-box.active .resize-handle' not in css_content and old_resize in css_content:
    css_content = css_content.replace(old_resize, new_resize)
    print("Fixed CSS resize handles overlap")
with open('static/style.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# 3. FIX JS INJECTION AND AUTOMATIC GALLERY RELOAD
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Fix the broken script tags from previous patches
html_content = html_content.replace('</script>\n</body>\n\n        let boxesVisible = true;', '')
html_content = html_content.replace('</script>\n</body>\n\n        async function scanFullVideo()', '')
html_content = re.sub(r'</script>\s*</body>\s*let boxesVisible = true;.*?\}', '', html_content, flags=re.DOTALL)
html_content = re.sub(r'</script>\s*</body>\s*async function scanFullVideo\(\).*?\}', '', html_content, flags=re.DOTALL)

# Let's clean up any junk text at the end of index.html
html_content = re.sub(r'</script>.*?</body>', '</script>\n</body>', html_content, flags=re.DOTALL)

# Inject the functions properly INSIDE the script tag
js_to_inject = '''
        let boxesVisible = true;
        function toggleBoxes() {
            boxesVisible = !boxesVisible;
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.opacity = boxesVisible ? '1' : '0';
                b.style.pointerEvents = boxesVisible ? 'auto' : 'none';
            });
            const btn = document.getElementById('btn-toggle-boxes');
            if (btn) btn.innerHTML = boxesVisible ? '👁️ Ocultar Recuadros' : '👁️ Mostrar Recuadros';
        }

        async function scanFullVideo() {
            if (!currentFileObj || !isCurrentVideo) return;
            const btn = document.getElementById('btn-scan-video');
            const resDiv = document.getElementById('video-scan-results');
            if(!btn || !resDiv) return;
            
            btn.textContent = "⏳ Escaneando (puede tardar unos segundos)...";
            btn.style.pointerEvents = 'none';
            btn.style.opacity = '0.5';
            resDiv.innerHTML = '<div style="text-align:center;"><div class="loader-small"></div></div>';
            
            try {
                const res = await fetch('/api/scan_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const data = await res.json();
                
                if (data.error) {
                    resDiv.innerHTML = `<p style="color:#ff453a;">Error: ${data.error}</p>`;
                } else if (data.detections && data.detections.length > 0) {
                    let html = '<h4 style="margin:0 0 10px 0; color:var(--text); font-size:0.9rem;">Personas Detectadas:</h4>';
                    data.detections.forEach(d => {
                        html += `<div style="background:rgba(0,0,0,0.3); padding:8px; border-radius:8px; margin-bottom:8px;">`;
                        html += `<div style="font-weight:bold; color:#0a84ff; margin-bottom:4px;">👤 ${d.identity}</div>`;
                        html += `<div style="font-size:0.8rem; color:var(--text-dim);">Segundos: `;
                        d.seconds.forEach(sec => {
                            html += `<span onclick="document.getElementById('lb-media-container').querySelector('video').currentTime = ${sec}" style="cursor:pointer; display:inline-block; padding:2px 6px; background:rgba(255,255,255,0.1); border-radius:4px; margin:2px; transition:0.2s;">${sec}s</span>`;
                        });
                        html += `</div></div>`;
                    });
                    resDiv.innerHTML = html;
                } else {
                    resDiv.innerHTML = '<p style="color:var(--text-dim); font-size:0.8rem;">No se encontraron caras conocidas en todo el vídeo.</p>';
                }
            } catch (err) {
                resDiv.innerHTML = '<p style="color:#ff453a;">Error de conexión al escanear vídeo.</p>';
            }
            
            btn.textContent = "🎬 Volver a Escanear Vídeo";
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        }
'''

if 'function toggleBoxes()' not in html_content:
    html_content = html_content.replace('</script>\n</body>', js_to_inject + '\n</script>\n</body>')
    print("Injected JS functions properly")

# Fix automatic gallery reload on api_correct
old_ui_correct = '''                fetch('/api/correct', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: currentFileObj.path,
                        new_categoria: categoryName,
                        new_identidad: face.identity,
                        face: {x: face.x, y: face.y, width: face.width, height: face.height}
                    })
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('Recuadro guardado y reaprendizaje activo.');
                    }
                });'''
new_ui_correct = '''                fetch('/api/correct', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: currentFileObj.path,
                        new_categoria: categoryName,
                        new_identidad: face.identity,
                        face: {x: face.x, y: face.y, width: face.width, height: face.height}
                    })
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('Recuadro guardado. Actualizando galería...');
                        loadGallery();
                        if (isCurrentVideo) {
                            setTimeout(() => closeLightbox(), 500);
                        }
                    }
                });'''
if old_ui_correct in html_content:
    html_content = html_content.replace(old_ui_correct, new_ui_correct)
    print("Fixed automatic UI refresh on api_correct")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
    
print("All patches applied!")
