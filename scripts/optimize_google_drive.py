import winreg

key_path = r"Software\Google\DriveFS"
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
except FileNotFoundError:
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

# Limit Google Drive local content cache to 8 GB (8 * 1024^3 bytes)
max_cache_bytes = 8 * 1024 * 1024 * 1024
# Require Google Drive to preserve at least 15 GB free space on C:
min_free_bytes = 15 * 1024 * 1024 * 1024

winreg.SetValueEx(key, "ContentCacheMaxBytes", 0, winreg.REG_QWORD, max_cache_bytes)
winreg.SetValueEx(key, "MinFreeSpaceBytes", 0, winreg.REG_QWORD, min_free_bytes)
winreg.CloseKey(key)

print(f"Google Drive configurado exitosamente:")
print(f"- ContentCacheMaxBytes: {max_cache_bytes / (1024**3):.1f} GB max cache")
print(f"- MinFreeSpaceBytes: {min_free_bytes / (1024**3):.1f} GB espacio libre reservado")
