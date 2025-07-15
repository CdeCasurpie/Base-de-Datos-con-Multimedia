import os
import json
from HeiderDB.database.index_base import IndexBase
from HeiderDB.database.indexes.feature_extractor import create_feature_extractor
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

    def initialize(self, media_type="image", method="sift"):
        self.storage = MultimediaStorage(self.data_path)
        self.feature_extractor = create_feature_extractor(media_type, method)
        vector_index_file = os.path.join(
            os.path.dirname(self.data_path),
            f"{self.table_name}_{self.column_name}_vector.idx",
        )
        vector_metadata_file = os.path.join(
            os.path.dirname(self.data_path),
            f"{self.table_name}_{self.column_name}_vector_meta.json",
        )
        self.vector_index = VectorIndex(
            index_file=vector_index_file,
            metadata_file=vector_metadata_file,
            page_size=self.page_size,
        )
        if os.path.exists(self.metadata_file):
            self._load_metadata()
        else:
            self._save_metadata()

    def add(self, record, key):
        if self.vector_index is None:
            raise RuntimeError("Index not initialized. Call initialize() first.")
        src = record[self.column_name]
        print(f"DEBUG MultimediaIndex: Añadiendo vector para key={key}, src={src}")

        dst = self.storage.store(src)
        print(f"DEBUG MultimediaIndex: Archivo almacenado en: {dst}")

        vec = self.feature_extractor.extract(dst)
        print(
            f"DEBUG MultimediaIndex: Vector extraído, dimensión: {len(vec) if vec is not None else 'None'}"
        )

        if vec is not None:
            self.vector_index.add_vector(key, vec)
            print(f"DEBUG MultimediaIndex: Vector añadido al VectorIndex")

            # ¡IMPORTANTE! Guardar el VectorIndex después de añadir
            self.vector_index.save()
            print(f"DEBUG MultimediaIndex: VectorIndex guardado exitosamente")

            self.metadata[key] = dst
            self._save_metadata()
            print(f"DEBUG MultimediaIndex: Vector añadido exitosamente para key={key}")
        else:
            print(f"DEBUG MultimediaIndex: ERROR - Vector es None para key={key}")
            raise RuntimeError(f"No se pudo extraer vector para {src}")

    def remove(self, key):
        if self.vector_index is None:
            return False
        success = self.vector_index.remove_vector(key)
        if success and key in self.metadata:
            path = self.metadata.pop(key)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Warning: Could not remove file {path}: {e}")
            self._save_metadata()
        return success

    def rebuild(self):
        if self.vector_index is None or self.feature_extractor is None:
            return
        for key, path in self.metadata.items():
            if os.path.exists(path):
                vec = self.feature_extractor.extract(path)
                self.vector_index.add_vector(key, vec)

    def search(self, key):
        return self.metadata.get(key)

    def range_search(self, begin_key, end_key=None):
        keys = sorted(self.metadata.keys())
        if isinstance(begin_key, str):
            selected = [
                k
                for k in keys
                if str(k) >= str(begin_key)
                and (end_key is None or str(k) <= str(end_key))
            ]
        else:
            selected = [
                k for k in keys if k >= begin_key and (end_key is None or k <= end_key)
            ]
        return [(k, self.metadata[k]) for k in selected]

    def knn_search(self, query_file, k=5):
        """
        Busca los k vectores más similares al archivo de consulta.
        """
        print(
            f"DEBUG MultimediaIndex: knn_search llamado con query_file='{query_file}', k={k}"
        )

        if self.vector_index is None:
            print("DEBUG MultimediaIndex: vector_index es None")
            return []

        if self.feature_extractor is None:
            print("DEBUG MultimediaIndex: feature_extractor es None")
            return []

        # Verificar que el archivo existe
        if not os.path.exists(query_file):
            print(f"DEBUG MultimediaIndex: Archivo no encontrado: {query_file}")
            return []

        try:
            # Extraer características del archivo de consulta directamente
            print(f"DEBUG MultimediaIndex: Extrayendo características de {query_file}")
            qvec = self.feature_extractor.extract(query_file)

            if qvec is None:
                print("DEBUG MultimediaIndex: feature_extractor.extract() retornó None")
                return []

            print(
                f"DEBUG MultimediaIndex: Vector extraído correctamente, dimensión: {len(qvec) if hasattr(qvec, '__len__') else 'unknown'}"
            )

            # Verificar que hay vectores en el índice
            vector_count = (
                len(self.vector_index.vector_index)
                if hasattr(self.vector_index, "vector_index")
                else 0
            )
            print(f"DEBUG MultimediaIndex: Vectores en índice: {vector_count}")

            if vector_count == 0:
                print("DEBUG MultimediaIndex: No hay vectores en el índice")
                return []

            # Ejecutar búsqueda KNN
            print(f"DEBUG MultimediaIndex: Ejecutando search_knn en VectorIndex")
            results = self.vector_index.search_knn(qvec, k)
            print(f"DEBUG MultimediaIndex: search_knn retornó: {results}")
            print(
                f"DEBUG MultimediaIndex: Número de resultados: {len(results) if results else 0}"
            )

            return results

        except Exception as e:
            print(f"DEBUG MultimediaIndex: Error en knn_search: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_all(self):
        return list(self.metadata.items())

    def count(self):
        return len(self.metadata)

    def _save_metadata(self):
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def _load_metadata(self):
        try:
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)
                numeric_metadata = {}
                for k, v in self.metadata.items():
                    try:
                        numeric_key = int(k)
                        numeric_metadata[numeric_key] = v
                    except (ValueError, TypeError):
                        numeric_metadata[k] = v
                self.metadata = numeric_metadata
        except Exception as e:
            print(f"Error loading metadata: {e}")
            self.metadata = {}
