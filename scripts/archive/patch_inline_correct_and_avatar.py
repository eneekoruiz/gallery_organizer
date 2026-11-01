import sys

# 1. Patch inlineCorrect in index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_inline_correct = """        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {
    releaseMediaElement();
            if(!valStr) return;
            let idObj;
            if(valStr === 'NEW') {
                const newCat = prompt("Introduce la categoría:", "Conocidos");
                if(!newCat) return;
                const newIdent = prompt("Introduce el nombre completo:");
                if(!newIdent) return;
                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }
            
            let applyToDuplicates = false;
            try {
                const dupRes = await fetch('/api/duplicates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const dupData = await dupRes.json();
                if (dupData.duplicate) {
                    applyToDuplicates = true;
                }
            } catch (e) {
                console.error("Error checking duplicates", e);
            }

            const res = await fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    path: currentFileObj.path, 
                    new_categoria: idObj.categoria, 
                    new_identidad: idObj.identidad,
                    face: {x: faceX, y: faceY, width: faceW, height: faceH},
                    apply_to_duplicates: applyToDuplicates
                })
            });"""

new_inline_correct = """        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {
            releaseMediaElement();
            if(!valStr) return;
            const targetPath = (currentFileObj && currentFileObj.path) ? currentFileObj.path : decodeURIComponent(pathEncoded);
            if(!targetPath) return;

            let idObj;
            if(valStr === 'NEW') {
                const newCat = prompt("Introduce la categoría:", "Conocidos");
                if(!newCat) return;
                const newIdent = prompt("Introduce el nombre completo:");
                if(!newIdent) return;
                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }
            
            let applyToDuplicates = false;
            try {
                const dupRes = await fetch('/api/duplicates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: targetPath })
                });
                const dupData = await dupRes.json();
                if (dupData.duplicate) {
                    applyToDuplicates = true;
                }
            } catch (e) {
                console.error("Error checking duplicates", e);
            }

            const res = await fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    path: targetPath, 
                    new_categoria: idObj.categoria, 
                    new_identidad: idObj.identidad,
                    face: {x: faceX, y: faceY, width: faceW, height: faceH},
                    apply_to_duplicates: applyToDuplicates
                })
            });"""

if old_inline_correct in html:
    html = html.replace(old_inline_correct, new_inline_correct)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Patched inlineCorrect targetPath in index.html")
else:
    print("Could not match old_inline_correct in index.html")

# 2. Patch api_person_avatar in app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

old_avatar_find = """    target_dir = None
    if cat == 'Personas Sin Nombre':
        for base in [FOTOS_DIR, Path('Resultados')]:
            if base.exists():
                for sub in base.iterdir():
                    if sub.is_dir() and (sub / ident).exists():
                        target_dir = sub / ident
                        break
                if target_dir: break
    else:
        target_dir = FOTOS_DIR / cat / ident
        if not target_dir.exists():
            target_dir = Path('Resultados') / cat / ident"""

new_avatar_find = """    target_dir = Path('Resultados') / cat / ident
    if not target_dir.exists():
        target_dir = FOTOS_DIR / cat / ident"""

if old_avatar_find in app_code:
    app_code = app_code.replace(old_avatar_find, new_avatar_find)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("Patched target_dir lookup in api_person_avatar in app.py")
else:
    print("Could not match old_avatar_find in app.py")
