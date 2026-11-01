import urllib.request, re, json, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

folder_id = '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD'
url = f'https://drive.google.com/drive/folders/{folder_id}'

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Search for all strings matching filenames (IMG_, VID_, DSC_, Snapchat-, etc.) or extensions
filenames = set()
pattern = r'([a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp|mp4|mov|avi|heic|JPG|JPEG|PNG|MP4|MOV))'
for match in re.finditer(pattern, html):
    filenames.add(match.group(1))

print(f"✅ Encontrados {len(filenames)} archivos en el inventario del enlace de Google Drive:")
for fn in sorted(list(filenames))[:30]:
    print(f"  - {fn}")

with open('gdrive_inventario.json', 'w', encoding='utf-8') as f:
    json.dump(list(filenames), f, indent=2)

print(f"\nGuardado gdrive_inventario.json con {len(filenames)} elementos.")
