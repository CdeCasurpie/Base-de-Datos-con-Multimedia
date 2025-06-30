import os
import sys
import time
import random
import numpy as np
from database.indexes.vector_index import VectorIndex

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clear_screen():
    """Limpia la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def create_test_vector_index():
    """Crear un índice de vectores de prueba"""
    data_dir = os.path.join(os.getcwd(), "data", "indexes")
    os.makedirs(data_dir, exist_ok=True)
    
    index_file = os.path.join(data_dir, "test_vector_index.pkl")
    metadata_file = os.path.join(data_dir, "test_vector_index_metadata.json")
    
    vector_index = VectorIndex(index_file, metadata_file)
    
    print("Índice de vectores creado")
    print(f"Archivo de índice: {index_file}")
    print(f"Archivo de metadatos: {metadata_file}")
    print(f"Vectores existentes: {vector_index.get_vector_count()}")
    
    return vector_index

RNG = np.random.default_rng()  # O usa np.random.default_rng(42) si quieres reproducibilidad global

def generate_random_vector(dimension=128):
    """Generar un vector aleatorio normalizado"""
    vector = RNG.uniform(-1, 1, dimension)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector

def generate_similar_vector(base_vector, noise_level=0.1):
    """Generar un vector similar al base con un poco de ruido"""
    noise = RNG.normal(0, noise_level, len(base_vector))
    similar_vector = base_vector + noise
    norm = np.linalg.norm(similar_vector)
    if norm > 0:
        similar_vector = similar_vector / norm
    return similar_vector

def print_vector_index_info(vector_index):
    """Mostrar información detallada del índice de vectores"""
    print("\n=== INFORMACIÓN DEL ÍNDICE DE VECTORES ===")
    print(f"Total de vectores: {vector_index.get_vector_count()}")
    print(f"Total de clusters: {vector_index.get_cluster_count()}")
    
    if vector_index.cluster_centers is not None:
        print("Clustering: Habilitado")
        if vector_index.clusters:
            cluster_sizes = [len(vectors) for vectors in vector_index.clusters.values()]
            print(f"Clusters creados: {len(cluster_sizes)}")
            print("Distribución por cluster:")
            for cluster_id, size in enumerate(cluster_sizes):
                print(f"  Cluster {cluster_id}: {size} vectores")
            print(f"Tamaño promedio de cluster: {np.mean(cluster_sizes):.2f}")
            print(f"Desviación estándar: {np.std(cluster_sizes):.2f}")
    else:
        print("Clustering: No habilitado")

def benchmark_search_methods(vector_index, k=5, num_queries=10):
    """Comparar rendimiento entre métodos de búsqueda"""
    if vector_index.get_vector_count() == 0:
        print("Error: No hay vectores para realizar benchmark")
        return
    
    # Obtener dimensión de los vectores
    first_vector = next(iter(vector_index.vectors.values()))
    dimension = len(first_vector)
    
    print("\n=== BENCHMARK DE MÉTODOS DE BÚSQUEDA ===")
    print(f"Parámetros: k={k}, consultas={num_queries}, dimensión={dimension}")
    
    # Generar vectores de consulta aleatorios
    query_vectors = [generate_random_vector(dimension) for _ in range(num_queries)]
    
    # Benchmark búsqueda fuerza bruta
    print("Ejecutando búsqueda por fuerza bruta...")
    start_time = time.time()
    brute_results = []
    for query in query_vectors:
        results = vector_index.search_knn(query, k)
        brute_results.append(results)
    brute_time = time.time() - start_time
    
    # Benchmark búsqueda con índice
    print("Ejecutando búsqueda con índice...")
    start_time = time.time()
    index_results = []
    for query in query_vectors:
        results = vector_index.search_knn_with_index(query, k)
        index_results.append(results)
    index_time = time.time() - start_time
    
    print("\nResultados del benchmark:")
    print(f"Tiempo fuerza bruta: {brute_time*1000:.2f} ms ({brute_time*1000/num_queries:.2f} ms/consulta)")
    print(f"Tiempo con índice: {index_time*1000:.2f} ms ({index_time*1000/num_queries:.2f} ms/consulta)")
    
    if index_time > 0:
        speedup = brute_time / index_time
        print(f"Aceleración: {speedup:.2f}x")
    
    # Verificar exactitud comparando algunos resultados
    accuracy_matches = 0
    for i in range(min(5, num_queries)):
        brute_ids = [r[0] for r in brute_results[i]]
        index_ids = [r[0] for r in index_results[i]]
        if brute_ids == index_ids:
            accuracy_matches += 1
    
    accuracy = accuracy_matches / min(5, num_queries) * 100
    print(f"Exactitud de resultados: {accuracy:.1f}% (primeras {min(5, num_queries)} consultas)")

def print_menu():
    """Mostrar el menú de opciones"""
    print("\n===== MENÚ DE PRUEBAS DEL ÍNDICE DE VECTORES =====")
    print("1. Añadir vector individual")
    print("2. Añadir vectores aleatorios en masa")
    print("3. Buscar vector por ID")
    print("4. Búsqueda KNN (fuerza bruta)")
    print("5. Búsqueda KNN (con índice)")
    print("6. Construir clusters K-means")
    print("7. Eliminar vector por ID")
    print("8. Mostrar información del índice")
    print("9. Benchmark de métodos de búsqueda")
    print("10. Limpiar índice completo")
    print("11. Salir")
    print("==================================================")

def handle_add_vector(vector_index):
    """Maneja la adición de un vector individual"""
    clear_screen()
    print("=== AÑADIR VECTOR INDIVIDUAL ===")
    
    try:
        vector_id = input("ID del vector: ")
        
        if vector_index.get_vector(vector_id) is not None:
            print(f"Error: Ya existe un vector con ID={vector_id}")
            return
        
        dimension = int(input("Dimensión del vector (128 por defecto): ") or "128")
        
        print("Opciones para generar el vector:")
        print("1. Aleatorio")
        print("2. Valores manuales (separados por comas)")
        
        vector_option = input("Seleccione opción (1-2): ")
        
        if vector_option == "2":
            values_input = input(f"Ingrese {dimension} valores separados por comas: ")
            values = [float(x.strip()) for x in values_input.split(',')]
            if len(values) != dimension:
                print(f"Error: Se esperaban {dimension} valores, se recibieron {len(values)}")
                return
            vector = np.array(values)
        else:
            vector = generate_random_vector(dimension)
        
        start_time = time.time()
        vector_index.add_vector(vector_id, vector)
        elapsed_time = time.time() - start_time
        
        print(f"Vector añadido exitosamente en {elapsed_time*1000:.2f} ms")
        print(f"ID: {vector_id}")
        print(f"Dimensión: {len(vector)}")
        print(f"Primeros 5 valores: {vector[:5].tolist()}")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

def handle_add_bulk_vectors(vector_index):
    """Maneja la adición masiva de vectores"""
    clear_screen()
    print("=== AÑADIR VECTORES EN MASA ===")
    
    try:
        count = int(input("Número de vectores a generar: "))
        dimension = int(input("Dimensión de los vectores (128 por defecto): ") or "128")
        
        if count <= 0:
            print("Error: El número de vectores debe ser positivo")
            return
        
        print(f"Generando {count} vectores de {dimension} dimensiones...")
        start_time = time.time()
        
        for i in range(count):
            vector_id = f"vec_{i+1}_{int(time.time()*1000) % 10000}"
            vector = generate_random_vector(dimension)
            vector_index.add_vector(vector_id, vector)
            
            if (i + 1) % 100 == 0:
                print(f"Progreso: {i+1}/{count} vectores añadidos")
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{count} vectores añadidos exitosamente en {elapsed_time:.2f} segundos")
        print(f"Velocidad promedio: {count/elapsed_time:.2f} vectores/segundo")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")

def handle_search_vector(vector_index):
    """Maneja la búsqueda de un vector específico"""
    clear_screen()
    print("=== BUSCAR VECTOR POR ID ===")
    
    vector_id = input("ID del vector a buscar: ")
    
    start_time = time.time()
    vector = vector_index.get_vector(vector_id)
    elapsed_time = time.time() - start_time
    
    if vector is not None:
        print(f"Vector encontrado en {elapsed_time*1000:.2f} ms")
        print(f"ID: {vector_id}")
        print(f"Dimensión: {len(vector)}")
        print(f"Primeros 10 valores: {vector[:10].tolist()}")
        
        cluster_id = vector_index.vector_to_cluster.get(vector_id)
        if cluster_id is not None:
            print(f"Pertenece al cluster: {cluster_id}")
    else:
        print(f"Vector con ID '{vector_id}' no encontrado")

def handle_knn_search(vector_index, use_index=False):
    """Maneja la búsqueda KNN"""
    method_name = "con índice" if use_index else "fuerza bruta"
    clear_screen()
    print(f"=== BÚSQUEDA KNN ({method_name.upper()}) ===")
    
    try:
        if vector_index.get_vector_count() == 0:
            print("Error: No hay vectores en el índice")
            return
        
        k = int(input("Número de vecinos más cercanos (k): "))
        if k <= 0:
            print("Error: k debe ser positivo")
            return
        
        print("Opciones para el vector de consulta:")
        print("1. Usar un vector existente del índice")
        print("2. Generar vector aleatorio")
        print("3. Ingresar valores manualmente")
        
        option = input("Seleccione opción (1-3): ")
        
        if option == "1":
            print("Vectores disponibles:")
            vector_ids = list(vector_index.vectors.keys())
            for i, vid in enumerate(vector_ids[:10]):
                print(f"{i+1}. {vid}")
            if len(vector_ids) > 10:
                print(f"... y {len(vector_ids)-10} más")
            
            selected_id = input("Ingrese el ID del vector: ")
            if selected_id not in vector_index.vectors:
                print(f"Error: Vector '{selected_id}' no encontrado")
                return
            query_vector = vector_index.vectors[selected_id]
            
        elif option == "3":
            first_vector = next(iter(vector_index.vectors.values()))
            dimension = len(first_vector)
            values_input = input(f"Ingrese {dimension} valores separados por comas: ")
            values = [float(x.strip()) for x in values_input.split(',')]
            if len(values) != dimension:
                print(f"Error: Se esperaban {dimension} valores")
                return
            query_vector = np.array(values)
        else:
            first_vector = next(iter(vector_index.vectors.values()))
            dimension = len(first_vector)
            query_vector = generate_random_vector(dimension)
        
        print(f"Vector de consulta (primeros 5 valores): {query_vector[:5].tolist()}")
        
        # Realizar búsqueda
        start_time = time.time()
        if use_index:
            results = vector_index.search_knn_with_index(query_vector, k)
        else:
            results = vector_index.search_knn(query_vector, k)
        elapsed_time = time.time() - start_time
        
        print(f"\nBúsqueda completada en {elapsed_time*1000:.2f} ms")
        print(f"Método: {method_name}")
        print(f"Vecinos encontrados: {len(results)}")
        
        print(f"\nVecinos más cercanos (k={k}):")
        for i, (vid, distance) in enumerate(results):
            print(f"{i+1}. ID: {vid}, Distancia: {distance:.6f}")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

def handle_build_clusters(vector_index):
    """Maneja la construcción de clusters K-means"""
    clear_screen()
    print("=== CONSTRUIR CLUSTERS K-MEANS ===")
    
    try:
        if vector_index.get_vector_count() == 0:
            print("Error: No hay vectores en el índice")
            return
        
        max_clusters = vector_index.get_vector_count()
        num_clusters = int(input(f"Número de clusters (máx {max_clusters}): "))
        
        if num_clusters <= 0 or num_clusters > max_clusters:
            print(f"Error: Número de clusters debe estar entre 1 y {max_clusters}")
            return
        
        print(f"Construyendo {num_clusters} clusters usando K-means...")
        start_time = time.time()
        
        vector_index.build_kmeans_clusters(num_clusters)
        
        elapsed_time = time.time() - start_time
        
        print(f"Clustering completado en {elapsed_time*1000:.2f} ms")
        print(f"Se crearon {vector_index.get_cluster_count()} clusters")
        
        if vector_index.clusters:
            cluster_sizes = [len(vectors) for vectors in vector_index.clusters.values()]
            print(f"Distribución de vectores por cluster: {cluster_sizes}")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except Exception as e:
        print(f"Error durante clustering: {e}")

def handle_remove_vector(vector_index):
    """Maneja la eliminación de un vector"""
    clear_screen()
    print("=== ELIMINAR VECTOR ===")
    
    if vector_index.get_vector_count() == 0:
        print("Error: No hay vectores en el índice")
        return
    
    vector_id = input("ID del vector a eliminar: ")
    
    start_time = time.time()
    success = vector_index.remove_vector(vector_id)
    elapsed_time = time.time() - start_time
    
    if success:
        print(f"Vector '{vector_id}' eliminado exitosamente en {elapsed_time*1000:.2f} ms")
    else:
        print(f"Vector con ID '{vector_id}' no encontrado")

def main():
    clear_screen()
    print("=== PRUEBA DEL ÍNDICE DE VECTORES MULTIMEDIA ===")
    
    vector_index = create_test_vector_index()
    
    while True:
        print_menu()
        option = input("Elija una opción (1-11): ")
        
        if option == "1":
            handle_add_vector(vector_index)
        elif option == "2":
            handle_add_bulk_vectors(vector_index)
        elif option == "3":
            handle_search_vector(vector_index)
        elif option == "4":
            handle_knn_search(vector_index, use_index=False)
        elif option == "5":
            handle_knn_search(vector_index, use_index=True)
        elif option == "6":
            handle_build_clusters(vector_index)
        elif option == "7":
            handle_remove_vector(vector_index)
        elif option == "8":
            clear_screen()
            print_vector_index_info(vector_index)
        elif option == "9":
            try:
                k = int(input("Valor de k para benchmark (5 por defecto): ") or "5")
                queries = int(input("Número de consultas (10 por defecto): ") or "10")
                benchmark_search_methods(vector_index, k, queries)
            except ValueError:
                print("Error: Valores inválidos para benchmark")
        elif option == "10":
            clear_screen()
            confirm = input("¿Está seguro de que desea limpiar todo el índice? (s/N): ")
            if confirm.lower() == 's':
                vector_index.clear()
                print("Índice limpiado exitosamente")
            else:
                print("Operación cancelada")
        elif option == "11":
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida. Por favor, elija una opción del 1 al 11.")
        
        input("\nPresione Enter para continuar...")
        clear_screen()

if __name__ == "__main__":
    main()
