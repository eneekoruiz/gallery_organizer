import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<div id="stats-modal".*?</div>\s*</div>\s*</div>', content, re.DOTALL)
if match:
    with open('temp_stats.html', 'w', encoding='utf-8') as out:
        out.write(match.group(0))
    print("Extracted to temp_stats.html")
else:
    print("Not found")
