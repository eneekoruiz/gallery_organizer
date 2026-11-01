import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_merge_redirect = """                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a '${targetCat} / ${targetName}'.`);
                closeMergeModal();
                await loadIdentities();
                await loadGallery();
                renderGrid(targetCat, targetName);"""

new_merge_no_redirect = """                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a '${targetCat} / ${targetName}'.`);
                closeMergeModal();
                await loadIdentities();
                await loadGallery();
                renderGrid(null, null);"""

if old_merge_redirect in content:
    content = content.replace(old_merge_redirect, new_merge_no_redirect)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Removed automatic redirection after merge in index.html")
else:
    print("Could not find old_merge_redirect in index.html")
