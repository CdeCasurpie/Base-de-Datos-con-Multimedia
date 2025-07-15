import os
import shutil
import hashlib
from pathlib import Path


class MultimediaStorage:
    def __init__(self, data_path):
        self.data_path = data_path
        data_dir = os.path.dirname(data_path)
        self.storage_dir = os.path.join(data_dir, "multimedia")
        os.makedirs(self.storage_dir, exist_ok=True)
        print(f"MultimediaStorage inicializado en: {self.storage_dir}")

    def store(self, source_path):
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Archivo no encontrado: {source_path}")
        file_hash = self._calculate_file_hash(source_path)
        file_extension = Path(source_path).suffix
        stored_filename = f"{file_hash}{file_extension}"
        stored_path = os.path.join(self.storage_dir, stored_filename)
        if not os.path.exists(stored_path):
            shutil.copy2(source_path, stored_path)
            print(f"Archivo copiado: {source_path} -> {stored_path}")
        else:
            print(f"Archivo ya existe: {stored_path}")
        return stored_path

    def remove(self, stored_path):
        try:
            if os.path.exists(stored_path):
                os.remove(stored_path)
                print(f"Archivo eliminado: {stored_path}")
                return True
            return False
        except Exception as e:
            print(f"Error eliminando archivo {stored_path}: {e}")
            return False

    def exists(self, stored_path):
        return os.path.exists(stored_path)

    def get_storage_stats(self):
        if not os.path.exists(self.storage_dir):
            return {"files": 0, "total_size": 0}
        files = os.listdir(self.storage_dir)
        total_size = 0
        for file in files:
            file_path = os.path.join(self.storage_dir, file)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
        return {
            "files": len(files),
            "total_size": total_size,
            "storage_dir": self.storage_dir,
        }

    def _calculate_file_hash(self, file_path):
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            import time

            fallback = f"{os.path.basename(file_path)}_{int(time.time())}"
            return hashlib.md5(fallback.encode()).hexdigest()
