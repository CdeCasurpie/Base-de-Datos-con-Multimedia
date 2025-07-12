import os
import json
from HeiderDB.database.index_base import IndexBase
from HeiderDB.database.indexes.feature_extractor import FeatureExtractor
from HeiderDB.database.indexes.vector_index import VectorIndex
from HeiderDB.database.indexes.multimedia_storage import MultimediaStorage


class MultimediaIndex(IndexBase):
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.vector_index = None
        self.feature_extractor = None
        self.storage = None
        self.metadata_file = os.path.join(
            os.path.dirname(data_path), f"{table_name}_{column_name}_metadata.json"
        )
        self.metadata = {}

    def initialize(self, media_type="image"):
        self.storage = MultimediaStorage(self.data_path)
        self.feature_extractor = FeatureExtractor(media_type)
        vi_path = os.path.join(
            os.path.dirname(self.data_path),
            f"{self.table_name}_{self.column_name}_vector.idx",
        )
        self.vector_index = VectorIndex(
            self.table_name, self.column_name, vi_path, self.table_ref, self.page_size
        )
        if os.path.exists(self.metadata_file):
            self._load_metadata()
        else:
            self._save_metadata()

    def add(self, record, key):
        src = record[self.column_name]
        dst = self.storage.store(src)
        vec = self.feature_extractor.extract(dst)
        self.vector_index.insert(key, vec)
        self.metadata[key] = dst
        self._save_metadata()

    def remove(self, key):
        success = self.vector_index.delete(key)
        if success and key in self.metadata:
            path = self.metadata.pop(key)
            try:
                os.remove(path)
            except:
                pass
            self._save_metadata()
        return success

    def rebuild(self):
        self.initialize()
        for key, path in self.metadata.items():
            vec = self.feature_extractor.extract(path)
            self.vector_index.insert(key, vec)

    def search(self, key):
        return self.metadata.get(key)

    def range_search(self, begin_key, end_key=None):
        keys = sorted(self.metadata)
        selected = [
            k for k in keys if k >= begin_key and (end_key is None or k <= end_key)
        ]
        return [(k, self.metadata[k]) for k in selected]

    def knn_search(self, query_file, k=5):
        query_path = self.storage.store(query_file)
        qvec = self.feature_extractor.extract(query_path)
        return self.vector_index.search(qvec, k)

    def get_all(self):
        return list(self.metadata.items())

    def count(self):
        return len(self.metadata)

    def _save_metadata(self):
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f)

    def _load_metadata(self):
        with open(self.metadata_file, "r") as f:
            self.metadata = json.load(f)
