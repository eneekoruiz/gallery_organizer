import os, hashlib, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

SRC_DIR = Path(r"D:\Galeria Eneko NO ABRIR")
DST_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
VALID_EXTS = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".webp", ".heic"}

def get_fast_fingerprint(filepath):
    try:
        st = os.stat(filepath)
        size = st.st_size
        if size == 0: return None
        hasher = hashlib.md5()
        hasher.update(f"{size}_{Path(filepath).name.lower()}".encode('utf-8'))
        return hasher.hexdigest()
    except:
        return None

print("=== DEEP FORENSIC DISK SIZE AUDIT ===", flush=True)

# 1. Map target files
dst_hashes = set()
dst_filenames = set()

for root, dirs, files in os.walk(str(DST_DIR)):
    for f in files:
        if Path(f).suffix.lower() in VALID_EXTS:
            fp = os.path.join(root, f)
            h = get_fast_fingerprint(fp)
            if h: dst_hashes.add(h)
            dst_filenames.add(f.lower())

# 2. Check source files
missing_files_info = []

for root, dirs, files in os.walk(str(SRC_DIR)):
    for f in files:
        if Path(f).suffix.lower() in VALID_EXTS:
            fp = os.path.join(root, f)
            h = get_fast_fingerprint(fp)
            fname_lower = f.lower()
            
            if not (h in dst_hashes or fname_lower in dst_filenames):
                try:
                    sz = os.path.getsize(fp)
                    missing_files_info.append((fp, f, sz, Path(f).suffix.lower()))
                except:
                    pass

missing_files_info.sort(key=lambda x: x[2], reverse=True)

total_missing_bytes = sum(x[2] for x in missing_files_info)
total_missing_gb = total_missing_bytes / (1024**3)

video_exts = {".mp4", ".mov", ".avi"}
video_missing = [x for x in missing_files_info if x[3] in video_exts]
photo_missing = [x for x in missing_files_info if x[3] not in video_exts]

video_missing_bytes = sum(x[2] for x in video_missing)
photo_missing_bytes = sum(x[2] for x in photo_missing)

print(f"\nTotal missing/purged files count: {len(missing_files_info)}")
print(f"Total size of purged files: {total_missing_gb:.2f} GB")
print(f" - Purged Videos: {len(video_missing)} files occupying {video_missing_bytes / (1024**3):.2f} GB")
print(f" - Purged Photos: {len(photo_missing)} files occupying {photo_missing_bytes / (1024**3):.2f} GB")

print("\n--- TOP 25 LARGEST PURGED DUPLICATE FILES ---")
for idx, (fp, fname, sz, ext) in enumerate(missing_files_info[:25]):
    mb_sz = sz / (1024*1024)
    gb_sz = sz / (1024**3)
    if gb_sz >= 1.0:
        print(f" {idx+1}. [{gb_sz:.2f} GB] {fname} ({fp})")
    else:
        print(f" {idx+1}. [{mb_sz:.1f} MB] {fname} ({fp})")
