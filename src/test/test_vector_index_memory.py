import numpy as np
import psutil
import os
import tempfile
from ..database.indexes.vector_index import VectorIndex

def test_vector_index_memory_and_knn():
    # Configuración
    N = 10000  # Número de vectores
    D = 32     # Dimensión de cada vector
    K = 5      # Vecinos a buscar
    np.random.seed(42)
    process = psutil.Process(os.getpid())

    with tempfile.TemporaryDirectory() as tmpdir:
        idx_file = os.path.join(tmpdir, "test_index.pkl")
        meta_file = os.path.join(tmpdir, "test_meta.json")
        vi = VectorIndex(idx_file, meta_file, page_size=100, cache_size=5)

        # Insertar N vectores
        for i in range(N):
            vec = np.random.rand(D).astype(np.float32)
            vi.add_vector(f"id_{i}", vec)
            if i % 1000 == 0:
                print(f"Insertados: {i}")

        # Medir memoria tras inserción
        mem_after_insert = process.memory_info().rss / (1024 * 1024)
        print(f"Memoria tras insertar {N} vectores: {mem_after_insert:.2f} MB")

        # Construir clusters
        vi.build_kmeans_clusters(num_clusters=10)
        print(f"Clusters construidos: {vi.get_cluster_count()}")

        # Búsqueda KNN
        query = np.random.rand(D).astype(np.float32)
        results = vi.search_knn_with_index(query, k=K)
        print(f"Resultados KNN: {results}")

        # Medir memoria tras búsquedas
        mem_after_search = process.memory_info().rss / (1024 * 1024)
        print(f"Memoria tras búsquedas: {mem_after_search:.2f} MB")

        # Asegurar que la memoria no crece linealmente con N
        assert mem_after_insert < 200, "Uso de memoria excesivo tras inserción"
        assert mem_after_search < 220, "Uso de memoria excesivo tras búsquedas"
        assert len(results) == K, "KNN no retorna K resultados"


def test_vector_index_robustness():
    # Configuración robusta
    N = 100000  # Número de vectores
    D = 32      # Dimensión
    K = 10      # Vecinos a buscar
    REMOVE = 10000  # Vectores a borrar
    np.random.seed(123)
    process = psutil.Process(os.getpid())

    with tempfile.TemporaryDirectory() as tmpdir:
        idx_file = os.path.join(tmpdir, "robust_index.pkl")
        meta_file = os.path.join(tmpdir, "robust_meta.json")
        vi = VectorIndex(idx_file, meta_file, page_size=200, cache_size=8)

        # Insertar N vectores
        for i in range(N):
            vec = np.random.rand(D).astype(np.float32)
            vi.add_vector(f"id_{i}", vec)
            if i % 10000 == 0:
                print(f"[ROBUST] Insertados: {i}")

        mem_after_insert = process.memory_info().rss / (1024 * 1024)
        print(f"[ROBUST] Memoria tras insertar {N}: {mem_after_insert:.2f} MB")

        # Borrado aleatorio
        to_remove = np.random.choice([f"id_{i}" for i in range(N)], size=REMOVE, replace=False)
        for idx, vid in enumerate(to_remove):
            vi.remove_vector(vid)
            if idx % 2000 == 0:
                print(f"[ROBUST] Borrados: {idx}")

        print(f"[ROBUST] Vectores tras borrado: {vi.get_vector_count()}")

        # Compactar páginas
        vi.compact_pages()
        stats = vi.get_storage_stats()
        print(f"[ROBUST] Stats tras compactar: {stats}")

        # Guardar y recargar
        vi.save()
        del vi
        vi = VectorIndex(idx_file, meta_file, page_size=200, cache_size=8)
        print(f"[ROBUST] Recargado. Vectores: {vi.get_vector_count()} Páginas: {vi.get_page_count()}")

        # Clustering y KNN
        vi.build_kmeans_clusters(num_clusters=20)
        print(f"[ROBUST] Clusters: {vi.get_cluster_count()}")
        query = np.random.rand(D).astype(np.float32)
        results = vi.search_knn_with_index(query, k=K)
        print(f"[ROBUST] KNN: {results}")

        mem_after_search = process.memory_info().rss / (1024 * 1024)
        print(f"[ROBUST] Memoria tras búsquedas: {mem_after_search:.2f} MB")

        # Fragmentación y aserciones
        assert stats['fragmentation_ratio'] < 0.2, "Fragmentación excesiva tras compactar"
        assert mem_after_insert < 400, "Uso de memoria excesivo tras inserción masiva"
        assert mem_after_search < 450, "Uso de memoria excesivo tras búsquedas"
        assert len(results) == K, "KNN no retorna K resultados"
        assert vi.get_vector_count() == N - REMOVE, "Conteo de vectores incorrecto tras borrado"

if __name__ == "__main__":
    test_vector_index_memory_and_knn()
    print("\n--- TEST ROBUSTEZ ---\n")
    test_vector_index_robustness()