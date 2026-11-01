import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Async Guard in runAnalysis
old_run_analysis_start = '''async function runAnalysis() {
            if (!currentFileObj) return;'''
new_run_analysis_start = '''async function runAnalysis() {
            if (!currentFileObj) return;
            const currentRunPath = currentFileObj.path;'''

old_run_analysis_mid = '''                data = await res.json();
            } catch (err) {'''
new_run_analysis_mid = '''                data = await res.json();
            } catch (err) {'''
            
# Let's just do a regex replace for the fetch await block to add the check
content = re.sub(
    r'(const res = await fetch\(\'/api/analyze\'.*?data = await res\.json\(\);\s*\}\s*catch[^{]*\{\s*[^}]*\s*\}\s*)(cardsContainer\.innerHTML = \'\';)',
    r'\1if (currentFileObj.path !== currentRunPath) return; \2',
    content,
    flags=re.DOTALL
)

if 'const currentRunPath = currentFileObj.path;' not in content:
    content = content.replace(old_run_analysis_start, new_run_analysis_start)

# Fix 2: Marcar Persona Reset Zoom
old_manual = '''        function enableManualSelection() {
            if (!currentFileObj) return;'''
new_manual = '''        function enableManualSelection() {
            if (!currentFileObj) return;
            resetZoom(); // Prevenir panning y offsets erróneos
            window.isDrawingMode = true;'''
content = content.replace(old_manual, new_manual)

# Fix 3: Disable Panning when drawing
old_pan = '''            wrapper.addEventListener('mousedown', (e) => {
                if (zoomLevel > 1.0 && !e.target.closest('.lb-bounding-box') && !e.target.closest('.resize-handle')) {'''
new_pan = '''            wrapper.addEventListener('mousedown', (e) => {
                if (window.isDrawingMode) return;
                if (zoomLevel > 1.0 && !e.target.closest('.lb-bounding-box') && !e.target.closest('.resize-handle')) {'''
content = content.replace(old_pan, new_pan)

# Turn off isDrawingMode when done drawing
old_mouseup = '''                    container.style.cursor = 'default';
                    
                    const rect = container.getBoundingClientRect();'''
new_mouseup = '''                    container.style.cursor = 'default';
                    window.isDrawingMode = false;
                    
                    const rect = container.getBoundingClientRect();'''
content = content.replace(old_mouseup, new_mouseup)

# Optional: Add requestAnimationFrame to applyZoomTransform
# It's better to throttle the mousemove event
old_mousemove = '''            document.addEventListener('mousemove', (e) => {
                if (isPanDragging && zoomLevel > 1.0) {
                    panX = e.clientX - panStartX;
                    panY = e.clientY - panStartY;
                    applyZoomTransform();
                }
            });'''
new_mousemove = '''            let panTicking = false;
            document.addEventListener('mousemove', (e) => {
                if (isPanDragging && zoomLevel > 1.0) {
                    panX = e.clientX - panStartX;
                    panY = e.clientY - panStartY;
                    if (!panTicking) {
                        window.requestAnimationFrame(() => {
                            applyZoomTransform();
                            panTicking = false;
                        });
                        panTicking = true;
                    }
                }
            });'''
content = content.replace(old_mousemove, new_mousemove)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Patched index.html for bugs")
