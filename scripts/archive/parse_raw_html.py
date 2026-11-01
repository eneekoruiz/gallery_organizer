import re

with open('gdrive_raw.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Pattern for Google Drive item arrays: [ "ID", "Filename.ext", ... ]
matches = re.findall(r'\["([a-zA-Z0-9_-]{25,50})",\["([^"]+)"', html)
print('Array matches:', len(matches))

ext_matches = set()
for item_id, name in matches:
    if any(name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi']):
        ext_matches.add((item_id, name))

print(f"Archivos encontrados con extensión multimedia: {len(ext_matches)}")
for item_id, name in list(ext_matches)[:20]:
    print(f" - {name} (ID: {item_id})")

# Check AF_initDataCallback payloads
callbacks = re.findall(r'AF_initDataCallback\(\{key:\s*\'ds:([^\']+)\',[\s\S]*?data:([\s\S]*?)\}\);', html)
print("Callbacks count:", len(callbacks))
for key, data_str in callbacks:
    print(f"Callback ds:{key} length: {len(data_str)}")
