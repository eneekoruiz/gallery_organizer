import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_render_tree = """        function renderTree() {
            const treeEl = document.getElementById('tree-container');
            treeEl.innerHTML = '';
            for (const cat in fullGallery) {
                const catEl = document.createElement('div');
                catEl.className = 'tree-folder category';
                catEl.textContent = `📁 ${cat}`;
                treeEl.appendChild(catEl);
                for (const ident in fullGallery[cat]) {
                    const identEl = document.createElement('div');
                    identEl.className = 'tree-folder identity';
                    const count = fullGallery[cat][ident].length;
                    identEl.innerHTML = `👤 ${ident} <span class="badge-count">${count}</span>`;
                    identEl.onclick = () => renderGrid(cat, ident);
                    treeEl.appendChild(identEl);
                }
            }
        }"""

new_render_tree = """        function renderTree() {
            const treeEl = document.getElementById('tree-container');
            treeEl.innerHTML = '';
            
            // Reordenar categorías para que Objetos quede abajo del todo
            const categories = Object.keys(fullGallery).sort((a, b) => {
                if (a.toLowerCase().includes('objeto')) return 1;
                if (b.toLowerCase().includes('objeto')) return -1;
                return a.localeCompare(b);
            });

            for (const cat of categories) {
                const catEl = document.createElement('div');
                catEl.className = 'tree-folder category';
                catEl.textContent = `📁 ${cat}`;
                treeEl.appendChild(catEl);
                
                const sortedIdents = Object.keys(fullGallery[cat]).sort((a, b) => a.localeCompare(b));
                for (const ident of sortedIdents) {
                    const identEl = document.createElement('div');
                    identEl.className = 'tree-folder identity';
                    const count = fullGallery[cat][ident].length;
                    identEl.innerHTML = `👤 ${ident} <span class="badge-count">${count}</span>`;
                    identEl.onclick = () => renderGrid(cat, ident);
                    treeEl.appendChild(identEl);
                }
            }
        }"""

if old_render_tree in content:
    content = content.replace(old_render_tree, new_render_tree)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched renderTree to position Objetos at the bottom of the sidebar")
else:
    print("Could not match old_render_tree in index.html")
