import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_highlight = '''        function highlightFace(faceNum) {
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.borderColor = 'rgba(255, 255, 255, 0.4)';
                b.style.zIndex = '1';
                b.classList.remove('active');
            });
            document.querySelectorAll('.person-card').forEach(c => c.style.background = 'rgba(28, 28, 30, 0.5)');
            
            const box = document.getElementById(`bbox-${faceNum}`);
            if (box) {
                box.style.borderColor = '#0a84ff';
                box.style.zIndex = '10';
                box.classList.add('active');
                
                // Auto-Focus Zoom
                const mediaEl = document.getElementById('lb-media');
                if (mediaEl && box.dataset.faceX) {
                    const intrinsicWidth = mediaEl.naturalWidth || mediaEl.videoWidth;
                    const intrinsicHeight = mediaEl.naturalHeight || mediaEl.videoHeight;
                    
                    if (intrinsicWidth && intrinsicHeight) {
                        const fx = parseFloat(box.dataset.faceX);
                        const fy = parseFloat(box.dataset.faceY);
                        const fw = parseFloat(box.dataset.faceW);
                        const fh = parseFloat(box.dataset.faceH);
                        
                        const centerX = fx + (fw / 2);
                        const centerY = fy + (fh / 2);
                        
                        const renderScale = mediaEl.clientWidth / intrinsicWidth;
                        
                        const offX = centerX - (intrinsicWidth / 2);
                        const offY = centerY - (intrinsicHeight / 2);
                        
                        zoomLevel = 4.0; // Fixed zoom 400%
                        panX = -(offX * renderScale) * zoomLevel;
                        panY = -(offY * renderScale) * zoomLevel;
                        
                        applyZoomTransform();
                    }
                }
            }
            
            const card = document.getElementById(`person-card-${faceNum}`);
            if (card) {
                card.style.background = 'rgba(10, 132, 255, 0.2)';
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }'''

if 'function highlightFace(faceNum) {' in content:
    content = re.sub(r'function highlightFace\(faceNum\) \{.*?\}\s*\}', new_highlight, content, flags=re.DOTALL)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched highlightFace!")
else:
    print("Could not find highlightFace")
