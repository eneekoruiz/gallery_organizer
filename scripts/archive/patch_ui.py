import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS
css_to_add = '''
/* MULTI-SELECT & FLOATING BAR */
.select-checkbox {
    position: absolute;
    top: 10px;
    left: 10px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 2px solid white;
    background: rgba(0,0,0,0.5);
    cursor: pointer;
    z-index: 10;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
}
.media-card:hover .select-checkbox, .select-checkbox.selected {
    opacity: 1;
}
.select-checkbox.selected {
    background: #30d158;
    border-color: #30d158;
}
.select-checkbox.selected::after {
    content: "✓";
    color: white;
    font-size: 14px;
    font-weight: bold;
}
.floating-action-bar {
    position: fixed;
    bottom: -100px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(20, 20, 22, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 100px;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 15px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    z-index: 99999;
    transition: bottom 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.floating-action-bar.visible {
    bottom: 30px;
}
.fab-count {
    color: white;
    font-weight: bold;
    font-size: 14px;
    background: #30d158;
    padding: 4px 10px;
    border-radius: 20px;
}
.fab-btn {
    background: transparent;
    border: none;
    color: white;
    font-size: 14px;
    cursor: pointer;
    padding: 6px 12px;
    border-radius: 20px;
    transition: background 0.2s;
}
.fab-btn:hover {
    background: rgba(255,255,255,0.1);
}
.fab-select {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
    border-radius: 8px;
    padding: 6px 12px;
    outline: none;
}
'''
if '/* MULTI-SELECT & FLOATING BAR */' not in content:
    content = content.replace('</style>', css_to_add + '\n</style>')

# 2. Add Floating Bar HTML
html_to_add = '''
    <div id="floating-action-bar" class="floating-action-bar">
        <span class="fab-count" id="fab-count">0 seleccionadas</span>
        
        <select id="fab-reassign-select" class="fab-select">
            <option value="">-- Reasignar a... --</option>
            <!-- Opciones se llenarán dinámicamente -->
        </select>
        
        <button class="fab-btn" onclick="applyBulkReassign()" style="color:#0a84ff; font-weight:bold;">Aplicar</button>
        <button class="fab-btn" onclick="applyBulkIgnore()" style="color:#ff453a;">Ignorar Todo</button>
        <div style="width:1px; height:20px; background:rgba(255,255,255,0.2);"></div>
        <button class="fab-btn" onclick="clearSelection()">Cancelar</button>
    </div>
'''
if 'id="floating-action-bar"' not in content:
    content = content.replace('</body>', html_to_add + '\n</body>')

# 3. Add JS logic
js_to_add = '''
        let selectedPaths = new Set();
        
        function toggleSelection(e, path) {
            e.stopPropagation(); // Evitar abrir el lightbox
            if (selectedPaths.has(path)) {
                selectedPaths.delete(path);
                e.target.classList.remove('selected');
            } else {
                selectedPaths.add(path);
                e.target.classList.add('selected');
            }
            updateFloatingBar();
        }
        
        function updateFloatingBar() {
            const bar = document.getElementById('floating-action-bar');
            const count = document.getElementById('fab-count');
            
            if (selectedPaths.size > 0) {
                count.innerText = `${selectedPaths.size} seleccionadas`;
                bar.classList.add('visible');
                
                // Poblar selectores si está vacío
                const select = document.getElementById('fab-reassign-select');
                if (select.options.length <= 1) {
                    populateFabSelect(select);
                }
            } else {
                bar.classList.remove('visible');
            }
        }
        
        function populateFabSelect(select) {
            select.innerHTML = '<option value="">-- Reasignar a... --</option>';
            const personas = new Set();
            if (identitiesList) {
                identitiesList.forEach(id => {
                    if (id.categoria === 'Conocidos' || id.categoria === 'Familiares') {
                        personas.add(id.identidad);
                    }
                });
            }
            const sorted = Array.from(personas).sort();
            sorted.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.innerText = p;
                select.appendChild(opt);
            });
        }
        
        function clearSelection() {
            selectedPaths.clear();
            document.querySelectorAll('.select-checkbox.selected').forEach(el => el.classList.remove('selected'));
            updateFloatingBar();
        }
        
        async function applyBulkReassign() {
            const select = document.getElementById('fab-reassign-select');
            const val = select.value;
            if (!val) {
                showToast('Selecciona una persona primero', true);
                return;
            }
            await performBulkAction(val);
        }
        
        async function applyBulkIgnore() {
            if(confirm(`¿Ignorar las ${selectedPaths.size} fotos seleccionadas?`)) {
                await performBulkAction('Ignorar');
            }
        }
        
        async function performBulkAction(identity) {
            const paths = Array.from(selectedPaths);
            const res = await fetch('/api/correct_bulk', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ paths, new_identity: identity })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Se han actualizado ${data.count} caras masivamente 🎉`);
                clearSelection();
                loadGallery(); // Recargar cuadrícula
            } else {
                showToast(`Error: ${data.error}`, true);
            }
        }
'''
if 'let selectedPaths = new Set();' not in content:
    content = content.replace('</script>', js_to_add + '\n</script>')

# 4. Inject checkbox into renderGrid
old_card_append = '''card.onclick = () => openLightbox(item);'''
new_card_append = '''card.onclick = () => openLightbox(item);
                    
                    const checkbox = document.createElement('div');
                    checkbox.className = 'select-checkbox';
                    if (selectedPaths && selectedPaths.has(item.path)) {
                        checkbox.classList.add('selected');
                    }
                    checkbox.onclick = (e) => toggleSelection(e, item.path);
                    card.appendChild(checkbox);'''
                    
if 'checkbox.className = \'select-checkbox\';' not in content:
    content = content.replace(old_card_append, new_card_append)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched multi-select!")
