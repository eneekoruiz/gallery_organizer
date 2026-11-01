with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add img tag to html
old_html = '''                <div>
                    <h1 id="gallery-title">Todas las Fotos</h1>
                    <p id="gallery-subtitle">Selecciona un álbum en el panel izquierdo.</p>
                </div>'''
new_html = '''                <div style="display:flex; align-items:center; gap:20px;">
                    <img id="gallery-avatar" src="" style="width:70px; height:70px; border-radius:50%; object-fit:cover; border:2px solid #30d158; box-shadow:0 0 15px rgba(0,0,0,0.4); display:none;">
                    <div>
                        <h1 id="gallery-title" style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.5px;">Todas las Fotos</h1>
                        <p id="gallery-subtitle" style="margin:5px 0 0 0; color:#888; font-size:0.9rem;">Selecciona un álbum en el panel izquierdo.</p>
                    </div>
                </div>'''
if old_html in content:
    content = content.replace(old_html, new_html)
    print('Added avatar to HTML')

# Update JS to show it
old_js = '''            document.getElementById('gallery-title').textContent = `${currentCat} / ${currentIdent}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;'''
new_js = '''            document.getElementById('gallery-title').textContent = `${currentCat} / ${currentIdent}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;
            const avatar = document.getElementById('gallery-avatar');
            if (currentCat && currentIdent && currentCat === 'Personas Sin Nombre') {
                avatar.src = `/api/person_avatar?cat=${encodeURIComponent(currentCat)}&ident=${encodeURIComponent(currentIdent)}`;
                avatar.style.display = 'block';
                avatar.onerror = () => { avatar.style.display = 'none'; };
            } else if (avatar) {
                avatar.style.display = 'none';
            }'''
if old_js in content:
    content = content.replace(old_js, new_js)
    print('Added avatar to JS')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
