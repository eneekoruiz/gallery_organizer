import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Reset Zoom button in toolbar
toolbar_target = '<button class="icon-btn" onclick="toggleMetadata()" title="Info y Personas">ℹ️ Personas</button>'
toolbar_replacement = '<button class="icon-btn" onclick="resetZoom()" title="Resetear Zoom">🔍 100%</button>\n                <button class="icon-btn" onclick="toggleMetadata()" title="Info y Personas">ℹ️ Personas</button>'

content = content.replace(toolbar_target, toolbar_replacement)

# Add Zoom JS Logic
zoom_script = """
        // Motor de Zoom Interactivo con Rueda del Ratón y Panoramización (Pan)
        let zoomLevel = 1.0;
        let panX = 0;
        let panY = 0;
        let isPanDragging = false;
        let panStartX = 0;
        let panStartY = 0;

        function resetZoom() {
            zoomLevel = 1.0;
            panX = 0;
            panY = 0;
            applyZoomTransform();
        }

        function applyZoomTransform() {
            const container = document.getElementById('lb-media-container');
            if (container) {
                container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            const wrapper = document.getElementById('viewer-wrapper');
            if (!wrapper) return;

            // Rueda del Ratón para Zoom
            wrapper.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.15 : -0.15;
                const oldZoom = zoomLevel;
                zoomLevel = Math.min(Math.max(1.0, zoomLevel + delta), 4.0);

                if (zoomLevel === 1.0) {
                    panX = 0;
                    panY = 0;
                }
                applyZoomTransform();
            }, { passive: false });

            // Panoramización con Arrastre cuando hay Zoom
            wrapper.addEventListener('mousedown', (e) => {
                if (zoomLevel > 1.0 && !e.target.closest('.lb-bounding-box') && !e.target.closest('.resize-handle')) {
                    isPanDragging = true;
                    panStartX = e.clientX - panX;
                    panStartY = e.clientY - panY;
                    wrapper.style.cursor = 'grabbing';
                }
            });

            document.addEventListener('mousemove', (e) => {
                if (isPanDragging && zoomLevel > 1.0) {
                    panX = e.clientX - panStartX;
                    panY = e.clientY - panStartY;
                    applyZoomTransform();
                }
            });

            document.addEventListener('mouseup', () => {
                if (isPanDragging) {
                    isPanDragging = false;
                    const wrapper = document.getElementById('viewer-wrapper');
                    if (wrapper) wrapper.style.cursor = 'default';
                }
            });
        });
"""

# Insert zoom_script before openLightbox function
open_lb_idx = content.find("async function openLightbox(")
content = content[:open_lb_idx] + zoom_script + "\n\n" + content[open_lb_idx:]

# Also ensure openLightbox resets zoom when opening a new photo
content = content.replace("async function openLightbox(item) {", "async function openLightbox(item) {\n            resetZoom();")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con Zoom interactivo por rueda del ratón y panoramización.")
