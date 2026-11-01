import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace HTML of the modal
old_html = """
            <div style="margin-bottom:15px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#30d158;">
                    🔗 Opción A: Fusionar con persona ya existente
                </label>
                <select id="merge-existing-select" style="width:100%; padding:10px; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem;">
                    <option value="">-- Selecciona persona --</option>
                </select>
            </div>
"""

new_html = """
            <div style="margin-bottom:15px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#30d158;">
                    🔗 Opción A: Fusionar con persona ya existente
                </label>
                <div id="merge-existing-select" style="width:100%; max-height:200px; overflow-y:auto; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem;">
                    <!-- Secciones plegables de categorías -->
                </div>
                <input type="hidden" id="merge-selected-value" value="">
            </div>
"""
if old_html in content:
    content = content.replace(old_html, new_html)

# Replace Javascript logic
old_js = """
        function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            
            const selectEl = document.getElementById('merge-existing-select');
            selectEl.innerHTML = '<option value="">-- Selecciona una persona existente --</option>';
            
            // Show all valid categories in groups
            let groupedIds = {};
            identitiesList.forEach(id => {
                if (id.categoria !== 'Personas Sin Nombre' && id.categoria !== 'Ignorar' && id.categoria !== '_Dudosos') {
                    if (!groupedIds[id.categoria]) groupedIds[id.categoria] = [];
                    groupedIds[id.categoria].push(id);
                }
            });
            
            Object.keys(groupedIds).sort().forEach(cat => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = cat;
                groupedIds[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    const opt = document.createElement('option');
                    // Store both identity and category in value
                    opt.value = JSON.stringify({cat: id.categoria, ident: id.identidad});
                    opt.textContent = id.identidad;
                    optgroup.appendChild(opt);
                });
                selectEl.appendChild(optgroup);
            });
            
            document.getElementById('merge-count-span').textContent = currentFolderItems.length;
            document.getElementById('merge-group-name').textContent = currentIdent;
            document.getElementById('merge-new-input').value = '';
            document.getElementById('modal-merge').style.display = 'flex';
        }
"""

new_js = """
        function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            
            const containerEl = document.getElementById('merge-existing-select');
            containerEl.innerHTML = '';
            document.getElementById('merge-selected-value').value = '';
            
            let groupedIds = {};
            identitiesList.forEach(id => {
                if (id.categoria !== 'Personas Sin Nombre' && id.categoria !== 'Ignorar' && id.categoria !== '_Dudosos') {
                    if (!groupedIds[id.categoria]) groupedIds[id.categoria] = [];
                    groupedIds[id.categoria].push(id);
                }
            });
            
            const btnStyle = "display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:white; cursor:pointer; border-radius:4px; font-size:13px; margin-bottom:2px; transition:background 0.2s;";
            const hoverScript = "onmouseover=\\"if(this.dataset.selected!=='true') this.style.background='#3a3a3c'\\" onmouseout=\\"if(this.dataset.selected!=='true') this.style.background='transparent'\\"";
            
            Object.keys(groupedIds).sort().forEach(cat => {
                const details = document.createElement('details');
                details.style.marginBottom = '4px';
                
                const summary = document.createElement('summary');
                summary.style.cssText = 'cursor:pointer; padding:6px 10px; font-weight:bold; color:#aaa; font-size:12px; background:#1c1c1e; margin-bottom:2px; position:sticky; top:0; z-index:10; border-bottom:1px solid #333;';
                summary.textContent = cat;
                details.appendChild(summary);
                
                const contentDiv = document.createElement('div');
                contentDiv.style.cssText = 'padding-left:8px; border-left:2px solid #333; margin-left:10px; margin-top:5px; margin-bottom:5px;';
                
                groupedIds[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    const btn = document.createElement('button');
                    btn.style.cssText = btnStyle;
                    btn.innerHTML = id.identidad;
                    btn.setAttribute('onmouseover', "if(this.dataset.selected!=='true') this.style.background='#3a3a3c'");
                    btn.setAttribute('onmouseout', "if(this.dataset.selected!=='true') this.style.background='transparent'");
                    
                    btn.onclick = () => {
                        // Reset all buttons
                        const allBtns = containerEl.querySelectorAll('button');
                        allBtns.forEach(b => {
                            b.dataset.selected = 'false';
                            b.style.background = 'transparent';
                            b.style.fontWeight = 'normal';
                        });
                        
                        // Select this button
                        btn.dataset.selected = 'true';
                        btn.style.background = '#30d158';
                        btn.style.color = 'black';
                        btn.style.fontWeight = 'bold';
                        
                        // Clear text input
                        document.getElementById('merge-new-input').value = '';
                        
                        // Set hidden value
                        document.getElementById('merge-selected-value').value = JSON.stringify({cat: id.categoria, ident: id.identidad});
                    };
                    
                    contentDiv.appendChild(btn);
                });
                
                details.appendChild(contentDiv);
                containerEl.appendChild(details);
            });
            
            // Text input should clear selection
            document.getElementById('merge-new-input').oninput = () => {
                const allBtns = containerEl.querySelectorAll('button');
                allBtns.forEach(b => {
                    b.dataset.selected = 'false';
                    b.style.background = 'transparent';
                    b.style.color = 'white';
                    b.style.fontWeight = 'normal';
                });
                document.getElementById('merge-selected-value').value = '';
            };
            
            document.getElementById('merge-count-span').textContent = currentFolderItems.length;
            document.getElementById('merge-group-name').textContent = currentIdent;
            document.getElementById('merge-new-input').value = '';
            document.getElementById('modal-merge').style.display = 'flex';
        }
"""
if old_js in content:
    content = content.replace(old_js, new_js)

# Fix submitMergeGroup
old_submit = """
        async function submitMergeGroup() {
            const selectVal = document.getElementById('merge-existing-select').value;
            const newVal = document.getElementById('merge-new-input').value.trim();
            
            if (!selectVal && !newVal) {
                alert("Debes elegir una opción.");
                return;
            }
"""

new_submit = """
        async function submitMergeGroup() {
            const selectVal = document.getElementById('merge-selected-value').value;
            const newVal = document.getElementById('merge-new-input').value.trim();
            
            if (!selectVal && !newVal) {
                alert("Debes elegir una opción.");
                return;
            }
"""
if old_submit in content:
    content = content.replace(old_submit, new_submit)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated modal-merge component")
