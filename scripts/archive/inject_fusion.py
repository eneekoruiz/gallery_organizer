import sys
import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update renameCurrentGroup to show all categories
old_rename_loop = """            identitiesList.forEach(id => {
                if (id.categoria === 'Conocidos') {
                    const opt = document.createElement('option');
                    opt.value = id.identidad;
                    opt.textContent = id.identidad;
                    selectEl.appendChild(opt);
                }
            });"""

new_rename_loop = """            // Show all valid categories in groups
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
            });"""

if old_rename_loop in content:
    content = content.replace(old_rename_loop, new_rename_loop)
    print("Updated renameCurrentGroup loop")
else:
    print("Warning: old_rename_loop not found")


# 2. Update submitMergeGroup to extract category and lock UI
old_submit_start = """        async function submitMergeGroup() {
            const existingName = document.getElementById('merge-existing-select').value;
            const newName = document.getElementById('merge-new-input').value.trim();
            
            const targetName = existingName || newName;
            if (!targetName) {
                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");
                return;
            }
            
            closeMergeModal();
            showToast(`⏳ Fusionando ${currentFolderItems.length} fotos con '${targetName}' y reentrenando IA...`);
            
            const res = await fetch('/api/rename_group', {"""

new_submit_start = """        async function submitMergeGroup() {
            const existingNameJSON = document.getElementById('merge-existing-select').value;
            const newName = document.getElementById('merge-new-input').value.trim();
            
            let targetName = "";
            let targetCat = "Conocidos";
            
            if (existingNameJSON) {
                const parsed = JSON.parse(existingNameJSON);
                targetName = parsed.ident;
                targetCat = parsed.cat;
            } else if (newName) {
                targetName = newName;
            } else {
                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");
                return;
            }
            
            // LOCK UI
            const btn = document.getElementById('modal-merge').querySelector('button[style*="background: #30d158"]');
            if(btn) { btn.disabled = true; btn.textContent = "⏳ Fusionando..."; }
            
            showToast(`⏳ Fusionando ${currentFolderItems.length} fotos con '${targetName}' y reentrenando IA...`);
            
            try {
            const res = await fetch('/api/rename_group', {"""

if old_submit_start in content:
    content = content.replace(old_submit_start, new_submit_start)
    print("Updated submitMergeGroup start")
else:
    print("Warning: old_submit_start not found")

# 3. Update submitMergeGroup payload and unlock UI
old_submit_end = """                    new_name: targetName,
                    new_cat: 'Conocidos'
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a 'Conocidos / ${targetName}' y se reentrenó el modelo IA.`);
                await loadIdentities();
                await loadGallery();
                renderGrid('Conocidos', targetName);
            } else {
                showToast(data.error || "No se pudo fusionar el grupo.", true);
            }
        }"""

new_submit_end = """                    new_name: targetName,
                    new_cat: targetCat
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a '${targetCat} / ${targetName}'.`);
                closeMergeModal();
                await loadIdentities();
                await loadGallery();
                renderGrid(targetCat, targetName);
            } else {
                showToast(data.error || "No se pudo fusionar el grupo.", true);
            }
            } catch (e) {
                showToast("Error de conexión durante la fusión.", true);
            } finally {
                if(btn) { btn.disabled = false; btn.innerHTML = "🚀 Aplicar Fusión / Guardar"; }
                closeMergeModal();
            }
        }"""

if old_submit_end in content:
    content = content.replace(old_submit_end, new_submit_end)
    print("Updated submitMergeGroup end")
else:
    print("Warning: old_submit_end not found")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
