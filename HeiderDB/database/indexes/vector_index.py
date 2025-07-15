import os
import json
import numpy as np
from sklearn.cluster import KMeans
import pickle
import math
import warnings
from collections import OrderedDict

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.cluster")


class VectorIndex:
    """
    Estructura de datos para vectores de características con paginación.
    Maneja búsquedas de similitud y clustering usando almacenamiento secundario.
    """

    def __init__(self, index_file, metadata_file, page_size=100, cache_size=10):
        self.index_file = index_file
        self.metadata_file = metadata_file
        self.page_size = page_size
        self.cache_size = cache_size

        self.vector_index = {}  # {vector_id: (page_id, position_in_page)}
        self.page_directory = (
            {}
        )  # {page_id: {'file_path': str, 'vector_count': int, 'free_positions': list}}

        self.page_cache = OrderedDict()  # {page_id: {'vectors': dict, 'dirty': bool}}

        self.clusters = {}
        self.cluster_centers = None
        self.vector_to_cluster = {}

        self.next_page_id = 0
        self.total_vectors = 0

        self.pages_dir = os.path.join(os.path.dirname(self.index_file), "pages")
        self._vectors_cache = None

        self.load()

    def _create_page_file_path(self, page_id):
        """Crea la ruta del archivo para una página específica"""
        return os.path.join(self.pages_dir, f"page_{page_id}.pkl")

    def _load_page(self, page_id):
        """Carga una página desde disco al cache"""
        if page_id in self.page_cache:
            self.page_cache.move_to_end(page_id)
            return self.page_cache[page_id]

        if len(self.page_cache) >= self.cache_size:
            self._evict_oldest_page()

        page_file = self._create_page_file_path(page_id)
        if os.path.exists(page_file):
            try:
                with open(page_file, "rb") as f:
                    vectors_data = pickle.load(f)
                page_data = {"vectors": vectors_data, "dirty": False}
            except Exception as e:
                print(f"Error cargando página {page_id}: {e}")
                page_data = {"vectors": {}, "dirty": False}
        else:
            page_data = {"vectors": {}, "dirty": False}

        self.page_cache[page_id] = page_data
        return page_data

    def _save_page(self, page_id):
        """Guarda una página desde cache a disco"""
        if page_id not in self.page_cache:
            return

        page_data = self.page_cache[page_id]
        if not page_data["dirty"]:
            return

        os.makedirs(self.pages_dir, exist_ok=True)
        page_file = self._create_page_file_path(page_id)

        try:
            with open(page_file, "wb") as f:
                pickle.dump(page_data["vectors"], f)
            page_data["dirty"] = False
        except Exception as e:
            print(f"Error guardando página {page_id}: {e}")

    def _evict_oldest_page(self):
        """Remueve la página más antigua del cache (LRU)"""
        if not self.page_cache:
            return

        oldest_page_id, page_data = self.page_cache.popitem(last=False)
        if page_data["dirty"]:
            self._save_page_data(oldest_page_id, page_data)

    def _save_page_data(self, page_id, page_data):
        """Guarda datos de página específicos a disco"""
        os.makedirs(self.pages_dir, exist_ok=True)
        page_file = self._create_page_file_path(page_id)

        try:
            with open(page_file, "wb") as f:
                pickle.dump(page_data["vectors"], f)
        except Exception as e:
            print(f"Error guardando página {page_id}: {e}")

    def _flush_all_pages(self):
        """Guarda todas las páginas dirty a disco"""
        for page_id in list(self.page_cache.keys()):
            self._save_page(page_id)

    def _create_new_page(self):
        """Crea una nueva página"""
        page_id = self.next_page_id
        self.next_page_id += 1

        self.page_directory[page_id] = {
            "file_path": self._create_page_file_path(page_id),
            "vector_count": 0,
            "free_positions": list(range(self.page_size)),
        }

        return page_id

    def _find_available_page(self):
        """Encuentra una página con espacio disponible o crea una nueva"""
        for page_id, info in self.page_directory.items():
            if info["free_positions"]:
                return page_id

        return self._create_new_page()

    def add_vector(self, id, vector):
        """
        Añade un vector al índice usando paginación

        Params:
            id: Identificador único del vector
            vector: Vector de características (numpy array o lista)
        """
        print(
            f"DEBUG VectorIndex.add_vector: Añadiendo vector_id={id}, vector shape={vector.shape if hasattr(vector, 'shape') else len(vector)}"
        )

        if isinstance(vector, list):
            vector = np.array(vector)

        self._invalidate_vectors_cache()

        if id in self.vector_index:
            print(
                f"DEBUG VectorIndex.add_vector: Actualizando vector existente id={id}"
            )
            page_id, position = self.vector_index[id]
            page_data = self._load_page(page_id)
            page_data["vectors"][position] = vector
            page_data["dirty"] = True
        else:
            print(f"DEBUG VectorIndex.add_vector: Añadiendo nuevo vector id={id}")
            page_id = self._find_available_page()
            print(
                f"DEBUG VectorIndex.add_vector: _find_available_page() retornó page_id={page_id}"
            )

            page_data = self._load_page(page_id)
            print(
                f"DEBUG VectorIndex.add_vector: _load_page({page_id}) retornó page_data con keys: {list(page_data.keys())}"
            )

            page_info = self.page_directory[page_id]
            print(
                f"DEBUG VectorIndex.add_vector: page_info free_positions: {page_info['free_positions']}"
            )

            if not page_info["free_positions"]:
                print(
                    f"DEBUG VectorIndex.add_vector: No hay posiciones libres, creando nueva página"
                )
                page_id = self._create_new_page()
                page_data = self._load_page(page_id)
                page_info = self.page_directory[page_id]

            position = page_info["free_positions"].pop(0)
            print(
                f"DEBUG VectorIndex.add_vector: Asignando position={position} en page_id={page_id}"
            )

            page_data["vectors"][position] = vector
            page_data["dirty"] = True
            print(
                f"DEBUG VectorIndex.add_vector: Vector guardado en page_data['vectors'][{position}]"
            )
            print(
                f"DEBUG VectorIndex.add_vector: page_data['vectors'] ahora tiene keys: {list(page_data['vectors'].keys())}"
            )

            self.vector_index[id] = (page_id, position)
            page_info["vector_count"] += 1
            self.total_vectors += 1

            print(
                f"DEBUG VectorIndex.add_vector: vector_index[{id}] = ({page_id}, {position})"
            )
            print(
                f"DEBUG VectorIndex.add_vector: total_vectors ahora es: {self.total_vectors}"
            )

        if self.cluster_centers is not None:
            cluster_id = self._assign_to_nearest_cluster(vector)
            self.vector_to_cluster[id] = cluster_id
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            if id not in self.clusters[cluster_id]:
                self.clusters[cluster_id].append(id)

        print(f"DEBUG VectorIndex.add_vector: Finalizando add_vector para id={id}")

        self.save_metadata()

    def remove_vector(self, id):
        """
        Remueve un vector del índice usando paginación

        Params:
            id: Identificador del vector

        Returns:
            bool: True si se removió exitosamente, False si no existía
        """
        if id not in self.vector_index:
            return False

        self._invalidate_vectors_cache()

        page_id, position = self.vector_index[id]
        page_data = self._load_page(page_id)

        if position in page_data["vectors"]:
            del page_data["vectors"][position]
            page_data["dirty"] = True

        del self.vector_index[id]
        page_info = self.page_directory[page_id]
        page_info["free_positions"].append(position)
        page_info["free_positions"].sort()
        page_info["vector_count"] -= 1
        self.total_vectors -= 1

        if id in self.vector_to_cluster:
            cluster_id = self.vector_to_cluster[id]
            if cluster_id in self.clusters and id in self.clusters[cluster_id]:
                self.clusters[cluster_id].remove(id)
            del self.vector_to_cluster[id]

        self.save_metadata()
        return True

    def get_vector(self, id):
        """
        Obtiene un vector por su ID usando paginación

        Params:
            id: Identificador del vector

        Returns:
            numpy.ndarray: Vector o None si no existe
        """
        print(f"DEBUG VectorIndex.get_vector: Buscando vector_id={id}")
        print(
            f"DEBUG VectorIndex.get_vector: vector_index keys={list(self.vector_index.keys())}"
        )

        if id not in self.vector_index:
            print(f"DEBUG VectorIndex.get_vector: ERROR - {id} no está en vector_index")
            return None

        page_id, position = self.vector_index[id]
        print(
            f"DEBUG VectorIndex.get_vector: Found page_id={page_id}, position={position}"
        )

        page_data = self._load_page(page_id)
        print(
            f"DEBUG VectorIndex.get_vector: _load_page({page_id}) retornó: {page_data is not None}"
        )

        if page_data is None:
            print(
                f"DEBUG VectorIndex.get_vector: ERROR - page_data es None para page_id={page_id}"
            )
            return None

        result = page_data["vectors"].get(position)
        print(
            f"DEBUG VectorIndex.get_vector: page_data['vectors'].get({position}) retornó: {result is not None}"
        )
        print(
            f"DEBUG VectorIndex.get_vector: page_data['vectors'] keys: {list(page_data['vectors'].keys())}"
        )

        return result

    @property
    def vectors(self):
        """
        Propiedad para compatibilidad con código existente.
        Devuelve un diccionario de todos los vectores (carga lazy).
        ADVERTENCIA: Esta propiedad puede usar mucha memoria para datasets grandes.
        """

        if self._vectors_cache is None:
            self._vectors_cache = {}
            for vector_id, (page_id, position) in self.vector_index.items():
                vector = self.get_vector(vector_id)
                if vector is not None:
                    self._vectors_cache[vector_id] = vector
        return self._vectors_cache

    def _invalidate_vectors_cache(self):
        """Invalida el cache de vectores"""
        self._vectors_cache = None

    def search_knn(self, query_vector, k=5):
        """
        Búsqueda KNN sin usar clustering (fuerza bruta) con paginación

        Params:
            query_vector: Vector de consulta
            k: Número de vecinos más cercanos

        Returns:
            list: Lista de tuplas (id, distancia) ordenadas por distancia
        """
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)

        print(f"DEBUG VectorIndex: search_knn iniciado con k={k}")
        print(
            f"DEBUG VectorIndex: vector_index tiene {len(self.vector_index)} vectores"
        )
        print(f"DEBUG VectorIndex: vector_index keys: {list(self.vector_index.keys())}")

        if not self.vector_index:
            print("DEBUG VectorIndex: vector_index está vacío, retornando []")
            return []

        distances = []

        for vector_id in self.vector_index.keys():
            print(f"DEBUG VectorIndex: Procesando vector_id={vector_id}")
            vector = self.get_vector(vector_id)
            print(
                f"DEBUG VectorIndex: get_vector({vector_id}) retornó: {vector is not None}"
            )
            if vector is not None:
                distance = self.compute_distance(query_vector, vector)
                print(f"DEBUG VectorIndex: Distancia para {vector_id}: {distance}")
                distances.append((vector_id, distance))
            else:
                print(
                    f"DEBUG VectorIndex: ERROR - get_vector({vector_id}) retornó None"
                )

        print(f"DEBUG VectorIndex: Total distancias calculadas: {len(distances)}")
        distances.sort(key=lambda x: x[1])
        result = distances[:k]
        print(f"DEBUG VectorIndex: Retornando {len(result)} resultados")
        return result

    def search_knn_with_index(self, query_vector, k=5):
        """
        Búsqueda KNN usando clustering para acelerar la búsqueda con paginación

        Params:
            query_vector: Vector de consulta
            k: Número de vecinos más cercanos

        Returns:
            list: Lista de tuplas (id, distancia) ordenadas por distancia
        """
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)

        if not self.vector_index or self.cluster_centers is None:
            return self.search_knn(query_vector, k)

        cluster_distances = self._get_ordered_clusters(query_vector)

        candidates = self._search_in_clusters(query_vector, cluster_distances, k)

        if len(candidates) < k:
            return self.search_knn(query_vector, k)

        candidates.sort(key=lambda x: x[1])
        return candidates[:k]

    def _get_ordered_clusters(self, query_vector):
        """Obtiene clusters ordenados por distancia al vector de consulta"""
        cluster_distances = []
        for i, center in enumerate(self.cluster_centers):
            distance = self.compute_distance(query_vector, center)
            cluster_distances.append((i, distance))

        cluster_distances.sort(key=lambda x: x[1])
        return cluster_distances

    def _search_in_clusters(self, query_vector, cluster_distances, k):
        """Busca candidatos en los clusters más cercanos"""
        candidates = []
        searched_clusters = 0
        max_clusters_to_search = min(3, len(self.cluster_centers))

        for cluster_id, _ in cluster_distances:
            if searched_clusters >= max_clusters_to_search and len(candidates) >= k:
                break

            if cluster_id in self.clusters:
                cluster_candidates = self._get_cluster_candidates(
                    query_vector, cluster_id
                )
                candidates.extend(cluster_candidates)

            searched_clusters += 1

        return candidates

    def _get_cluster_candidates(self, query_vector, cluster_id):
        """Obtiene candidatos de un cluster específico usando paginación"""
        candidates = []
        for vector_id in self.clusters[cluster_id]:
            vector = self.get_vector(vector_id)
            if vector is not None:
                distance = self.compute_distance(query_vector, vector)
                candidates.append((vector_id, distance))
        return candidates

    def build_kmeans_clusters(self, num_clusters=10):
        """
        Construye clusters usando K-means con paginación

        Params:
            num_clusters: Número de clusters a crear
        """
        if self.total_vectors < num_clusters:
            num_clusters = max(1, self.total_vectors)

        if self.total_vectors == 0:
            return

        vector_ids = list(self.vector_index.keys())
        vector_data = []

        for vector_id in vector_ids:
            vector = self.get_vector(vector_id)
            if vector is not None:
                vector_data.append(vector)

        if not vector_data:
            return

        vector_data = np.array(vector_data)

        unique_vectors = np.unique(vector_data, axis=0)
        if len(unique_vectors) < num_clusters:
            print(
                f"Advertencia: Los vectores tienen poca variación. Reduciendo clusters a {len(unique_vectors)}"
            )
            num_clusters = max(1, len(unique_vectors))

        try:
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(vector_data)

            self.cluster_centers = kmeans.cluster_centers_

            self.clusters = {}
            self.vector_to_cluster = {}

            for i, vector_id in enumerate(vector_ids):
                if i < len(cluster_labels):
                    cluster_id = int(cluster_labels[i])
                    self.vector_to_cluster[vector_id] = cluster_id

                    if cluster_id not in self.clusters:
                        self.clusters[cluster_id] = []
                    self.clusters[cluster_id].append(vector_id)

            self.save_metadata()

        except Exception as e:
            print(f"Error durante clustering: {e}")
            self.clusters = {0: vector_ids}
            self.vector_to_cluster = dict.fromkeys(vector_ids, 0)
            if len(vector_data) > 0:
                self.cluster_centers = np.array([np.mean(vector_data, axis=0)])
            else:
                self.cluster_centers = None
            self.save_metadata()

    def _assign_to_nearest_cluster(self, vector):
        """
        Asigna un vector al cluster más cercano

        Params:
            vector: Vector a asignar

        Returns:
            int: ID del cluster más cercano
        """
        if self.cluster_centers is None:
            return 0

        min_distance = float("inf")
        nearest_cluster = 0

        for i, center in enumerate(self.cluster_centers):
            distance = self.compute_distance(vector, center)
            if distance < min_distance:
                min_distance = distance
                nearest_cluster = i

        return nearest_cluster

    def save(self):
        """
        Guarda el índice completo (páginas + metadata)
        """
        self._flush_all_pages()
        self.save_metadata()

    def save_metadata(self):
        """
        Guarda solo los metadatos del índice
        """
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)

            metadata = {
                "vector_index": {str(k): list(v) for k, v in self.vector_index.items()},
                "page_directory": {str(k): v for k, v in self.page_directory.items()},
                "clusters": {str(k): v for k, v in self.clusters.items()},
                "vector_to_cluster": {
                    str(k): int(v) if isinstance(v, np.integer) else v
                    for k, v in self.vector_to_cluster.items()
                },
                "cluster_centers": (
                    self.cluster_centers.tolist()
                    if self.cluster_centers is not None
                    else None
                ),
                "next_page_id": self.next_page_id,
                "total_vectors": self.total_vectors,
                "page_size": self.page_size,
                "cache_size": self.cache_size,
            }

            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"Error al guardar metadatos del índice de vectores: {e}")

    def load(self):
        """
        Carga el índice desde archivos (solo metadata, páginas se cargan on-demand)
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, "r") as f:
                    metadata = json.load(f)

                vector_index_raw = metadata.get("vector_index", {})
                self.vector_index = {}
                for k, v in vector_index_raw.items():
                    try:
                        key = int(k) if k.isdigit() else k
                    except (ValueError, TypeError):
                        key = k
                    self.vector_index[key] = tuple(v)

                page_directory_raw = metadata.get("page_directory", {})
                self.page_directory = {}
                for k, v in page_directory_raw.items():
                    try:
                        key = int(k)
                    except (ValueError, TypeError):
                        key = k
                    self.page_directory[key] = v

                self.clusters = {
                    int(k): v for k, v in metadata.get("clusters", {}).items()
                }

                vector_to_cluster_raw = metadata.get("vector_to_cluster", {})
                self.vector_to_cluster = {}
                for k, v in vector_to_cluster_raw.items():
                    try:
                        key = int(k) if k.isdigit() else k
                    except (ValueError, TypeError):
                        key = k
                    self.vector_to_cluster[key] = (
                        int(v)
                        if isinstance(v, (int, float, str)) and str(v).isdigit()
                        else v
                    )

                cluster_centers_data = metadata.get("cluster_centers")
                if cluster_centers_data:
                    self.cluster_centers = np.array(cluster_centers_data)
                else:
                    self.cluster_centers = None

                self.next_page_id = metadata.get("next_page_id", 0)
                self.total_vectors = metadata.get("total_vectors", 0)
                self.page_size = metadata.get("page_size", self.page_size)
                self.cache_size = metadata.get("cache_size", self.cache_size)

        except Exception as e:
            print(f"Error al cargar metadatos del índice de vectores: {e}")
            self.vector_index = {}
            self.page_directory = {}
            self.clusters = {}
            self.vector_to_cluster = {}
            self.cluster_centers = None
            self.next_page_id = 0
            self.total_vectors = 0

    def compute_distance(self, vec1, vec2):
        """
        Calcula la distancia euclidiana entre dos vectores

        Params:
            vec1: Primer vector
            vec2: Segundo vector

        Returns:
            float: Distancia euclidiana
        """
        return np.linalg.norm(vec1 - vec2)

    def get_vector_count(self):
        """
        Retorna el número de vectores en el índice

        Returns:
            int: Número de vectores
        """
        return self.total_vectors

    def get_cluster_count(self):
        """
        Retorna el número de clusters

        Returns:
            int: Número de clusters
        """
        return len(self.clusters)

    def get_page_count(self):
        """
        Retorna el número de páginas en el índice

        Returns:
            int: Número de páginas
        """
        return len(self.page_directory)

    def get_cache_info(self):
        """
        Retorna información sobre el cache de páginas

        Returns:
            dict: Información del cache
        """
        return {
            "pages_in_cache": len(self.page_cache),
            "cache_size_limit": self.cache_size,
            "dirty_pages": sum(
                1 for page_data in self.page_cache.values() if page_data["dirty"]
            ),
        }

    def clear(self):
        """
        Limpia todos los datos del índice y elimina archivos de páginas
        """
        self.vector_index = {}
        self.page_directory = {}
        self.clusters = {}
        self.vector_to_cluster = {}
        self.cluster_centers = None
        self.page_cache.clear()
        self.next_page_id = 0
        self.total_vectors = 0
        self._vectors_cache = None

        if os.path.exists(self.pages_dir):
            try:
                for filename in os.listdir(self.pages_dir):
                    if filename.startswith("page_") and filename.endswith(".pkl"):
                        file_path = os.path.join(self.pages_dir, filename)
                        os.remove(file_path)
                os.rmdir(self.pages_dir)
            except Exception as e:
                print(f"Error limpiando archivos de páginas: {e}")

        self.save_metadata()

    def compact_pages(self):
        """
        Compacta páginas eliminando espacios vacíos.
        Útil después de muchas operaciones de eliminación.
        """
        print("Iniciando compactación de páginas...")

        new_page_directory = {}
        new_vector_index = {}
        new_next_page_id = 0

        active_vectors = {}
        for vector_id, (page_id, position) in self.vector_index.items():
            vector = self.get_vector(vector_id)
            if vector is not None:
                active_vectors[vector_id] = vector

        self.page_cache.clear()

        current_page_id = None
        current_position = 0

        for vector_id, vector in active_vectors.items():
            if current_page_id is None or current_position >= self.page_size:
                current_page_id = new_next_page_id
                new_next_page_id += 1
                current_position = 0

                new_page_directory[current_page_id] = {
                    "file_path": self._create_page_file_path(current_page_id),
                    "vector_count": 0,
                    "free_positions": list(range(self.page_size)),
                }

            page_data = self._load_page(current_page_id)
            page_data["vectors"][current_position] = vector
            page_data["dirty"] = True

            new_vector_index[vector_id] = (current_page_id, current_position)
            page_info = new_page_directory[current_page_id]
            page_info["free_positions"].remove(current_position)
            page_info["vector_count"] += 1

            current_position += 1

        for page_id in self.page_directory.keys():
            if page_id not in new_page_directory:
                old_file = self._create_page_file_path(page_id)
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except Exception as e:
                        print(f"Error eliminando página antigua {page_id}: {e}")

        self.page_directory = new_page_directory
        self.vector_index = new_vector_index
        self.next_page_id = new_next_page_id

        self._flush_all_pages()
        self.save_metadata()

        print(f"Compactación completada. Páginas activas: {len(self.page_directory)}")

    def get_storage_stats(self):
        """
        Obtiene estadísticas de almacenamiento

        Returns:
            dict: Estadísticas del almacenamiento
        """
        stats = {
            "total_vectors": self.total_vectors,
            "total_pages": len(self.page_directory),
            "pages_in_cache": len(self.page_cache),
            "average_vectors_per_page": 0,
            "fragmentation_ratio": 0,
            "disk_usage_bytes": 0,
        }

        if self.page_directory:
            total_capacity = len(self.page_directory) * self.page_size
            stats["average_vectors_per_page"] = self.total_vectors / len(
                self.page_directory
            )
            stats["fragmentation_ratio"] = 1.0 - (self.total_vectors / total_capacity)

        if os.path.exists(self.pages_dir):
            for filename in os.listdir(self.pages_dir):
                if filename.startswith("page_") and filename.endswith(".pkl"):
                    file_path = os.path.join(self.pages_dir, filename)
                    if os.path.exists(file_path):
                        stats["disk_usage_bytes"] += os.path.getsize(file_path)

        return stats
