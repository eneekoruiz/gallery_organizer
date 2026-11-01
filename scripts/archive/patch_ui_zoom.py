import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add toggle button next to 'PERSONAS DETECTADAS'
old_title = 'PERSONAS DETECTADAS'
new_title = '''PERSONAS DETECTADAS 
                <button id="btn-toggle-boxes" onclick="toggleBoxes()" style="float:right; background:transparent; border:none; color:#0a84ff; cursor:pointer; font-size:0.8rem; margin-top:2px;">👁️ Ocultar</button>'''
if 'id="btn-toggle-boxes"' not in content:
    content = content.replace(old_title, new_title, 1)

# 2. Add toggleBoxes function
toggle_js = '''
        let boxesVisible = true;
        function toggleBoxes() {
            boxesVisible = !boxesVisible;
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.opacity = boxesVisible ? '1' : '0';
                b.style.pointerEvents = boxesVisible ? 'auto' : 'none';
            });
            const btn = document.getElementById('btn-toggle-boxes');
            if (btn) btn.innerHTML = boxesVisible ? '👁️ Ocultar' : '👁️ Mostrar';
        }
'''
if 'function toggleBoxes()' not in content:
    content = content.replace('</script>\n</body>', toggle_js + '\n</script>\n</body>')

# 3. Fix Zoom Limits and Freeze
old_wheel = '''            wrapper.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.15 : -0.15;
                const oldZoom = zoomLevel;
                zoomLevel = Math.min(Math.max(1.0, zoomLevel + delta), 4.0);

                if (zoomLevel === 1.0) {
                    panX = 0;
                    panY = 0;
                }
                applyZoomTransform();
            }, { passive: false });'''

new_wheel = '''            let zoomTicking = false;
            wrapper.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.3 : -0.3;
                zoomLevel = Math.min(Math.max(1.0, zoomLevel + delta), 16.0);

                if (zoomLevel === 1.0) {
                    panX = 0;
                    panY = 0;
                }
                
                if (!zoomTicking) {
                    window.requestAnimationFrame(() => {
                        applyZoomTransform();
                        zoomTicking = false;
                    });
                    zoomTicking = true;
                }
            }, { passive: false });'''

if '16.0' not in content:
    content = content.replace(old_wheel, new_wheel)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Patched UI zooming and toggle successfully")
