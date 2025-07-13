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
        
        self.page_directory = {}  # {page_id: {'file_path': str, 'vector_count': int, 'free_positions': list}}
        
        self.page_cache = OrderedDict()  # {page_id: {'vectors': dict, 'dirty': bool}}
        
        self.clusters = {}  
        self.cluster_centers = None
        self.vector_to_cluster = {}
        
        self.next_page_id = 0
        self.total_vectors = 0
        
        self.pages_file = self.index_file.replace('.pkl', '_pages.dat') if self.index_file.endswith('.pkl') else self.index_file + '_pages.dat'
        self._vectors_cache = None
        self.load()

    
    def _load_page(self, page_id):
        """Carga una página desde el archivo único al cache"""
        if page_id in self.page_cache:
            self.page_cache.move_to_end(page_id)
            return self.page_cache[page_id]
        if len(self.page_cache) >= self.cache_size:
            self._evict_oldest_page()
        # Buscar la página en el archivo único
        page_data = {'vectors': {}, 'dirty': False}
        try:
            if os.path.exists(self.pages_file):
                with open(self.pages_file, 'rb') as f:
                    current_page = 0
                    while True:
                        header = f.read(8)
                        if not header or len(header) < 8:
                            break
                        page_size = int.from_bytes(header, 'big')
                        page_bytes = f.read(page_size)
                        if current_page == page_id:
                            if page_size == 0:
                                # Página vacía
                                vectors_data = {}
                            else:
                                vectors_data = pickle.loads(page_bytes)
                            page_data = {'vectors': vectors_data, 'dirty': False}
                            break
                        current_page += 1
        except Exception as e:
            print(f"Error cargando página {page_id}: {e}")
        self.page_cache[page_id] = page_data
        return page_data
    
    def _save_page(self, page_id):
        """Guarda una página desde cache al archivo único"""
        if page_id not in self.page_cache:
            return
        page_data = self.page_cache[page_id]
        if not page_data['dirty']:
            return
        max_page = max(self.page_directory.keys()) if self.page_directory else -1
        pages = []
        if os.path.exists(self.pages_file):
            with open(self.pages_file, 'rb') as f:
                for i in range(max_page + 1):
                    header = f.read(8)
                    if not header or len(header) < 8:
                        break
                    page_size = int.from_bytes(header, 'big')
                    page_bytes = f.read(page_size)
                    pages.append((header, page_bytes))
        # Actualizar solo la página modificada
        new_pages = []
        for i in range(max_page + 1):
            if i == page_id:
                pdata = self.page_cache[i]['vectors']
                vbytes = pickle.dumps(pdata) if pdata else pickle.dumps({})
                pheader = len(vbytes).to_bytes(8, 'big')
                new_pages.append(pheader + vbytes)
            elif i < len(pages):
                new_pages.append(pages[i][0] + pages[i][1])
            else:
                empty_bytes = pickle.dumps({})
                empty_header = len(empty_bytes).to_bytes(8, 'big')
                new_pages.append(empty_header + empty_bytes)
        with open(self.pages_file, 'wb') as f:
            for p in new_pages:
                f.write(p)
        page_data['dirty'] = False
    
    def _evict_oldest_page(self):
        """Remueve la página más antigua del cache (LRU)"""
        if not self.page_cache:
            return
        oldest_page_id, page_data = self.page_cache.popitem(last=False)
        if page_data['dirty']:
            self._save_page(oldest_page_id)
    
    def _flush_all_pages(self):
        """Guarda todas las páginas dirty a disco"""
        for page_id in list(self.page_cache.keys()):
            self._save_page(page_id)
    
    def _create_new_page(self):
        """Crea una nueva página"""
        page_id = self.next_page_id
        self.next_page_id += 1
        self.page_directory[page_id] = {
            'vector_count': 0,
            'free_positions': list(range(self.page_size))
        }
        # Inicializar la página en el cache antes de guardarla
        self.page_cache[page_id] = {'vectors': {}, 'dirty': True}
        self._save_page(page_id)
        return page_id
    
    def _find_available_page(self):
        """Encuentra una página con espacio disponible o crea una nueva"""
        for page_id, info in self.page_directory.items():
            if info['free_positions']:
                return page_id
        
        return self._create_new_page()
    
    def add_vector(self, id, vector):
        """
        Añade un vector al índice usando paginación
        (Ahora busca en todas las páginas si el id ya existe, si no, lo agrega en la primera página con espacio)
        """
        if isinstance(vector, list):
            vector = np.array(vector)
        self._invalidate_vectors_cache()
        # Buscar si el id ya existe en alguna página
        found = False
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for pos, v in page_data['vectors'].items():
                # Siempre guardar el formato {'id': id, 'vector': vector}
                if hasattr(v, 'id') and v.id == id:
                    page_data['vectors'][pos] = {'id': id, 'vector': vector}
                    page_data['dirty'] = True
                    found = True
                    break
                elif isinstance(v, dict) and v.get('id', None) == id:
                    page_data['vectors'][pos] = {'id': id, 'vector': vector}
                    page_data['dirty'] = True
                    found = True
                    break
            if found:
                break
        if not found:
            page_id = self._find_available_page()
            page_data = self._load_page(page_id)
            page_info = self.page_directory[page_id]
            if not page_info['free_positions']:
                page_id = self._create_new_page()
                page_data = self._load_page(page_id)
                page_info = self.page_directory[page_id]
            position = page_info['free_positions'].pop(0)
            # Guardar el id junto con el vector para poder buscarlo después
            page_data['vectors'][position] = {'id': id, 'vector': vector}
            page_data['dirty'] = True
            page_info['vector_count'] += 1
            self.total_vectors += 1
        if self.cluster_centers is not None:
            cluster_id = self._assign_to_nearest_cluster(vector)
            self.vector_to_cluster[id] = cluster_id
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            if id not in self.clusters[cluster_id]:
                self.clusters[cluster_id].append(id)
        self.save_metadata()
    
    def remove_vector(self, id):
        """
        Remueve un vector del índice usando paginación
        """
        self._invalidate_vectors_cache()
        found = False
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for pos, v in list(page_data['vectors'].items()):
                if (isinstance(v, dict) and v.get('id', None) == id) or (hasattr(v, 'id') and v.id == id):
                    del page_data['vectors'][pos]
                    page_data['dirty'] = True
                    page_info['free_positions'].append(pos)
                    page_info['free_positions'].sort()
                    page_info['vector_count'] -= 1
                    self.total_vectors -= 1
                    found = True
                    break
            if found:
                break
        if id in self.vector_to_cluster:
            cluster_id = self.vector_to_cluster[id]
            if cluster_id in self.clusters and id in self.clusters[cluster_id]:
                self.clusters[cluster_id].remove(id)
            del self.vector_to_cluster[id]
        self.save_metadata()
        return found
    
    def get_vector(self, id):
        """
        Obtiene un vector por su ID usando paginación (busca en todas las páginas)
        """
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for v in page_data['vectors'].values():
                if (isinstance(v, dict) and v.get('id', None) == id) or (hasattr(v, 'id') and v.id == id):
                    return v['vector'] if isinstance(v, dict) and 'vector' in v else v
        return None
    
    # La propiedad vectors se elimina para evitar cargar todo en memoria
    
    def _invalidate_vectors_cache(self):
        """Invalida el cache de vectores"""
        self._vectors_cache = None
        
    def search_knn(self, query_vector, k=5):
        """
        Búsqueda KNN optimizada usando heap para mantener solo los k mejores vecinos.
        """
        import heapq
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)
        best_k = []  # heap de tamaño k
        # Por ahora, recorre todas las páginas (en el futuro, se puede filtrar por clustering)
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for v in page_data['vectors'].values():
                if isinstance(v, dict) and 'id' in v and 'vector' in v:
                    vector_id = v['id']
                    vector = v['vector']
                elif hasattr(v, 'id') and hasattr(v, 'vector'):
                    vector_id = v.id
                    vector = v.vector
                else:
                    continue
                distance = self.compute_distance(query_vector, vector)
                if len(best_k) < k:
                    heapq.heappush(best_k, (-distance, vector_id))
                elif distance < -best_k[0][0]:
                    heapq.heapreplace(best_k, (-distance, vector_id))
        # Ordenar los k mejores por distancia ascendente
        return [(vid, -dist) for dist, vid in sorted(best_k, key=lambda x: -x[0])]
        
    def search_knn_with_index(self, query_vector, k=5):
        """
        Búsqueda KNN usando clustering para filtrar páginas relevantes y acelerar la búsqueda.
        Solo busca en las páginas que contienen los IDs de los clusters más cercanos.
        """
        import heapq
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)
        if self.cluster_centers is None or not self.clusters:
            return self.search_knn(query_vector, k)
        # Ordenar clusters por cercanía al query
        cluster_distances = self._get_ordered_clusters(query_vector)
        # Buscar solo en los clusters más cercanos (ej: 3 más cercanos)
        best_k = []
        visited_ids = set()
        clusters_to_search = [cid for cid, _ in cluster_distances[:min(3, len(cluster_distances))]]
        for cluster_id in clusters_to_search:
            for vector_id in self.clusters.get(cluster_id, []):
                if vector_id in visited_ids:
                    continue
                vector = self.get_vector(vector_id)
                if vector is not None:
                    distance = self.compute_distance(query_vector, vector)
                    if len(best_k) < k:
                        heapq.heappush(best_k, (-distance, vector_id))
                    elif distance < -best_k[0][0]:
                        heapq.heapreplace(best_k, (-distance, vector_id))
                    visited_ids.add(vector_id)
        # Si no hay suficientes candidatos, buscar en el resto de clusters
        if len(best_k) < k:
            for cluster_id, _ in cluster_distances[min(3, len(cluster_distances)):]:
                for vector_id in self.clusters.get(cluster_id, []):
                    if vector_id in visited_ids:
                        continue
                    vector = self.get_vector(vector_id)
                    if vector is not None:
                        distance = self.compute_distance(query_vector, vector)
                        if len(best_k) < k:
                            heapq.heappush(best_k, (-distance, vector_id))
                        elif distance < -best_k[0][0]:
                            heapq.heapreplace(best_k, (-distance, vector_id))
                        visited_ids.add(vector_id)
                    if len(best_k) >= k:
                        break
                if len(best_k) >= k:
                    break
        # Si aún no hay suficientes, usar el método completo
        if len(best_k) < k:
            return self.search_knn(query_vector, k)
        return [(vid, -dist) for dist, vid in sorted(best_k, key=lambda x: -x[0])]
    
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
                cluster_candidates = self._get_cluster_candidates(query_vector, cluster_id)
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
        Construye clusters usando K-means con paginación.
        Siempre asigna todos los vectores a al menos un cluster, aunque haya poca variación o error.
        Incluye prints de depuración para vector_ids, vector_data y cluster_labels.
        """
        # Asegura que todas las páginas estén en disco y actualizadas antes de clusterizar
        self._flush_all_pages()
        if self.total_vectors < num_clusters:
            num_clusters = max(1, self.total_vectors)
        if self.total_vectors == 0:
            print("[DEBUG] No hay vectores para clusterizar.")
            return
        vector_ids = []
        vector_data = []
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for v in page_data['vectors'].values():
                if isinstance(v, dict) and 'id' in v and 'vector' in v:
                    vector_ids.append(v['id'])
                    vector_data.append(v['vector'])
                elif hasattr(v, 'id') and hasattr(v, 'vector'):
                    vector_ids.append(v.id)
                    vector_data.append(v.vector)
        if not vector_data:
            return
        vector_data = np.array(vector_data)
        unique_vectors = np.unique(vector_data, axis=0)
        if len(unique_vectors) < num_clusters:
            num_clusters = max(1, len(unique_vectors))
        try:
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(vector_data)
            #
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
            # Refuerzo: si por cualquier motivo no hay clusters válidos, asignar todos a uno solo
            if not self.clusters or sum(len(v) for v in self.clusters.values()) == 0:
                self.clusters = {0: vector_ids}
                self.vector_to_cluster = dict.fromkeys(vector_ids, 0)
                self.cluster_centers = np.array([np.mean(vector_data, axis=0)])
            self.save_metadata()
        except Exception as e:
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
        
        min_distance = float('inf')
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
        Guarda solo los metadatos del índice (sin vector_index)
        """
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            metadata = {
                'page_directory': {str(k): v for k, v in self.page_directory.items()},
                'clusters': {str(k): v for k, v in self.clusters.items()},
                'vector_to_cluster': {str(k): int(v) if isinstance(v, np.integer) else v 
                                    for k, v in self.vector_to_cluster.items()},
                'cluster_centers': self.cluster_centers.tolist() if self.cluster_centers is not None else None,
                'next_page_id': self.next_page_id,
                'total_vectors': self.total_vectors,
                'page_size': self.page_size,
                'cache_size': self.cache_size
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error al guardar metadatos del índice de vectores: {e}")
        
    def load(self):
        """
        Carga el índice desde archivos (solo metadata, páginas se cargan on-demand)
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                page_directory_raw = metadata.get('page_directory', {})
                self.page_directory = {}
                for k, v in page_directory_raw.items():
                    try:
                        key = int(k)
                    except (ValueError, TypeError):
                        key = k
                    self.page_directory[key] = v
                self.clusters = {int(k): v for k, v in metadata.get('clusters', {}).items()}
                vector_to_cluster_raw = metadata.get('vector_to_cluster', {})
                self.vector_to_cluster = {}
                for k, v in vector_to_cluster_raw.items():
                    try:
                        key = int(k) if k.isdigit() else k
                    except (ValueError, TypeError):
                        key = k
                    self.vector_to_cluster[key] = int(v) if isinstance(v, (int, float, str)) and str(v).isdigit() else v
                cluster_centers_data = metadata.get('cluster_centers')
                if cluster_centers_data:
                    self.cluster_centers = np.array(cluster_centers_data)
                else:
                    self.cluster_centers = None
                self.next_page_id = metadata.get('next_page_id', 0)
                self.total_vectors = metadata.get('total_vectors', 0)
                self.page_size = metadata.get('page_size', self.page_size)
                self.cache_size = metadata.get('cache_size', self.cache_size)
        except Exception as e:
            print(f"Error al cargar metadatos del índice de vectores: {e}")
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
            'pages_in_cache': len(self.page_cache),
            'cache_size_limit': self.cache_size,
            'dirty_pages': sum(1 for page_data in self.page_cache.values() if page_data['dirty'])
        }
    
    def clear(self):
        """
        Limpia todos los datos del índice y elimina el archivo de páginas
        """
        self.page_directory = {}
        self.clusters = {}
        self.vector_to_cluster = {}
        self.cluster_centers = None
        self.page_cache.clear()
        self.next_page_id = 0
        self.total_vectors = 0
        self._vectors_cache = None
        if os.path.exists(self.pages_file):
            try:
                os.remove(self.pages_file)
            except Exception as e:
                print(f"Error limpiando archivo de páginas: {e}")
        self.save_metadata()
    
    def compact_pages(self):
        """
        Compacta páginas eliminando espacios vacíos.
        Útil después de muchas operaciones de eliminación.
        """
        print("Iniciando compactación de páginas...")
        new_page_directory = {}
        new_next_page_id = 0
        # Extraer todos los vectores activos
        active_vectors = []
        for page_id, page_info in self.page_directory.items():
            page_data = self._load_page(page_id)
            for v in page_data['vectors'].values():
                if isinstance(v, dict) and 'id' in v and 'vector' in v:
                    active_vectors.append((v['id'], v['vector']))
                elif hasattr(v, 'id') and hasattr(v, 'vector'):
                    active_vectors.append((v.id, v.vector))
        self.page_cache.clear()
        current_page_id = None
        current_position = 0
        for vector_id, vector in active_vectors:
            if current_page_id is None or current_position >= self.page_size:
                current_page_id = new_next_page_id
                new_next_page_id += 1
                current_position = 0
                new_page_directory[current_page_id] = {
                    'vector_count': 0,
                    'free_positions': list(range(self.page_size))
                }
            page_data = self._load_page(current_page_id)
            page_data['vectors'][current_position] = {'id': vector_id, 'vector': vector}
            page_data['dirty'] = True
            page_info = new_page_directory[current_page_id]
            page_info['free_positions'].remove(current_position)
            page_info['vector_count'] += 1
            current_position += 1
        self.page_directory = new_page_directory
        self.next_page_id = new_next_page_id
        self._flush_all_pages()
        self.save_metadata()
        print(f"Compactación completada. Páginas activas: {len(self.page_directory)}")
    
    def get_storage_stats(self):
        """
        Obtiene estadísticas de almacenamiento
        """
        stats = {
            'total_vectors': self.total_vectors,
            'total_pages': len(self.page_directory),
            'pages_in_cache': len(self.page_cache),
            'average_vectors_per_page': 0,
            'fragmentation_ratio': 0,
            'disk_usage_bytes': 0
        }
        if self.page_directory:
            total_capacity = len(self.page_directory) * self.page_size
            stats['average_vectors_per_page'] = self.total_vectors / len(self.page_directory)
            stats['fragmentation_ratio'] = 1.0 - (self.total_vectors / total_capacity)
        if os.path.exists(self.pages_file):
            stats['disk_usage_bytes'] = os.path.getsize(self.pages_file)
        return stats
