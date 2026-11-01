import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(
    r"if \(item\.type === 'video'\) \{(.*?)\} else \{(.*?card\.appendChild\(img\);\s*)\}",
    re.DOTALL
)

new_block = '''const thumb = document.createElement('img');
                    thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
                    thumb.loading = 'lazy';
                    thumb.style.opacity = '0';
                    thumb.onload = () => thumb.style.opacity = '1';
                    thumb.style.transition = 'opacity 0.3s ease';
                    thumb.style.width = '100%';
                    thumb.style.height = '100%';
                    thumb.style.objectFit = 'cover';
                    card.appendChild(thumb);
                    
                    if (item.type === 'video') {
                        const playIcon = document.createElement('div');
                        playIcon.className = 'video-icon';
                        playIcon.innerHTML = '▶';
                        card.appendChild(playIcon);
                    }'''

content, count = pattern.subn(new_block, content)
print(f'Replaced {count} occurrences.')
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
