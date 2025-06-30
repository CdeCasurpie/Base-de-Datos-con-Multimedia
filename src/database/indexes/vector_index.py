import os
import json
import numpy as np
from sklearn.cluster import KMeans
import pickle

class VectorIndex:
    """
    Estructura de datos para vectores de características.
    Maneja búsquedas de similitud y clustering.
    """
    
    def __init__(self, index_file, metadata_file):
        self.index_file = index_file
        self.metadata_file = metadata_file
        self.vectors = {}  
        self.clusters = {}  
        self.cluster_centers = None
        self.vector_to_cluster = {} 
        self.load()
        
    def add_vector(self, id, vector):
        """
        Añade un vector al índice
        
        Params:
            id: Identificador único del vector
            vector: Vector de características (numpy array)
        """
        if isinstance(vector, list):
            vector = np.array(vector)
        
        self.vectors[id] = vector.copy()
        
        if self.cluster_centers is not None:
            cluster_id = self._assign_to_nearest_cluster(vector)
            self.vector_to_cluster[id] = cluster_id
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            self.clusters[cluster_id].append(id)
        
        self.save()
        
    def remove_vector(self, id):
        """
        Remueve un vector del índice
        
        Params:
            id: Identificador del vector a remover
            
        Returns:
            bool: True si se removió exitosamente
        """
        if id not in self.vectors:
            return False
            
        del self.vectors[id]
        
        if id in self.vector_to_cluster:
            cluster_id = self.vector_to_cluster[id]
            if cluster_id in self.clusters and id in self.clusters[cluster_id]:
                self.clusters[cluster_id].remove(id)
            del self.vector_to_cluster[id]
        
        self.save()
        return True
        
    def search_knn(self, query_vector, k=5):
        """
        Búsqueda KNN sin usar clustering (fuerza bruta)
        
        Params:
            query_vector: Vector de consulta
            k: Número de vecinos más cercanos
            
        Returns:
            list: Lista de tuplas (id, distancia) ordenadas por distancia
        """
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)
            
        if not self.vectors:
            return []
        
        distances = []
        for vector_id, vector in self.vectors.items():
            distance = self.compute_distance(query_vector, vector)
            distances.append((vector_id, distance))
        
        distances.sort(key=lambda x: x[1])
        return distances[:k]
        
    def search_knn_with_index(self, query_vector, k=5):
        """
        Búsqueda KNN usando clustering para acelerar la búsqueda
        
        Params:
            query_vector: Vector de consulta
            k: Número de vecinos más cercanos
            
        Returns:
            list: Lista de tuplas (id, distancia) ordenadas por distancia
        """
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)
            
        if not self.vectors or self.cluster_centers is None:
            return self.search_knn(query_vector, k)
        
        # Obtener clusters ordenados por distancia
        cluster_distances = self._get_ordered_clusters(query_vector)
        
        # Buscar candidatos en clusters cercanos
        candidates = self._search_in_clusters(query_vector, cluster_distances, k)
        
        # Si no hay suficientes candidatos, usar búsqueda completa
        if len(candidates) < k:
            return self.search_knn(query_vector, k)
        
        # Ordenar candidatos y tomar los k mejores
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
                cluster_candidates = self._get_cluster_candidates(query_vector, cluster_id)
                candidates.extend(cluster_candidates)
            
            searched_clusters += 1
        
        return candidates
    
    def _get_cluster_candidates(self, query_vector, cluster_id):
        """Obtiene candidatos de un cluster específico"""
        candidates = []
        for vector_id in self.clusters[cluster_id]:
            if vector_id in self.vectors:
                distance = self.compute_distance(query_vector, self.vectors[vector_id])
                candidates.append((vector_id, distance))
        return candidates
        
    def build_kmeans_clusters(self, num_clusters=10):
        """
        Construye clusters usando K-means
        
        Params:
            num_clusters: Número de clusters a crear
        """
        if len(self.vectors) < num_clusters:
            num_clusters = max(1, len(self.vectors))
        
        if not self.vectors:
            return
        
        vector_ids = list(self.vectors.keys())
        vector_data = np.array([self.vectors[id] for id in vector_ids])
        
        if len(np.unique(vector_data, axis=0)) < num_clusters:
            print(f"Advertencia: Los vectores tienen poca variación. Reduciendo clusters a {len(np.unique(vector_data, axis=0))}")
            num_clusters = max(1, len(np.unique(vector_data, axis=0)))
        
        # Aplicar K-means con manejo de errores
        try:
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(vector_data)
            
            self.cluster_centers = kmeans.cluster_centers_
            
            self.clusters = {}
            self.vector_to_cluster = {}
            
            for i, vector_id in enumerate(vector_ids):
                cluster_id = int(cluster_labels[i])  
                self.vector_to_cluster[vector_id] = cluster_id
                
                if cluster_id not in self.clusters:
                    self.clusters[cluster_id] = []
                self.clusters[cluster_id].append(vector_id)
            
            self.save()
            
        except Exception as e:
            print(f"Error durante clustering: {e}")
            self.clusters = {0: vector_ids}
            self.vector_to_cluster = dict.fromkeys(vector_ids, 0)
            self.cluster_centers = np.array([np.mean(vector_data, axis=0)]) if len(vector_data) > 0 else None
            self.save()
        
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
        Guarda el índice en archivos
        """
        try:
            os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            
            with open(self.index_file, 'wb') as f:
                pickle.dump(self.vectors, f)
            
            # Guardar metadata como JSON
            metadata = {
                'clusters': {str(k): v for k, v in self.clusters.items()},
                'vector_to_cluster': {str(k): int(v) if isinstance(v, np.integer) else v for k, v in self.vector_to_cluster.items()},
                'cluster_centers': self.cluster_centers.tolist() if self.cluster_centers is not None else None,
                'vector_count': len(self.vectors)
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Error al guardar índice de vectores: {e}")
        
    def load(self):
        """
        Carga el índice desde archivos
        """
        try:
            # Cargar vectores
            if os.path.exists(self.index_file):
                with open(self.index_file, 'rb') as f:
                    self.vectors = pickle.load(f)
            
            # Cargar metadata
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Convertir claves de string a int para clusters
                self.clusters = {int(k): v for k, v in metadata.get('clusters', {}).items()}
                vector_to_cluster_raw = metadata.get('vector_to_cluster', {})
                self.vector_to_cluster = {}
                for k, v in vector_to_cluster_raw.items():
                    # Intentar convertir la clave a int si es posible
                    try:
                        key = int(k)
                    except (ValueError, TypeError):
                        key = k
                    self.vector_to_cluster[key] = int(v) if isinstance(v, (int, float, str)) and str(v).isdigit() else v
                
                cluster_centers_data = metadata.get('cluster_centers')
                if cluster_centers_data:
                    self.cluster_centers = np.array(cluster_centers_data)
                else:
                    self.cluster_centers = None
                    
        except Exception as e:
            print(f"Error al cargar índice de vectores: {e}")
            self.vectors = {}
            self.clusters = {}
            self.vector_to_cluster = {}
            self.cluster_centers = None
        
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
        return len(self.vectors)
    
    def get_cluster_count(self):
        """
        Retorna el número de clusters
        
        Returns:
            int: Número de clusters
        """
        return len(self.clusters)
    
    def get_vector(self, id):
        """
        Obtiene un vector por su ID
        
        Params:
            id: Identificador del vector
            
        Returns:
            numpy.ndarray: Vector o None si no existe
        """
        return self.vectors.get(id)
    
    def clear(self):
        """
        Limpia todos los datos del índice
        """
        self.vectors = {}
        self.clusters = {}
        self.vector_to_cluster = {}
        self.cluster_centers = None
        self.save()