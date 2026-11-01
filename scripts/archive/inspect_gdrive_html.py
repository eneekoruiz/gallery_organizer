import urllib.request, re, json

folder_id = '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD'
url = f'https://drive.google.com/drive/folders/{folder_id}'

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

# Save HTML to debug file
with open('gdrive_raw.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved gdrive_raw.html (size:", len(html), "bytes)")
