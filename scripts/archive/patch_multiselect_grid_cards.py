import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_click_block = """                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };"""

new_click_block = """                if (isMultiSelectMode) {
                    const chkContainer = document.createElement('div');
                    chkContainer.style.cssText = "position:absolute; top:10px; left:10px; z-index:10;";
                    const chk = document.createElement('input');
                    chk.type = 'checkbox';
                    chk.className = 'card-checkbox';
                    chk.checked = selectedFiles.has(item.path);
                    chk.style.cssText = "width:22px; height:22px; accent-color:#30d158; cursor:pointer;";
                    chkContainer.appendChild(chk);
                    card.appendChild(chkContainer);
                    
                    if (selectedFiles.has(item.path)) {
                        card.classList.add('selected-card');
                        card.style.border = '3px solid #30d158';
                        card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
                    }
                    
                    card.onclick = (e) => toggleFileSelection(item.path, card, e);
                } else {
                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };
                }"""

if old_click_block in content:
    content = content.replace(old_click_block, new_click_block, 1)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched card.onclick for multi-select in index.html")
else:
    print("Could not match old_click_block in index.html")
