import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_avatar_tag = """                    <img src="/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}" 
                         style="width:80px; height:80px; object-fit:cover; border-radius:50%; border:3px solid #0a84ff; background:#333; display:none;" 
                         onerror="this.style.display='none'" onload="this.style.display='block'">"""

new_avatar_tag = """                    <img src="/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}" 
                         style="width:75px; height:75px; object-fit:cover; border-radius:50%; display:none;" 
                         onerror="this.style.display='none';" onload="this.style.display='block'; this.style.border='3px solid #30d158'; this.style.boxShadow='0 0 12px rgba(48,209,88,0.4)';">"""

if old_avatar_tag in content:
    content = content.replace(old_avatar_tag, new_avatar_tag)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched avatar image element to hide empty border")
else:
    print("Could not find old_avatar_tag")
