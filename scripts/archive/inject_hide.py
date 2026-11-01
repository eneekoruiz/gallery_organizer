import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = "await loadIdentities();"

new_logic = """await loadIdentities();
                    
                    if (currentCat && currentIdent && idObj.identidad !== currentIdent) {
                        let stillHasFace = false;
                        for (let i = 0; i < currentFaces.length; i++) {
                            if (i !== faceNum - 1 && currentFaces[i].identity === currentIdent) {
                                stillHasFace = true; break;
                            }
                        }
                        if (!stillHasFace && galleryData && galleryData[currentCat] && galleryData[currentCat][currentIdent]) {
                            const pathStr = currentFileObj.path.replace(/\\\\/g, '/');
                            galleryData[currentCat][currentIdent] = galleryData[currentCat][currentIdent].filter(item => item.path.replace(/\\\\/g, '/') !== pathStr);
                            
                            const gridItem = document.getElementById('grid-container').children[currentItemIndex];
                            if (gridItem) {
                                gridItem.style.transition = 'all 0.3s ease';
                                gridItem.style.transform = 'scale(0)';
                                gridItem.style.opacity = '0';
                                setTimeout(() => gridItem.remove(), 300);
                            }
                            closeLightbox();
                            return; 
                        }
                    }"""

if old_logic in content:
    content = content.replace(old_logic, new_logic, 1) # Only replace the first occurrence which is in inlineCorrect
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated fast-hide logic")
else:
    print("Warning: old_logic not found")
