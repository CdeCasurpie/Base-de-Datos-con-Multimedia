import os
import json
import numpy as np
from sklearn.cluster import KMeans
import pickle
import math
import warnings
from collections import OrderedDict
import heapq
import glob

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.cluster")

class VectorIndex:
    """
    Estructura de datos para vectores TF-IDF con visual words y paginación.
    
    ARQUITECTURA DE ALMACENAMIENTO:
    1. _tfidf_vectors.dat: ID → vector TF-IDF (paginado tradicional)
    2. cluster_X.dat: Un archivo por cluster conteniendo lista de doc_ids (paginado vertical)
    3. metadata.json: IDF por cluster en RAM + configuración
    
    PAGINACIÓN:
    - TF-IDF vectors: Paginación horizontal tradicional (como actual)
    - Clusters: Paginación vertical simple - cada cluster crece en su propio archivo
      Formato: [HEADER: 8 bytes size][PAGE_0: doc_ids][HEADER: 8 bytes][PAGE_1: doc_ids]...
    """
    
    def __init__(self, index_file, metadata_file, page_size=100, cache_size=10, num_clusters=500, table_name=None):
        self.index_file = index_file
        self.metadata_file = metadata_file
        self.page_size = page_size  
        self.cache_size = cache_size
        self.num_clusters = num_clusters
        
        # Extraer nombre de tabla para evitar colisiones
        if table_name:
            self.table_name = table_name
        else:
            # Extraer del nombre del archivo si no se proporciona
            base_name = os.path.basename(index_file)
            self.table_name = base_name.replace('.pkl', '').replace('_index', '')
        
        # Archivos de datos con nombres únicos por tabla
        self.tfidf_vectors_file = self.index_file.replace('.pkl', '_tfidf_vectors.dat')
        self.clusters_dir = os.path.join(os.path.dirname(self.index_file), f'clusters_{self.table_name}')
        os.makedirs(self.clusters_dir, exist_ok=True)
        
        # Estructura 1: ID → vector TF-IDF (paginado horizontal tradicional)
        self.tfidf_page_directory = {}  # {page_id: {'vector_count': int, 'free_positions': list}}
        self.tfidf_page_cache = OrderedDict()  # {page_id: {'vectors': dict, 'dirty': bool}}
        self.next_tfidf_page_id = 0
        
        # Estructura 2: Cluster files (un archivo por cluster, paginado vertical)
        self.cluster_files = {}  # {cluster_id: 'path/cluster_X.dat'}
        self.cluster_cache = OrderedDict()  # {cluster_id: {'doc_ids': list, 'dirty': bool}}
        
        # Estructura 3: Cluster ID → IDF (en RAM)
        self.cluster_idf = {}  # {cluster_id: idf_value}
        self.cluster_document_count = {}  # {cluster_id: num_documents_containing_cluster}
        
        # Vocabulario visual (centroides de clusters)
        self.cluster_centers = None
        self.is_trained = False
        
        # Metadatos generales
        self.total_vectors = 0  # Total de documentos
        self.total_descriptors_processed = 0
        
        # Compatibilidad con interfaz anterior
        self.clusters = {}  # {cluster_id: [doc_ids]} - solo para compatibilidad
        self.vector_to_cluster = {}  # {doc_id: cluster_id}
        self.next_page_id = 0  # Alias para next_tfidf_page_id
        
        self.load()
    
    # ========== ENTRENAMIENTO DEL VOCABULARIO VISUAL ==========
    
    def train_visual_vocabulary(self, folder_path, feature_extractor):
        """
        Entrena el vocabulario visual a partir de todos los archivos en una carpeta y sus subcarpetas.
        """
        print(f"Iniciando entrenamiento de vocabulario visual desde: {folder_path}")
        
        # Buscar archivos multimedia recursivamente
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.wav', '.mp3', '.flac', '.ogg']
        all_files = []
        
        for ext in extensions:
            all_files.extend(glob.glob(os.path.join(folder_path, '**', f'*{ext}'), recursive=True))
            all_files.extend(glob.glob(os.path.join(folder_path, '**', f'*{ext.upper()}'), recursive=True))
        
        if not all_files:
            raise ValueError(f"No se encontraron archivos multimedia en {folder_path}")
        
        print(f"Encontrados {len(all_files)} archivos para entrenamiento")
        
        # Extraer descriptores de todos los archivos
        all_descriptors = []
        processed_files = 0
        
        for file_path in all_files:
            try:
                descriptors = feature_extractor.extract(file_path)
                if descriptors and len(descriptors) > 0:
                    all_descriptors.extend(descriptors)
                    processed_files += 1
                    if processed_files % 100 == 0:
                        print(f"Procesados {processed_files}/{len(all_files)} archivos...")
            except Exception as e:
                print(f"Error procesando {file_path}: {e}")
                continue
        
        if not all_descriptors:
            raise ValueError("No se pudieron extraer descriptores de ningún archivo")
        
        print(f"Total descriptores extraídos: {len(all_descriptors)}")
        
        # Convertir a matriz numpy para K-means
        descriptors_matrix = np.vstack(all_descriptors)
        
        # Ajustar número de clusters si hay pocos descriptores
        effective_clusters = min(self.num_clusters, len(all_descriptors))
        
        print(f"Entrenando K-means con {effective_clusters} clusters...")
        
        # Entrenar K-means
        kmeans = KMeans(n_clusters=effective_clusters, random_state=42, n_init=10)
        kmeans.fit(descriptors_matrix)
        
        self.cluster_centers = kmeans.cluster_centers_
        self.num_clusters = effective_clusters
        self.is_trained = True
        
        # Inicializar estructuras
        self.cluster_idf = {i: 0.0 for i in range(self.num_clusters)}
        self.cluster_document_count = {i: 0 for i in range(self.num_clusters)}
        
        # Crear archivos de clusters vacíos
        self.cluster_files = {}
        for cluster_id in range(self.num_clusters):
            cluster_file = os.path.join(self.clusters_dir, f'cluster_{cluster_id}.dat')
            self.cluster_files[cluster_id] = cluster_file
            # Crear archivo vacío
            with open(cluster_file, 'wb') as f:
                pass  # Archivo vacío
        
        print(f"Vocabulario visual entrenado exitosamente con {self.num_clusters} clusters")
        self.save_metadata()
    
    # ========== MÉTODOS PRINCIPALES ==========
    
    def add_vectors(self, doc_id, local_descriptors, save_metadata=True):
        """
        Añade un documento al índice TF-IDF.
        """
        if not self.is_trained:
            raise RuntimeError("Debe entrenar el vocabulario visual primero con train_visual_vocabulary()")
        
        if not local_descriptors or len(local_descriptors) == 0:
            print(f"Warning: No hay descriptores para documento {doc_id}")
            return
        
        # 1. Crear histograma TF
        tf_histogram = self._create_tf_histogram(local_descriptors)
        
        # 2. Actualizar conteos de documentos por cluster
        self._update_document_counts_and_idf(tf_histogram)
        
        # 3. Calcular vector TF-IDF
        tfidf_vector = self._calculate_tfidf_vector(tf_histogram)
        
        # 4. Guardar vector TF-IDF
        self._store_tfidf_vector(doc_id, tfidf_vector)
        
        # 5. Actualizar archivos de clusters
        for cluster_id, count in enumerate(tf_histogram):
            if count > 0:  # Documento contiene este cluster
                self._add_document_to_cluster(cluster_id, doc_id)
        
        self.total_vectors += 1
        
        if save_metadata:
            self.save_metadata()
    
    def add_vector(self, doc_id, local_descriptors, save_metadata=True):
        """COMPATIBILIDAD: Alias para add_vectors"""
        return self.add_vectors(doc_id, local_descriptors, save_metadata)
    
    def remove_vector(self, doc_id, save_metadata=True):
        """
        Remueve un documento del índice TF-IDF.
        """
        # Obtener vector TF-IDF actual para saber qué clusters actualizar
        tfidf_vector = self._get_tfidf_vector(doc_id)
        if tfidf_vector is None:
            return False
        
        # Remover de estructuras TF-IDF
        success = self._remove_tfidf_vector(doc_id)
        if not success:
            return False
        
        # Remover de archivos de clusters (donde TF-IDF > 0)
        for cluster_id, tfidf_value in enumerate(tfidf_vector):
            if tfidf_value > 0:
                self._remove_document_from_cluster(cluster_id, doc_id)
                # Actualizar conteos
                if cluster_id in self.cluster_document_count:
                    self.cluster_document_count[cluster_id] = max(0, self.cluster_document_count[cluster_id] - 1)
        
        # Recalcular IDF
        self._recalculate_all_idf()
        
        self.total_vectors -= 1
        
        if save_metadata:
            self.save_metadata()
        
        return True
    
    def get_vector(self, doc_id):
        """
        Obtiene vector TF-IDF de un documento por su ID.
        """
        return self._get_tfidf_vector(doc_id)
    
    # ========== BÚSQUEDAS KNN ==========
    
    def search_knn(self, query_descriptors, k=5):
        """
        Búsqueda KNN usando TF-IDF (búsqueda lineal completa).
        """
        if not self.is_trained:
            raise RuntimeError("Vocabulario visual no entrenado")
        
        # Crear vector TF-IDF de consulta
        query_tf = self._create_tf_histogram(query_descriptors)
        query_tfidf = self._calculate_tfidf_vector(query_tf)
        
        best_k = []
        
        # Recorrer todas las páginas TF-IDF
        for page_id in self.tfidf_page_directory:
            page_data = self._load_tfidf_page(page_id)
            
            for entry in page_data['vectors'].values():
                if isinstance(entry, dict) and 'id' in entry and 'tfidf_vector' in entry:
                    doc_id = entry['id']
                    doc_tfidf = entry['tfidf_vector']
                    
                    distance = self._compute_cosine_distance(query_tfidf, doc_tfidf)
                    
                    if len(best_k) < k:
                        heapq.heappush(best_k, (-distance, doc_id))
                    elif distance < -best_k[0][0]:
                        heapq.heapreplace(best_k, (-distance, doc_id))
        
        return [(doc_id, -dist) for dist, doc_id in sorted(best_k, key=lambda x: -x[0])]
    
    def search_knn_with_index(self, query_descriptors, k=5, clusters_to_check=10):
        """
        Búsqueda KNN optimizada usando archivos de clusters como índice invertido.
        """
        if not self.is_trained:
            raise RuntimeError("Vocabulario visual no entrenado")
        
        # Crear TF-IDF de consulta
        query_tf = self._create_tf_histogram(query_descriptors)
        query_tfidf = self._calculate_tfidf_vector(query_tf)
        
        # Identificar clusters relevantes ordenados por importancia
        relevant_clusters = []
        for cluster_id, tf_value in enumerate(query_tf):
            if tf_value > 0:
                tfidf_value = query_tfidf[cluster_id]
                relevant_clusters.append((cluster_id, tfidf_value))
        
        # Ordenar por importancia TF-IDF descendente
        relevant_clusters.sort(key=lambda x: x[1], reverse=True)
        
        # Buscar candidatos usando heap
        best_k = []
        visited_docs = set()
        
        # Procesar clusters más relevantes primero
        clusters_processed = 0
        for cluster_id, _ in relevant_clusters:
            if clusters_processed >= clusters_to_check and len(best_k) >= k:
                break
            
            doc_ids = self._load_cluster_documents(cluster_id)
            
            for doc_id in doc_ids:
                if doc_id in visited_docs:
                    continue
                
                doc_tfidf = self._get_tfidf_vector(doc_id)
                if doc_tfidf is not None:
                    distance = self._compute_cosine_distance(query_tfidf, doc_tfidf)
                    
                    if len(best_k) < k:
                        heapq.heappush(best_k, (-distance, doc_id))
                    elif distance < -best_k[0][0]:
                        heapq.heapreplace(best_k, (-distance, doc_id))
                    
                    visited_docs.add(doc_id)
            
            clusters_processed += 1
        
        # Si no hay suficientes, buscar en clusters restantes
        if len(best_k) < k and clusters_processed < len(relevant_clusters):
            for cluster_id, _ in relevant_clusters[clusters_processed:]:
                doc_ids = self._load_cluster_documents(cluster_id)
                
                for doc_id in doc_ids:
                    if doc_id in visited_docs:
                        continue
                    
                    doc_tfidf = self._get_tfidf_vector(doc_id)
                    if doc_tfidf is not None:
                        distance = self._compute_cosine_distance(query_tfidf, doc_tfidf)
                        
                        if len(best_k) < k:
                            heapq.heappush(best_k, (-distance, doc_id))
                        elif distance < -best_k[0][0]:
                            heapq.heapreplace(best_k, (-distance, doc_id))
                        
                        visited_docs.add(doc_id)
                
                if len(best_k) >= k:
                    break
        
        return [(doc_id, -dist) for dist, doc_id in sorted(best_k, key=lambda x: -x[0])]
    
    # ========== GESTIÓN DE ARCHIVOS DE CLUSTERS ==========
    
    def _get_cluster_file_path(self, cluster_id):
        """Retorna la ruta del archivo para un cluster específico."""
        return os.path.join(self.clusters_dir, f'cluster_{cluster_id}.dat')
    
    def _load_cluster_documents(self, cluster_id):
        """
        Carga la lista de documentos de un cluster desde su archivo.
        """
        if cluster_id in self.cluster_cache:
            self.cluster_cache.move_to_end(cluster_id)
            return self.cluster_cache[cluster_id]['doc_ids']
        
        # Limpiar cache si está lleno
        if len(self.cluster_cache) >= self.cache_size:
            self._evict_oldest_cluster()
        
        cluster_file = self._get_cluster_file_path(cluster_id)
        doc_ids = []
        
        try:
            if os.path.exists(cluster_file) and os.path.getsize(cluster_file) > 0:
                with open(cluster_file, 'rb') as f:
                    while True:
                        header = f.read(8)
                        if not header or len(header) < 8:
                            break
                        page_size = int.from_bytes(header, 'big')
                        if page_size == 0:
                            break
                        page_data = pickle.loads(f.read(page_size))
                        doc_ids.extend(page_data)
        except Exception as e:
            print(f"Error cargando cluster {cluster_id}: {e}")
        
        self.cluster_cache[cluster_id] = {'doc_ids': doc_ids, 'dirty': False}
        return doc_ids
    
    def _save_cluster_documents(self, cluster_id, doc_ids_list):
        """
        Guarda la lista de documentos de un cluster a su archivo.
        """
        cluster_file = self._get_cluster_file_path(cluster_id)
        
        try:
            with open(cluster_file, 'wb') as f:
                # Dividir en páginas
                for i in range(0, len(doc_ids_list), self.page_size):
                    page_data = doc_ids_list[i:i + self.page_size]
                    page_bytes = pickle.dumps(page_data)
                    header = len(page_bytes).to_bytes(8, 'big')
                    f.write(header + page_bytes)
        except Exception as e:
            print(f"Error guardando cluster {cluster_id}: {e}")
    
    def _add_document_to_cluster(self, cluster_id, doc_id):
        """Añade un documento a un cluster específico."""
        doc_ids = self._load_cluster_documents(cluster_id)
        
        if doc_id not in doc_ids:
            doc_ids.append(doc_id)
            self.cluster_cache[cluster_id]['dirty'] = True
    
    def _remove_document_from_cluster(self, cluster_id, doc_id):
        """Remueve un documento de un cluster específico."""
        doc_ids = self._load_cluster_documents(cluster_id)
        
        if doc_id in doc_ids:
            doc_ids.remove(doc_id)
            self.cluster_cache[cluster_id]['dirty'] = True
    
    def _evict_oldest_cluster(self):
        """Remueve el cluster más antiguo del cache."""
        if not self.cluster_cache:
            return
        
        oldest_cluster_id, cluster_data = self.cluster_cache.popitem(last=False)
        if cluster_data['dirty']:
            self._save_cluster_documents(oldest_cluster_id, cluster_data['doc_ids'])
    
    # ========== GESTIÓN DE VECTORES TF-IDF ==========
    
    def _store_tfidf_vector(self, doc_id, tfidf_vector):
        """Almacena un vector TF-IDF usando paginación horizontal."""
        page_id = self._find_available_tfidf_page()
        page_data = self._load_tfidf_page(page_id)
        page_info = self.tfidf_page_directory[page_id]
        
        position = page_info['free_positions'].pop(0)
        page_data['vectors'][position] = {'id': doc_id, 'tfidf_vector': tfidf_vector}
        page_data['dirty'] = True
        page_info['vector_count'] += 1
    
    def _get_tfidf_vector(self, doc_id):
        """Obtiene un vector TF-IDF por doc_id."""
        for page_id in self.tfidf_page_directory:
            page_data = self._load_tfidf_page(page_id)
            for entry in page_data['vectors'].values():
                if isinstance(entry, dict) and entry.get('id') == doc_id:
                    return entry['tfidf_vector']
        return None
    
    def _remove_tfidf_vector(self, doc_id):
        """Remueve un vector TF-IDF por doc_id."""
        for page_id, page_info in self.tfidf_page_directory.items():
            page_data = self._load_tfidf_page(page_id)
            for pos, entry in list(page_data['vectors'].items()):
                if isinstance(entry, dict) and entry.get('id') == doc_id:
                    del page_data['vectors'][pos]
                    page_data['dirty'] = True
                    page_info['free_positions'].append(pos)
                    page_info['free_positions'].sort()
                    page_info['vector_count'] -= 1
                    return True
        return False
    
    # ========== CÁLCULOS TF-IDF ==========
    
    def _create_tf_histogram(self, local_descriptors):
        """Crea histograma TF asignando descriptores a clusters más cercanos."""
        tf_histogram = np.zeros(self.num_clusters, dtype=np.int32)
        
        for descriptor in local_descriptors:
            # Encontrar cluster más cercano
            distances = np.linalg.norm(self.cluster_centers - descriptor, axis=1)
            nearest_cluster = np.argmin(distances)
            tf_histogram[nearest_cluster] += 1
        
        return tf_histogram
    
    def _calculate_tfidf_vector(self, tf_histogram):
        """Calcula vector TF-IDF multiplicando TF * IDF."""
        tfidf_vector = np.zeros(self.num_clusters, dtype=np.float32)
        
        for cluster_id, tf_value in enumerate(tf_histogram):
            if tf_value > 0:
                idf_value = self.cluster_idf.get(cluster_id, 1.0)
                tfidf_vector[cluster_id] = tf_value * idf_value
        
        return tfidf_vector
    
    def _update_document_counts_and_idf(self, tf_histogram):
        """Actualiza conteos de documentos por cluster y recalcula IDF."""
        for cluster_id, count in enumerate(tf_histogram):
            if count > 0:  # Documento contiene este cluster
                if cluster_id not in self.cluster_document_count:
                    self.cluster_document_count[cluster_id] = 0
                self.cluster_document_count[cluster_id] += 1
        
        self._recalculate_all_idf()
    
    def _recalculate_all_idf(self):
        """Recalcula valores IDF para todos los clusters."""
        if self.total_vectors == 0:
            return
        
        for cluster_id in range(self.num_clusters):
            doc_count = self.cluster_document_count.get(cluster_id, 0)
            if doc_count > 0:
                idf_value = math.log(self.total_vectors / doc_count)
                self.cluster_idf[cluster_id] = idf_value
            else:
                self.cluster_idf[cluster_id] = 0.0
    
    def _compute_cosine_distance(self, vec1, vec2):
        """Calcula distancia coseno entre dos vectores TF-IDF."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        cosine_sim = dot_product / (norm1 * norm2)
        return 1.0 - cosine_sim
    
    # ========== PAGINACIÓN TF-IDF ==========
    
    def _find_available_tfidf_page(self):
        """Encuentra página TF-IDF con espacio o crea nueva."""
        for page_id, info in self.tfidf_page_directory.items():
            if info['free_positions']:
                return page_id
        return self._create_new_tfidf_page()
    
    def _create_new_tfidf_page(self):
        """Crea nueva página TF-IDF."""
        page_id = self.next_tfidf_page_id
        self.next_tfidf_page_id += 1
        self.tfidf_page_directory[page_id] = {
            'vector_count': 0,
            'free_positions': list(range(self.page_size))
        }
        self.tfidf_page_cache[page_id] = {'vectors': {}, 'dirty': True}
        return page_id
    
    def _load_tfidf_page(self, page_id):
        """Carga página TF-IDF al cache."""
        if page_id in self.tfidf_page_cache:
            self.tfidf_page_cache.move_to_end(page_id)
            return self.tfidf_page_cache[page_id]
        
        if len(self.tfidf_page_cache) >= self.cache_size:
            self._evict_oldest_tfidf_page()
        
        page_data = {'vectors': {}, 'dirty': False}
        try:
            if os.path.exists(self.tfidf_vectors_file):
                with open(self.tfidf_vectors_file, 'rb') as f:
                    current_page = 0
                    while True:
                        header = f.read(8)
                        if not header or len(header) < 8:
                            break
                        page_size = int.from_bytes(header, 'big')
                        page_bytes = f.read(page_size)
                        if current_page == page_id:
                            if page_size > 0:
                                vectors_data = pickle.loads(page_bytes)
                                page_data = {'vectors': vectors_data, 'dirty': False}
                            break
                        current_page += 1
        except Exception as e:
            print(f"Error cargando página TF-IDF {page_id}: {e}")
        
        self.tfidf_page_cache[page_id] = page_data
        return page_data
    
    def _save_tfidf_page(self, page_id):
        """Guarda página TF-IDF a disco."""
        if page_id not in self.tfidf_page_cache:
            return
        
        page_data = self.tfidf_page_cache[page_id]
        if not page_data['dirty']:
            return
        
        max_page = max(self.tfidf_page_directory.keys()) if self.tfidf_page_directory else -1
        pages = []
        
        if os.path.exists(self.tfidf_vectors_file):
            with open(self.tfidf_vectors_file, 'rb') as f:
                for i in range(max_page + 1):
                    header = f.read(8)
                    if not header or len(header) < 8:
                        break
                    page_size = int.from_bytes(header, 'big')
                    page_bytes = f.read(page_size)
                    pages.append((header, page_bytes))
        
        new_pages = []
        for i in range(max_page + 1):
            if i == page_id:
                pdata = self.tfidf_page_cache[i]['vectors']
                vbytes = pickle.dumps(pdata) if pdata else pickle.dumps({})
                pheader = len(vbytes).to_bytes(8, 'big')
                new_pages.append(pheader + vbytes)
            elif i < len(pages):
                new_pages.append(pages[i][0] + pages[i][1])
            else:
                empty_bytes = pickle.dumps({})
                empty_header = len(empty_bytes).to_bytes(8, 'big')
                new_pages.append(empty_header + empty_bytes)
        
        with open(self.tfidf_vectors_file, 'wb') as f:
            for p in new_pages:
                f.write(p)
        
        page_data['dirty'] = False
    
    def _evict_oldest_tfidf_page(self):
        """Remueve página TF-IDF más antigua del cache."""
        if not self.tfidf_page_cache:
            return
        
        oldest_page_id, page_data = self.tfidf_page_cache.popitem(last=False)
        if page_data['dirty']:
            self._save_tfidf_page(oldest_page_id)
    
    # ========== COMPATIBILIDAD ==========
    
    def build_kmeans_clusters(self, folder_path=None, feature_extractor=None, num_clusters=None):
        """COMPATIBILIDAD: Redirige a train_visual_vocabulary."""
        if folder_path and feature_extractor:
            if num_clusters:
                self.num_clusters = num_clusters
            return self.train_visual_vocabulary(folder_path, feature_extractor)
        else:
            raise ValueError("build_kmeans_clusters requiere folder_path y feature_extractor")
    
    @property 
    def next_page_id(self):
        return self.next_tfidf_page_id
    
    @next_page_id.setter
    def next_page_id(self, value):
        self.next_tfidf_page_id = value
    
    def _sync_clusters_dict(self):
        """Sincroniza self.clusters dict para compatibilidad."""
        self.clusters = {}
        for cluster_id in range(self.num_clusters):
            doc_ids = self._load_cluster_documents(cluster_id)
            if doc_ids:
                self.clusters[cluster_id] = doc_ids
    
    def compute_distance(self, vec1, vec2):
        """COMPATIBILIDAD: Usa distancia coseno para TF-IDF."""
        return self._compute_cosine_distance(vec1, vec2)
    
    # ========== PERSISTENCIA ==========
    
    def save_metadata(self):
        """Guarda metadatos del índice."""
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            metadata = {
                # Identificador de tabla para evitar colisiones
                'table_name': self.table_name,
                
                # Estructura 3: IDF en RAM
                'cluster_idf': {str(k): float(v) for k, v in self.cluster_idf.items()},
                'cluster_document_count': {str(k): int(v) for k, v in self.cluster_document_count.items()},
                
                # Vocabulario visual
                'cluster_centers': self.cluster_centers.tolist() if self.cluster_centers is not None else None,
                'num_clusters': self.num_clusters,
                'is_trained': self.is_trained,
                
                # Metadatos de paginación TF-IDF
                'tfidf_page_directory': {str(k): v for k, v in self.tfidf_page_directory.items()},
                'next_tfidf_page_id': self.next_tfidf_page_id,
                
                # Archivos de clusters
                'cluster_files': {str(k): v for k, v in self.cluster_files.items()},
                
                # Estadísticas generales
                'total_vectors': self.total_vectors,
                'total_descriptors_processed': self.total_descriptors_processed,
                'page_size': self.page_size,
                'cache_size': self.cache_size
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Error guardando metadatos TF-IDF: {e}")
    
    def load(self):
        """Carga metadatos del índice."""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Cargar table_name si existe
                loaded_table_name = metadata.get('table_name')
                if loaded_table_name and not hasattr(self, 'table_name'):
                    self.table_name = loaded_table_name
                    # Actualizar clusters_dir con el nombre correcto
                    self.clusters_dir = os.path.join(os.path.dirname(self.index_file), f'clusters_{self.table_name}')
                    os.makedirs(self.clusters_dir, exist_ok=True)
                
                # Cargar Estructura 3: IDF
                self.cluster_idf = {int(k): float(v) for k, v in metadata.get('cluster_idf', {}).items()}
                self.cluster_document_count = {int(k): int(v) for k, v in metadata.get('cluster_document_count', {}).items()}
                
                # Cargar vocabulario visual
                cluster_centers_data = metadata.get('cluster_centers')
                if cluster_centers_data:
                    self.cluster_centers = np.array(cluster_centers_data)
                self.num_clusters = metadata.get('num_clusters', self.num_clusters)
                self.is_trained = metadata.get('is_trained', False)
                
                # Cargar metadatos de paginación TF-IDF
                self.tfidf_page_directory = {int(k): v for k, v in metadata.get('tfidf_page_directory', {}).items()}
                self.next_tfidf_page_id = metadata.get('next_tfidf_page_id', 0)
                
                # Cargar archivos de clusters
                self.cluster_files = {int(k): v for k, v in metadata.get('cluster_files', {}).items()}
                
                # Cargar estadísticas
                self.total_vectors = metadata.get('total_vectors', 0)
                self.total_descriptors_processed = metadata.get('total_descriptors_processed', 0)
                
                # Inicializar cluster_files si no existen
                if not self.cluster_files and self.is_trained:
                    for cluster_id in range(self.num_clusters):
                        cluster_file = os.path.join(self.clusters_dir, f'cluster_{cluster_id}.dat')
                        self.cluster_files[cluster_id] = cluster_file
                
                # Poblar self.clusters para compatibilidad
                self._sync_clusters_dict()
                
        except Exception as e:
            print(f"Error cargando metadatos TF-IDF: {e}")
            self._initialize_empty()
    
    def _initialize_empty(self):
        """Inicializa estructuras vacías."""
        self.cluster_idf = {}
        self.cluster_document_count = {}
        self.cluster_centers = None
        self.is_trained = False
        self.tfidf_page_directory = {}
        self.cluster_files = {}
        self.next_tfidf_page_id = 0
        self.total_vectors = 0
        self.total_descriptors_processed = 0
        self.clusters = {}
        self.vector_to_cluster = {}
    
    def save(self):
        """Guarda el índice completo."""
        # Flush páginas TF-IDF dirty
        for page_id in list(self.tfidf_page_cache.keys()):
            self._save_tfidf_page(page_id)
        
        # Flush clusters dirty
        for cluster_id, cluster_data in list(self.cluster_cache.items()):
            if cluster_data['dirty']:
                self._save_cluster_documents(cluster_id, cluster_data['doc_ids'])
                cluster_data['dirty'] = False
        
        # Guardar metadatos
        self.save_metadata()
    
    # ========== MÉTODOS DE UTILIDAD (COMPATIBILIDAD) ==========
    
    def get_vector_count(self):
        """COMPATIBILIDAD: Retorna total de documentos"""
        return self.total_vectors
    
    def get_cluster_count(self):
        """COMPATIBILIDAD: Retorna número de clusters entrenados"""
        return self.num_clusters if self.is_trained else 0
    
    def get_page_count(self):
        """COMPATIBILIDAD: Retorna número de páginas TF-IDF"""
        return len(self.tfidf_page_directory)
    
    def get_cache_info(self):
        """Retorna información sobre el cache."""
        return {
            'tfidf_pages_in_cache': len(self.tfidf_page_cache),
            'cluster_pages_in_cache': len(self.cluster_cache),
            'cache_size_limit': self.cache_size,
            'dirty_tfidf_pages': sum(1 for page_data in self.tfidf_page_cache.values() if page_data['dirty']),
            'dirty_cluster_pages': sum(1 for cluster_data in self.cluster_cache.values() if cluster_data['dirty'])
        }
    
    def clear(self):
        """Limpia todos los datos del índice."""
        # Limpiar caches
        self.tfidf_page_cache.clear()
        self.cluster_cache.clear()
        
        # Eliminar archivos
        if os.path.exists(self.tfidf_vectors_file):
            try:
                os.remove(self.tfidf_vectors_file)
            except Exception as e:
                print(f"Error eliminando archivo TF-IDF: {e}")
        
        # Eliminar archivos de clusters
        for cluster_id in range(self.num_clusters):
            cluster_file = self._get_cluster_file_path(cluster_id)
            if os.path.exists(cluster_file):
                try:
                    os.remove(cluster_file)
                except Exception as e:
                    print(f"Error eliminando cluster {cluster_id}: {e}")
        
        # Reinicializar estructuras
        self._initialize_empty()
        self.save_metadata()
    
    def get_storage_stats(self):
        """Obtiene estadísticas de almacenamiento."""
        stats = {
            'total_documents': self.total_vectors,
            'num_clusters': self.num_clusters,
            'is_trained': self.is_trained,
            'tfidf_pages': len(self.tfidf_page_directory),
            'cluster_files': len(self.cluster_files),
            'tfidf_disk_usage_bytes': 0,
            'clusters_disk_usage_bytes': 0,
            'total_disk_usage_bytes': 0
        }
        
        # Calcular uso de disco TF-IDF
        if os.path.exists(self.tfidf_vectors_file):
            stats['tfidf_disk_usage_bytes'] = os.path.getsize(self.tfidf_vectors_file)
        
        # Calcular uso de disco clusters
        for cluster_id in range(self.num_clusters):
            cluster_file = self._get_cluster_file_path(cluster_id)
            if os.path.exists(cluster_file):
                stats['clusters_disk_usage_bytes'] += os.path.getsize(cluster_file)
        
        stats['total_disk_usage_bytes'] = stats['tfidf_disk_usage_bytes'] + stats['clusters_disk_usage_bytes']
        
        return stats
    
    # ========== MÉTODOS ADICIONALES PARA COMPATIBILIDAD CON MultimediaIndex ==========
    
    def _invalidate_vectors_cache(self):
        """COMPATIBILIDAD: No hace nada en la nueva implementación"""
        pass
    
    def batch_save_metadata(self):
        """COMPATIBILIDAD: Alias para save_metadata"""
        self.save_metadata()
    
    def _assign_to_nearest_cluster(self, vector):
        """
        COMPATIBILIDAD: Asigna un vector al cluster más cercano
        """
        if self.cluster_centers is None:
            return 0
        
        distances = np.linalg.norm(self.cluster_centers - vector, axis=1)
        return np.argmin(distances)
    
    def _get_ordered_clusters(self, query_vector):
        """COMPATIBILIDAD: Obtiene clusters ordenados por distancia"""
        if self.cluster_centers is None:
            return []
        
        cluster_distances = []
        for i, center in enumerate(self.cluster_centers):
            distance = np.linalg.norm(query_vector - center)
            cluster_distances.append((i, distance))
        
        cluster_distances.sort(key=lambda x: x[1])
        return cluster_distances
    
    def compact_pages(self):
        """
        COMPATIBILIDAD: Compacta páginas TF-IDF eliminando espacios vacíos.
        """
        print("Iniciando compactación de páginas TF-IDF...")
        
        # Extraer todos los vectores TF-IDF activos
        active_vectors = []
        for page_id in self.tfidf_page_directory:
            page_data = self._load_tfidf_page(page_id)
            for entry in page_data['vectors'].values():
                if isinstance(entry, dict) and 'id' in entry and 'tfidf_vector' in entry:
                    active_vectors.append((entry['id'], entry['tfidf_vector']))
        
        # Limpiar estructuras
        self.tfidf_page_cache.clear()
        self.tfidf_page_directory = {}
        self.next_tfidf_page_id = 0
        
        # Recrear páginas compactadas
        for doc_id, tfidf_vector in active_vectors:
            self._store_tfidf_vector(doc_id, tfidf_vector)
        
        # Guardar cambios
        self.save()
        print(f"Compactación completada. Páginas TF-IDF activas: {len(self.tfidf_page_directory)}")
    
    def _flush_all_pages(self):
        """COMPATIBILIDAD: Guarda todas las páginas dirty a disco"""
        self.save()