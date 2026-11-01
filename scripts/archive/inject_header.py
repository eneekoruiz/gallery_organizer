import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_header = """            document.getElementById('gallery-title').textContent = `${cat} / ${ident}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;"""

new_header = """            // Inject avatar and clean title
            document.getElementById('gallery-title').innerHTML = `
                <div style="display:flex; align-items:center; gap:15px; margin-bottom:5px; margin-top:-10px;">
                    <img src="/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}" 
                         style="width:80px; height:80px; object-fit:cover; border-radius:50%; border:3px solid #0a84ff; background:#333; display:none;" 
                         onerror="this.style.display='none'" onload="this.style.display='block'">
                    <div>
                        <div style="font-size: 1.4rem; margin:0;">${cat} <span style="color:#666;">&gt;</span> ${ident}</div>
                        <div id="gallery-subtitle" style="font-size: 0.9rem; font-weight:normal; color:#aaa; margin-top:2px;">${currentFolderItems.length} elementos</div>
                    </div>
                </div>
            `;
            // document.getElementById('gallery-subtitle').textContent is already set inside the innerHTML above
            """

if old_header in content:
    content = content.replace(old_header, new_header)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated header in renderGrid")
else:
    print("Warning: old_header not found")
