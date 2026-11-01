import os
import sys
import ctypes
from pathlib import Path

# Get physical disk size vs file size for iCloud Photos
photos_dir = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")

FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_PINNED = 0x00080000
FILE_ATTRIBUTE_UNPINNED = 0x00100000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000

print(f"Checking {photos_dir}...")
if not photos_dir.exists():
    print("Does not exist")
    sys.exit(0)

# Sample 20 files
files = list(photos_dir.glob("*"))[:20]
for f in files:
    if f.is_file():
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(f))
        
        # Get compressed / allocated size
        high = ctypes.c_ulong()
        low = ctypes.windll.kernel32.GetCompressedFileSizeW(str(f), ctypes.byref(high))
        allocated = (high.value << 32) + low
        
        is_reparse = bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
        is_recall = bool(attrs & (FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS))
        is_pinned = bool(attrs & FILE_ATTRIBUTE_PINNED)
        is_unpinned = bool(attrs & FILE_ATTRIBUTE_UNPINNED)
        
        logical_size = f.stat().st_size
        print(f"{f.name[:30]:30} | Logical: {logical_size/(1024*1024):.2f}MB | Allocated on disk: {allocated/(1024*1024):.2f}MB | Reparse: {is_reparse} | Recall: {is_recall} | Pinned: {is_pinned}")
