import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    for line in f:
        if 'id="lightbox"' in line:
            print(line.strip())
