import os, shutil, json, urllib.request, urllib.parse
from abc import ABC, abstractmethod
from pathlib import Path

class BaseStorageAdapter(ABC):
    @abstractmethod
    def list_files(self, relative_path=""):
        pass

    @abstractmethod
    def read_file_bytes(self, relative_path):
        pass

    @abstractmethod
    def move_file(self, src_relative, dest_relative):
        pass

    @abstractmethod
    def delete_file(self, relative_path):
        pass

    @abstractmethod
    def file_exists(self, relative_path):
        pass

    @abstractmethod
    def get_thumbnail_url(self, relative_path):
        pass

class LocalStorageAdapter(BaseStorageAdapter):
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path):
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return self.root_dir / relative_path

    def list_files(self, relative_path=""):
        target = self._resolve_path(relative_path)
        file_list = []
        if not target.exists():
            return file_list
            
        for root, dirs, files in os.walk(str(target)):
            for f in files:
                fp = Path(root) / f
                rel = str(fp.relative_to(self.root_dir))
                file_list.append({
                    'path': str(fp),
                    'relative_path': rel,
                    'name': fp.name,
                    'size': fp.stat().st_size if fp.exists() else 0
                })
        return file_list

    def read_file_bytes(self, relative_path):
        fp = self._resolve_path(relative_path)
        with open(fp, 'rb') as f:
            return f.read()

    def move_file(self, src_relative, dest_relative):
        src_p = self._resolve_path(src_relative)
        dest_p = self._resolve_path(dest_relative)
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        if dest_p.exists() and dest_p != src_p:
            dest_p = dest_p.parent / f"moved_{src_p.name}"
        shutil.move(str(src_p), str(dest_p))
        return str(dest_p)

    def delete_file(self, relative_path):
        fp = self._resolve_path(relative_path)
        if fp.exists():
            fp.unlink()
            return True
        return False

    def file_exists(self, relative_path):
        return self._resolve_path(relative_path).exists()

    def get_thumbnail_url(self, relative_path):
        fp = self._resolve_path(relative_path)
        return f"/api/thumbnail?path={urllib.parse.quote(str(fp))}"

class GoogleDriveStorageAdapter(BaseStorageAdapter):
    def __init__(self, folder_id, api_key=None):
        self.folder_id = folder_id
        self.api_key = api_key or os.getenv("GOOGLE_DRIVE_API_KEY", "")

    def list_files(self, relative_path=""):
        url = f"https://www.googleapis.com/drive/v3/files?q=%27{self.folder_id}%27+in+parents+and+trashed=false&fields=files(id,name,mimeType,size,md5Checksum,webContentLink,thumbnailLink)&pageSize=1000"
        if self.api_key:
            url += f"&key={self.api_key}"

        file_list = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for item in data.get('files', []):
                    file_list.append({
                        'path': f"gdrive://{item['id']}",
                        'relative_path': item['name'],
                        'name': item['name'],
                        'size': int(item.get('size', 0)),
                        'gdrive_id': item['id'],
                        'thumbnail_link': item.get('thumbnailLink', '')
                    })
        except Exception as e:
            print("GoogleDriveStorageAdapter list_files error:", e)
        return file_list

    def read_file_bytes(self, relative_path):
        file_id = relative_path.replace("gdrive://", "")
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        if self.api_key:
            url += f"&key={self.api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def move_file(self, src_relative, dest_relative):
        # Drive file movement simulated via metadata tags / API calls
        print(f"[GDrive Adapter] Moving file {src_relative} -> {dest_relative}")
        return src_relative

    def delete_file(self, relative_path):
        print(f"[GDrive Adapter] Deleting file {relative_path}")
        return True

    def file_exists(self, relative_path):
        return True

    def get_thumbnail_url(self, relative_path):
        file_id = relative_path.replace("gdrive://", "")
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=s400"

def get_adapter(mode="local", config=None):
    config = config or {}
    if mode == "gdrive":
        folder_id = config.get("gdrive_folder_id", "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD")
        api_key = config.get("gdrive_api_key", os.getenv("GOOGLE_DRIVE_API_KEY", ""))
        return GoogleDriveStorageAdapter(folder_id, api_key)
    else:
        root_dir = config.get("local_path", r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
        return LocalStorageAdapter(root_dir)
