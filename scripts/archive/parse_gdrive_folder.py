import urllib.request, re, json

folder_id = '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD'
url = f'https://drive.google.com/drive/folders/{folder_id}'

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Search for filenames in JSON / JS structures
raw_matches = re.findall(r'\["([a-zA-Z0-9_-]{28,45})",\["([^"]+\.(?:jpg|jpeg|png|webp|mp4|mov|avi|heic|JPG|JPEG|PNG|MP4))"', html)

print(f"Encontrados {len(raw_matches)} archivos directamente en el HTML de Google Drive:")
unique_files = {}
for file_id, name in raw_matches:
    if name not in unique_files:
        unique_files[name] = file_id

for name, fid in list(unique_files.items())[:20]:
    print(f" - {name} (ID: {fid})")

with open('gdrive_folder_files.json', 'w', encoding='utf-8') as f:
    json.dump(unique_files, f, indent=2)

print(f"\nTotal archivos únicos parseados de Google Drive: {len(unique_files)}")
