import ctypes
from ctypes import wintypes
from pathlib import Path

# Load cfapi.dll
cfapi = ctypes.WinDLL("cldapi.dll")

# Function signature:
# HRESULT CfDehydratePlaceholder(
#   HANDLE          FileHandle,
#   LARGE_INTEGER   StartingOffset,
#   LARGE_INTEGER   Length,
#   CF_DEHYDRATE_FLAGS DehydrateFlags,
#   LPOVERLAPPED    Overlapped
# );

# Let's check kernel32 CreateFileW
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_WRITE_ATTRIBUTES = 0x0100
FILE_READ_ATTRIBUTES = 0x0080
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4

photos_dir = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")
sample_file = None
high = ctypes.c_ulong()
for f in photos_dir.glob("*"):
    if f.is_file():
        low = ctypes.windll.kernel32.GetCompressedFileSizeW(str(f), ctypes.byref(high))
        alloc = (high.value << 32) + low
        if alloc > 5 * 1024 * 1024: # > 5 MB
            sample_file = f
            break

print("Testing sample file:", sample_file.name if sample_file else "None")
if sample_file:
    low = ctypes.windll.kernel32.GetCompressedFileSizeW(str(sample_file), ctypes.byref(high))
    print(f"Before alloc: {((high.value << 32) + low)/(1024*1024):.2f} MB")
    
    # Try CfDehydratePlaceholder
    # CF_DEHYDRATE_FLAG_NONE = 0
    handle = ctypes.windll.kernel32.CreateFileW(
        str(sample_file),
        FILE_WRITE_ATTRIBUTES | FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        0x02000000, # FILE_FLAG_BACKUP_SEMANTICS
        None
    )
    if handle != -1 and handle != 0:
        hr = cfapi.CfDehydratePlaceholder(
            handle,
            ctypes.c_longlong(0),
            ctypes.c_longlong(-1), # entire file
            0, # CF_DEHYDRATE_FLAG_NONE
            None
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        print(f"CfDehydratePlaceholder HRESULT: {hr} (hex: {hex(hr & 0xFFFFFFFF)})")
    else:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"CreateFileW failed with error: {err}")

    low = ctypes.windll.kernel32.GetCompressedFileSizeW(str(sample_file), ctypes.byref(high))
    print(f"After alloc: {((high.value << 32) + low)/(1024*1024):.2f} MB")
