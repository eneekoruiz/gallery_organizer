import re

with open('gdrive_raw.html', 'r', encoding='utf-8') as f:
    html = f.read()

for match in re.finditer(r'AF_initDataCallback\(\{key:\s*\'ds:(\d+)\'[\s\S]*?data:([\s\S]*?)\}\);', html):
    ds_num = match.group(1)
    content = match.group(2)
    print(f"--- DS:{ds_num} (len: {len(content)}) ---")
    # Search for any quoted filename or path
    quotes = re.findall(r'"([^"\\]{4,100})"', content)
    interesting = [q for q in quotes if not q.startswith('http') and not q.startswith('//') and len(q) > 3]
    print(f"Found {len(interesting)} strings. Sample:")
    for s in interesting[:15]:
        print("  -", s)
