import os
import shutil
import uuid
import json


class MultimediaStorage:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.mapping_file = os.path.join(self.storage_path, "mappings.json")
        self.id_mapping = {}
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        if os.path.exists(self.mapping_file):
            self.load_mappings()

    def save_file(self, file_path):
        file_id = self._generate_unique_id()
        ext = os.path.splitext(file_path)[1]
        filename = f"{file_id}{ext}"
        dst = os.path.join(self.storage_path, filename)
        shutil.copyfile(file_path, dst)
        self.id_mapping[file_id] = filename
        self.save_mappings()
        return file_id

    def get_file(self, file_id):
        filename = self.id_mapping.get(file_id)
        if not filename:
            return None
        return os.path.join(self.storage_path, filename)

    def delete_file(self, file_id):
        filename = self.id_mapping.pop(file_id, None)
        if not filename:
            return False
        path = os.path.join(self.storage_path, filename)
        try:
            os.remove(path)
        except:
            pass
        self.save_mappings()
        return True

    def get_all_files(self):
        return list(self.id_mapping.keys())

    def _generate_unique_id(self):
        return uuid.uuid4().hex

    def load_mappings(self):
        with open(self.mapping_file, "r") as f:
            self.id_mapping = json.load(f)

    def save_mappings(self):
        with open(self.mapping_file, "w") as f:
            json.dump(self.id_mapping, f)
