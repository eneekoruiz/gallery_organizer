// ============================================================
// BOXES.JS - Face Bounding Boxes, Interactive Selection & AI Detection
// ============================================================

window.currentFaces = [];

window.triggerDeepScanLightbox = function(imgEl, container, cardsContainer) {
    if (!window.currentFileObj || !window.currentFileObj.path) return;
    
    imgEl = imgEl || document.querySelector('#lb-media-container img');
    container = container || document.getElementById('lb-media-container');
    cardsContainer = cardsContainer || document.getElementById('person-cards-container') || document.getElementById('lb-faces-list');
    
    if (cardsContainer) {
        cardsContainer.innerHTML = '<div style="color:#64d2ff; font-size:12px; padding:15px; text-align:center;"><div class="loader-small" style="margin:0 auto 8px auto;"></div>Analizando caras con IA...</div>';
    }

    // Remove existing boxes
    if (container) {
        container.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());
    }

    fetch('/api/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ path: window.currentFileObj.path, force: true })
    }).then(r => r.json()).then(data => {
        const faces = data.faces || [];
        window.currentFaces = faces;
        
        if (faces.length === 0) {
            if (cardsContainer) {
                cardsContainer.innerHTML = `
                    <div style="text-align:center; padding:20px; color:#8e8e93;">
                        <div style="font-size:24px; margin-bottom:6px;">👤</div>
                        <div style="font-size:12px; font-weight:600; color:#ccc;">No se detectaron rostros</div>
                        <div style="font-size:11px; margin-top:4px;">Foto de paisaje, objeto o texto.</div>
                    </div>
                `;
            }
            return;
        }

        if (cardsContainer) cardsContainer.innerHTML = '';

        faces.forEach((face, idx) => {
            const faceNum = idx + 1;
            const confPct = Math.round((face.confidence || 0.85) * 100);
            const identity = face.identity || 'Desconocido';
            const isKnown = identity !== 'Desconocido' && !identity.startsWith('Persona Nueva');

            // Render Face Card in Panel
            if (cardsContainer) {
                const card = document.createElement('div');
                card.className = 'lb-face-card';
                card.id = `face-card-${faceNum}`;
                card.style.cssText = 'display:flex; align-items:center; gap:10px; padding:10px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:12px; margin-bottom:8px; cursor:pointer; transition:all 0.15s;';
                card.onmouseover = () => {
                    card.style.background = 'rgba(10,132,255,0.12)';
                    card.style.borderColor = 'rgba(10,132,255,0.4)';
                    highlightBox(faceNum);
                };
                card.onmouseout = () => {
                    card.style.background = 'rgba(255,255,255,0.04)';
                    card.style.borderColor = 'rgba(255,255,255,0.08)';
                };

                card.innerHTML = `
                    <div style="width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg, #0a84ff, #bf5af2); color:#fff; font-weight:800; font-size:12px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        #${faceNum}
                    </div>
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:700; font-size:13px; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${identity}</div>
                        <div style="font-size:11px; color:${isKnown ? '#30d158' : '#ffd60a'}; font-weight:600;">Coincidencia: ${confPct}%</div>
                    </div>
                    <button onclick="window.openManualCorrection(${faceNum}, '${encodeURIComponent(identity)}')" style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); color:#64d2ff; padding:5px 10px; border-radius:8px; font-size:11px; font-weight:600; cursor:pointer; flex-shrink:0;">
                        Corregir
                    </button>
                `;
                cardsContainer.appendChild(card);
            }

            // Render Glowing Box on Image if dimensions known
            if (container && imgEl) {
                const fx = parseFloat(face.x || (face.box ? face.box[0] : 0));
                const fy = parseFloat(face.y || (face.box ? face.box[1] : 0));
                const fw = Math.max(20, parseFloat(face.width || (face.box ? face.box[2] : 100)));
                const fh = Math.max(20, parseFloat(face.height || (face.box ? face.box[3] : 100)));
                const imgW = face.img_width || imgEl.naturalWidth || 1000;
                const imgH = face.img_height || imgEl.naturalHeight || 1000;

                const box = document.createElement('div');
                box.className = 'lb-bounding-box';
                box.id = `bbox-${faceNum}`;
                box.style.cssText = `
                    position: absolute;
                    left: ${(fx / imgW) * 100}%;
                    top: ${(fy / imgH) * 100}%;
                    width: ${(fw / imgW) * 100}%;
                    height: ${(fh / imgH) * 100}%;
                    border: 2px solid #0a84ff;
                    box-shadow: 0 0 12px rgba(10,132,255,0.6);
                    border-radius: 6px;
                    pointer-events: auto;
                    cursor: pointer;
                    z-index: 100;
                    transition: all 0.15s ease;
                `;

                const badge = document.createElement('div');
                badge.style.cssText = 'position:absolute; top:-22px; left:0; background:#0a84ff; color:#fff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; white-space:nowrap;';
                badge.textContent = `${identity} (${confPct}%)`;
                box.appendChild(badge);

                container.appendChild(box);
            }
        });
    }).catch(e => {
        if (cardsContainer) cardsContainer.innerHTML = '<div style="color:#ff453a; font-size:12px; padding:15px; text-align:center;">Error al analizar caras.</div>';
    });
};

function highlightBox(faceNum) {
    document.querySelectorAll('.lb-bounding-box').forEach(b => {
        b.style.borderColor = '#0a84ff';
        b.style.boxShadow = '0 0 12px rgba(10,132,255,0.6)';
    });
    const target = document.getElementById(`bbox-${faceNum}`);
    if (target) {
        target.style.borderColor = '#30d158';
        target.style.boxShadow = '0 0 20px rgba(48,209,88,0.9)';
    }
}

window.toggleBoxes = function() {
    const boxes = document.querySelectorAll('.lb-bounding-box');
    boxes.forEach(b => {
        b.style.display = (b.style.display === 'none') ? 'block' : 'none';
    });
};

window.openManualCorrection = function(faceNum, currentNameEncoded) {
    const currentName = decodeURIComponent(currentNameEncoded);
    const newName = prompt(`Reasignar cara #${faceNum} (Actualmente: ${currentName}) a:`, currentName);
    if (!newName || newName.trim() === '' || newName === currentName) return;

    if (!window.currentFileObj || !window.currentFileObj.path) return;

    fetch('/api/correct', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            file_path: window.currentFileObj.path,
            target_identity: newName.trim(),
            target_category: 'Conocidos'
        })
    }).then(r => r.json()).then(data => {
        if (data.success) {
            if (typeof showToast === 'function') showToast(`✅ Cara #${faceNum} reasignada a "${newName.trim()}"`);
            window.triggerDeepScanLightbox();
            if (typeof loadGallery === 'function') loadGallery();
        } else {
            if (typeof showToast === 'function') showToast('Error al aplicar corrección', true);
        }
    }).catch(() => {
        if (typeof showToast === 'function') showToast('Error de red al corregir', true);
    });
};

window.enableManualSelection = function() {
    if (typeof showToast === 'function') showToast('✨ Haz clic en "Corregir" en el panel lateral para reasignar');
};
