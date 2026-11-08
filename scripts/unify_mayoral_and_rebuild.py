import os
import shutil
import json
import urllib.request

print("=== UNIFYING MAYORAL FOLDERS ON DISK ===")

# 1. Resultados
r_base = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos'
r_dest = os.path.join(r_base, 'C. Aitziber Mayoral')
os.makedirs(r_dest, exist_ok=True)

for name in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
    r_src = os.path.join(r_base, name)
    if os.path.exists(r_src) and r_src != r_dest:
        print(f"Moving files from {r_src} to {r_dest}...")
        for f in os.listdir(r_src):
            s = os.path.join(r_src, f)
            d = os.path.join(r_dest, f)
            if not os.path.exists(d):
                shutil.move(s, d)
                print(f"  Moved: {f}")
            else:
                print(f"  Already exists at dest: {f}")
        os.rmdir(r_src)
        print(f"Removed directory: {r_src}")

# 2. Fotos (Dataset)
f_base = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos\Conocidos'
f_dest = os.path.join(f_base, 'C. Aitziber Mayoral')
os.makedirs(f_dest, exist_ok=True)

for name in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
    f_src = os.path.join(f_base, name)
    if os.path.exists(f_src) and f_src != f_dest:
        print(f"Moving files from {f_src} to {f_dest}...")
        for f in os.listdir(f_src):
            s = os.path.join(f_src, f)
            d = os.path.join(f_dest, f)
            if not os.path.exists(d):
                shutil.move(s, d)
                print(f"  Moved: {f}")
            else:
                print(f"  Already exists at dest: {f}")
        os.rmdir(f_src)
        print(f"Removed directory: {f_src}")

# 3. apple_db.json
print("\nUnifying apple_db.json...")
with open('apple_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

count = 0
for k, v in db.items():
    if v.get('identity') in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
        v['identity'] = 'C. Aitziber Mayoral'
        count += 1
    for fc in v.get('faces', []):
        if fc.get('identity') in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
            fc['identity'] = 'C. Aitziber Mayoral'
            count += 1
        if fc.get('suggested_identity') in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
            fc['suggested_identity'] = 'C. Aitziber Mayoral'
            count += 1
        if fc.get('label') in ['C Aitziber Mayoral', 'C  Aitziber Mayoral']:
            fc['label'] = 'C. Aitziber Mayoral'
            count += 1
    if 'identities' in v and isinstance(v['identities'], list):
        v['identities'] = ['C. Aitziber Mayoral' if id_n in ['C Aitziber Mayoral', 'C  Aitziber Mayoral'] else id_n for id_n in v['identities']]

with open('apple_db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)
print(f"apple_db.json updated ({count} entries unified).")

# 4. Remove gallery_cache.json
if os.path.exists('gallery_cache.json'):
    os.remove('gallery_cache.json')
    print("Deleted gallery_cache.json.")

# 5. Call API to force rebuild
print("\nRebuilding gallery cache via API...")
try:
    req = urllib.request.Request('http://127.0.0.1:5000/api/gallery?force=true')
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        conocidos = data.get('Conocidos', {})
        mayoral_keys = [k for k in conocidos.keys() if 'Mayoral' in k]
        print(f"Done! Mayoral keys in gallery: {mayoral_keys}")
        if 'C. Aitziber Mayoral' in conocidos:
            print(f"C. Aitziber Mayoral total items: {len(conocidos['C. Aitziber Mayoral'])}")
except Exception as e:
    print(f"Error calling API: {e}")

print("=== FINISHED ===")
