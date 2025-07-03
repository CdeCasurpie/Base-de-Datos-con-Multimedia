import numpy as np
import sys
import os
import time
import random

# Agregar el directorio src al path de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)  # Va de test/ a src/
project_root = os.path.dirname(src_dir)  # Va de src/ a raíz del proyecto
sys.path.insert(0, src_dir)
sys.path.insert(0, project_root)

print(f"Directorio actual: {current_dir}")
print(f"Directorio src: {src_dir}")
print(f"Directorio proyecto: {project_root}")

try:
    from database.indexes.vector_index import VectorIndex
    print("✓ VectorIndex importado exitosamente")
except ImportError as e:
    print(f"✗ Error importando VectorIndex: {e}")
    print("Verificando estructura de directorios...")
    vector_index_path = os.path.join(src_dir, 'database', 'indexes', 'vector_index.py')
    print(f"Buscando: {vector_index_path}")
    print(f"Existe: {os.path.exists(vector_index_path)}")
    sys.exit(1)

def clear_screen():
    """Limpia la pantalla de la consola"""
    os.system('cls' if os.name == 'nt' else 'clear')

def create_test_vector_index():
    """Crear un índice de vectores de prueba con paginación"""
    data_dir = os.path.join(os.getcwd(), "data", "indexes")
    os.makedirs(data_dir, exist_ok=True)
    
    index_file = os.path.join(data_dir, "test_vector_index.pkl")
    metadata_file = os.path.join(data_dir, "test_vector_index_metadata.json")
    
    # Configuración para demostrar paginación - páginas pequeñas
    page_size = 10  # Solo 10 vectores por página
    cache_size = 5  # Solo 5 páginas en cache
    
    vector_index = VectorIndex(index_file, metadata_file, page_size=page_size, cache_size=cache_size)
    
    print("Índice de vectores con paginación creado")
    print(f"Archivo de índice: {index_file}")
    print(f"Archivo de metadatos: {metadata_file}")
    print(f"Configuración de paginación: {page_size} vectores/página, {cache_size} páginas en cache")
    print(f"Vectores existentes: {vector_index.get_vector_count()}")
    print(f"Páginas existentes: {vector_index.get_page_count()}")
    
    return vector_index

RNG = np.random.default_rng()  # O usa np.random.default_rng(42) si quieres reproducibilidad global

def get_vector_dimension(vector_index):
    """Obtener la dimensión de los vectores en el índice, o None si está vacío"""
    vector_ids = list(vector_index.vector_index.keys())
    if not vector_ids:
        return None
    
    first_vector = vector_index.get_vector(vector_ids[0])
    return len(first_vector) if first_vector is not None else None

def validate_vector_dimensions(vector_index):
    """Validar que todos los vectores en el índice tengan la misma dimensión"""
    vector_ids = list(vector_index.vector_index.keys())
    if len(vector_ids) < 2:
        return True, None  # Un vector o ninguno, no hay conflicto
    
    dimensions = set()
    for vid in vector_ids[:10]:  # Revisar primeros 10 para eficiencia
        vector = vector_index.get_vector(vid)
        if vector is not None:
            dimensions.add(len(vector))
    
    if len(dimensions) > 1:
        return False, f"Dimensiones inconsistentes encontradas: {sorted(dimensions)}"
    
    return True, None

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
    """Mostrar información detallada del índice de vectores con información de paginación"""
    print("\n=== INFORMACIÓN DEL ÍNDICE DE VECTORES CON PAGINACIÓN ===")
    print(f"Total de vectores: {vector_index.get_vector_count()}")
    print(f"Total de páginas: {vector_index.get_page_count()}")
    print(f"Total de clusters: {vector_index.get_cluster_count()}")
    
    # Información de dimensiones
    current_dim = get_vector_dimension(vector_index)
    if current_dim is not None:
        print(f"Dimensión de vectores: {current_dim}")
        is_valid, error_msg = validate_vector_dimensions(vector_index)
        if not is_valid:
            print(f"⚠️  {error_msg}")
    else:
        print("Dimensión de vectores: N/A (índice vacío)")
    
    # Información específica de paginación
    stats = vector_index.get_storage_stats()
    cache_info = vector_index.get_cache_info()
    
    print("--- Estadísticas de Paginación ---")
    print(f"Vectores por página (promedio): {stats['average_vectors_per_page']:.2f}")
    print(f"Fragmentación: {stats['fragmentation_ratio']:.2%}")
    print(f"Páginas en cache: {cache_info['pages_in_cache']}/{cache_info['cache_size_limit']}")
    print(f"Páginas dirty (sin guardar): {cache_info['dirty_pages']}")
    print(f"Uso de disco: {stats['disk_usage_bytes']} bytes")
    
    if vector_index.cluster_centers is not None:
        print("\n--- Clustering ---")
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
        print("\n--- Clustering ---")
        print("Clustering: No habilitado")

def benchmark_search_methods(vector_index, k=5, num_queries=10):
    """Comparar rendimiento entre métodos de búsqueda con información de paginación"""
    if vector_index.get_vector_count() == 0:
        print("Error: No hay vectores para realizar benchmark")
        return
    
    # Obtener dimensión de los vectores
    vector_ids = list(vector_index.vector_index.keys())
    if not vector_ids:
        print("Error: No hay vectores disponibles")
        return
    
    first_vector = vector_index.get_vector(vector_ids[0])
    dimension = len(first_vector)
    
    print("\n=== BENCHMARK DE MÉTODOS DE BÚSQUEDA CON PAGINACIÓN ===")
    print(f"Parámetros: k={k}, consultas={num_queries}, dimensión={dimension}")
    
    # Mostrar estado inicial del cache
    initial_cache_info = vector_index.get_cache_info()
    print(f"Estado inicial del cache: {initial_cache_info['pages_in_cache']} páginas")
    
    # Generar vectores de consulta aleatorios
    query_vectors = [generate_random_vector(dimension) for _ in range(num_queries)]
    
    # Benchmark búsqueda fuerza bruta
    print("\nEjecutando búsqueda por fuerza bruta (acceso paginado)...")
    start_time = time.time()
    brute_results = []
    for query in query_vectors:
        results = vector_index.search_knn(query, k)
        brute_results.append(results)
    brute_time = time.time() - start_time
    
    # Verificar accesos a páginas
    brute_cache_info = vector_index.get_cache_info()
    print(f"Páginas en cache después de fuerza bruta: {brute_cache_info['pages_in_cache']}")
    
    # Benchmark búsqueda con índice
    print("Ejecutando búsqueda con índice (clustering + paginación)...")
    start_time = time.time()
    index_results = []
    for query in query_vectors:
        results = vector_index.search_knn_with_index(query, k)
        index_results.append(results)
    index_time = time.time() - start_time
    
    # Verificar accesos a páginas después del índice
    index_cache_info = vector_index.get_cache_info()
    print(f"Páginas en cache después de búsqueda indexada: {index_cache_info['pages_in_cache']}")
    
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
    """Mostrar el menú de opciones con funciones específicas de paginación"""
    print("\n===== MENÚ DE PRUEBAS DEL ÍNDICE DE VECTORES CON PAGINACIÓN =====")
    print("1. Añadir vector individual")
    print("2. Añadir vectores aleatorios en masa")
    print("3. Buscar vector por ID")
    print("4. Búsqueda KNN (fuerza bruta)")
    print("5. Búsqueda KNN (con índice)")
    print("6. Construir clusters K-means")
    print("7. Eliminar vector por ID")
    print("8. Mostrar información del índice (incluye paginación)")
    print("9. Benchmark de métodos de búsqueda")
    print("10. Limpiar índice completo")
    print("11. Compactar páginas (optimizar almacenamiento)")
    print("12. Mostrar estadísticas detalladas de almacenamiento")
    print("13. Test de carga masiva (demostrar paginación)")
    print("14. Salir")
    print("================================================================")

def handle_add_vector(vector_index):
    """Maneja la adición de un vector individual"""
    clear_screen()
    print("=== AÑADIR VECTOR INDIVIDUAL ===")
    
    # Detectar dimensión existente
    current_dim = get_vector_dimension(vector_index)
    
    try:
        vector_id = input("ID del vector: ")
        
        if vector_index.get_vector(vector_id) is not None:
            print(f"Error: Ya existe un vector con ID={vector_id}")
            return
        
        if current_dim is not None:
            print(f"Dimensión detectada en el índice: {current_dim}")
            use_detected = input(f"¿Usar dimensión {current_dim}? (s/N): ").lower()
            if use_detected == 's':
                dimension = current_dim
            else:
                dimension = int(input("Dimensión del vector: "))
                print(f"⚠️  ADVERTENCIA: Vas a añadir un vector de dimensión {dimension}")
                print(f"   pero el índice ya contiene vectores de dimensión {current_dim}")
                print("   Esto causará errores en búsquedas KNN.")
                continue_anyway = input("¿Continuar de todas formas? (s/N): ").lower()
                if continue_anyway != 's':
                    print("Operación cancelada.")
                    return
        else:
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
        
        # Mostrar estado del cache antes de añadir
        cache_before = vector_index.get_cache_info()
        print(f"Cache antes: {cache_before['pages_in_cache']} páginas")
        
        start_time = time.time()
        vector_index.add_vector(vector_id, vector)
        elapsed_time = time.time() - start_time
        
        # Mostrar estado después de añadir
        cache_after = vector_index.get_cache_info()
        stats = vector_index.get_storage_stats()
        
        print(f"Vector añadido exitosamente en {elapsed_time*1000:.2f} ms")
        print(f"ID: {vector_id}")
        print(f"Dimensión: {len(vector)}")
        print(f"Primeros 5 valores: {vector[:5].tolist()}")
        print(f"Cache después: {cache_after['pages_in_cache']} páginas")
        print(f"Total páginas: {stats['total_pages']}")
        print(f"Fragmentación: {stats['fragmentation_ratio']:.2%}")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

def handle_add_bulk_vectors(vector_index):
    """Maneja la adición masiva de vectores mostrando el efecto de paginación"""
    clear_screen()
    print("=== AÑADIR VECTORES EN MASA (DEMOSTRACIÓN DE PAGINACIÓN) ===")
    
    # Detectar dimensión existente o usar default
    current_dim = get_vector_dimension(vector_index)
    
    try:
        count = int(input("Número de vectores a generar: "))
        
        if current_dim is not None:
            print(f"Dimensión detectada en el índice: {current_dim}")
            use_detected = input(f"¿Usar dimensión {current_dim}? (s/N): ").lower()
            if use_detected == 's':
                dimension = current_dim
            else:
                dimension = int(input("Dimensión de los vectores: "))
        else:
            dimension = int(input("Dimensión de los vectores (128 por defecto): ") or "128")
        
        if count <= 0:
            print("Error: El número de vectores debe ser positivo")
            return
        
        # Validar compatibilidad de dimensiones
        if current_dim is not None and dimension != current_dim:
            print(f"⚠️  ADVERTENCIA: Vas a añadir vectores de dimensión {dimension}")
            print(f"   pero el índice ya contiene vectores de dimensión {current_dim}")
            print("   Esto causará errores en búsquedas KNN.")
            continue_anyway = input("¿Continuar de todas formas? (s/N): ").lower()
            if continue_anyway != 's':
                print("Operación cancelada.")
                return
        
        print(f"Generando {count} vectores de {dimension} dimensiones...")
        print("Monitoreo de paginación en tiempo real:")
        
        initial_stats = vector_index.get_storage_stats()
        print(f"Estado inicial - Vectores: {initial_stats['total_vectors']}, Páginas: {initial_stats['total_pages']}")
        
        start_time = time.time()
        
        for i in range(count):
            vector_id = f"vec_{i+1}_{int(time.time()*1000) % 10000}"
            vector = generate_random_vector(dimension)
            vector_index.add_vector(vector_id, vector)
            
            # Mostrar progreso cada 10 vectores para observar paginación
            if (i + 1) % 10 == 0:
                stats = vector_index.get_storage_stats()
                cache_info = vector_index.get_cache_info()
                print(f"  {i+1}/{count} - Páginas: {stats['total_pages']}, "
                      f"Cache: {cache_info['pages_in_cache']}/{cache_info['cache_size_limit']}, "
                      f"Fragmentación: {stats['fragmentation_ratio']:.1%}")
        
        elapsed_time = time.time() - start_time
        final_stats = vector_index.get_storage_stats()
        
        print(f"\n{count} vectores añadidos exitosamente en {elapsed_time:.2f} segundos")
        print(f"Velocidad promedio: {count/elapsed_time:.2f} vectores/segundo")
        print(f"Páginas creadas: {final_stats['total_pages'] - initial_stats['total_pages']}")
        print(f"Uso de disco: {final_stats['disk_usage_bytes']} bytes")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")

def handle_search_vector(vector_index):
    """Maneja la búsqueda de un vector específico mostrando info de paginación"""
    clear_screen()
    print("=== BUSCAR VECTOR POR ID (CON INFO DE PAGINACIÓN) ===")
    
    vector_id = input("ID del vector a buscar: ")
    
    # Mostrar estado del cache antes de la búsqueda
    cache_before = vector_index.get_cache_info()
    print(f"Cache antes de la búsqueda: {cache_before['pages_in_cache']} páginas")
    
    start_time = time.time()
    vector = vector_index.get_vector(vector_id)
    elapsed_time = time.time() - start_time
    
    cache_after = vector_index.get_cache_info()
    
    if vector is not None:
        print(f"Vector encontrado en {elapsed_time*1000:.2f} ms")
        print(f"ID: {vector_id}")
        print(f"Dimensión: {len(vector)}")
        print(f"Primeros 10 valores: {vector[:10].tolist()}")
        print(f"Cache después: {cache_after['pages_in_cache']} páginas")
        
        # Mostrar información de ubicación en página
        if vector_id in vector_index.vector_index:
            page_id, position = vector_index.vector_index[vector_id]
            print(f"Ubicación: Página {page_id}, Posición {position}")
        
        cluster_id = vector_index.vector_to_cluster.get(vector_id)
        if cluster_id is not None:
            print(f"Pertenece al cluster: {cluster_id}")
    else:
        print(f"Vector con ID '{vector_id}' no encontrado")
        print(f"Cache después de búsqueda fallida: {cache_after['pages_in_cache']} páginas")

def handle_knn_search(vector_index, use_index=False):
    """Maneja la búsqueda KNN mostrando accesos a páginas"""
    method_name = "con índice" if use_index else "fuerza bruta"
    clear_screen()
    print(f"=== BÚSQUEDA KNN ({method_name.upper()}) CON MONITOREO DE PÁGINAS ===")
    
    try:
        if vector_index.get_vector_count() == 0:
            print("Error: No hay vectores en el índice")
            return
        
        # Validar dimensiones antes de continuar
        is_valid, error_msg = validate_vector_dimensions(vector_index)
        if not is_valid:
            print(f"❌ ERROR: {error_msg}")
            print("   Las búsquedas KNN no funcionarán correctamente con dimensiones mixtas.")
            print("   Recomendación: Limpiar el índice y añadir vectores de la misma dimensión.")
            return
        
        # Obtener dimensión de vectores existentes
        current_dim = get_vector_dimension(vector_index)
        if current_dim is None:
            print("Error: No se pudo determinar la dimensión de los vectores")
            return
        
        k = int(input("Número de vecinos más cercanos (k): "))
        if k <= 0:
            print("Error: k debe ser positivo")
            return
        
        print(f"Vectores en el índice tienen dimensión: {current_dim}")
        print("Opciones para el vector de consulta:")
        print("1. Usar un vector existente del índice")
        print("2. Generar vector aleatorio")
        print("3. Ingresar valores manualmente")
        
        option = input("Seleccione opción (1-3): ")
        
        if option == "1":
            print("Vectores disponibles:")
            vector_ids = list(vector_index.vector_index.keys())
            for i, vid in enumerate(vector_ids[:10]):
                print(f"{i+1}. {vid}")
            if len(vector_ids) > 10:
                print(f"... y {len(vector_ids)-10} más")
            
            selected_id = input("Ingrese el ID del vector: ")
            if selected_id not in vector_index.vector_index:
                print(f"Error: Vector '{selected_id}' no encontrado")
                return
            query_vector = vector_index.get_vector(selected_id)
            
        elif option == "3":
            values_input = input(f"Ingrese {current_dim} valores separados por comas: ")
            values = [float(x.strip()) for x in values_input.split(',')]
            if len(values) != current_dim:
                print(f"Error: Se esperaban {current_dim} valores, se recibieron {len(values)}")
                return
            query_vector = np.array(values)
        else:
            # Generar vector aleatorio con la dimensión correcta
            query_vector = generate_random_vector(current_dim)
        
        print(f"Vector de consulta (dimensión {len(query_vector)}, primeros 5 valores): {query_vector[:5].tolist()}")
        
        # Mostrar estado del cache antes de la búsqueda
        cache_before = vector_index.get_cache_info()
        print(f"Cache antes de la búsqueda: {cache_before['pages_in_cache']} páginas")
        
        # Realizar búsqueda
        start_time = time.time()
        if use_index:
            results = vector_index.search_knn_with_index(query_vector, k)
        else:
            results = vector_index.search_knn(query_vector, k)
        elapsed_time = time.time() - start_time
        
        cache_after = vector_index.get_cache_info()
        
        print(f"\nBúsqueda completada en {elapsed_time*1000:.2f} ms")
        print(f"Método: {method_name}")
        print(f"Vecinos encontrados: {len(results)}")
        print(f"Cache después: {cache_after['pages_in_cache']} páginas")
        print(f"Páginas dirty: {cache_after['dirty_pages']}")
        
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
    print("=== CONSTRUIR CLUSTERS K-MEANS CON PAGINACIÓN ===")
    
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
        print("NOTA: Este proceso carga todos los vectores para el clustering")
        
        cache_before = vector_index.get_cache_info()
        print(f"Cache antes: {cache_before['pages_in_cache']} páginas")
        
        start_time = time.time()
        vector_index.build_kmeans_clusters(num_clusters)
        elapsed_time = time.time() - start_time
        
        cache_after = vector_index.get_cache_info()
        
        print(f"Clustering completado en {elapsed_time*1000:.2f} ms")
        print(f"Se crearon {vector_index.get_cluster_count()} clusters")
        print(f"Cache después: {cache_after['pages_in_cache']} páginas")
        
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
    print("=== ELIMINAR VECTOR (CON MONITOREO DE FRAGMENTACIÓN) ===")
    
    if vector_index.get_vector_count() == 0:
        print("Error: No hay vectores en el índice")
        return
    
    vector_id = input("ID del vector a eliminar: ")
    
    stats_before = vector_index.get_storage_stats()
    print(f"Antes - Fragmentación: {stats_before['fragmentation_ratio']:.2%}")
    
    start_time = time.time()
    success = vector_index.remove_vector(vector_id)
    elapsed_time = time.time() - start_time
    
    if success:
        stats_after = vector_index.get_storage_stats()
        print(f"Vector '{vector_id}' eliminado exitosamente en {elapsed_time*1000:.2f} ms")
        print(f"Después - Fragmentación: {stats_after['fragmentation_ratio']:.2%}")
        print(f"Vectores restantes: {stats_after['total_vectors']}")
        
        if stats_after['fragmentation_ratio'] > 0.3:  # 30% fragmentación
            print("⚠ Alta fragmentación detectada. Considere ejecutar compactación (opción 11)")
    else:
        print(f"Vector con ID '{vector_id}' no encontrado")

def handle_compact_pages(vector_index):
    """Maneja la compactación de páginas"""
    clear_screen()
    print("=== COMPACTACIÓN DE PÁGINAS ===")
    
    if vector_index.get_vector_count() == 0:
        print("Error: No hay vectores en el índice")
        return
    
    stats_before = vector_index.get_storage_stats()
    print("Estado antes de la compactación:")
    print(f"  Páginas: {stats_before['total_pages']}")
    print(f"  Fragmentación: {stats_before['fragmentation_ratio']:.2%}")
    print(f"  Uso de disco: {stats_before['disk_usage_bytes']} bytes")
    
    confirm = input("\n¿Proceder con la compactación? (s/N): ")
    if confirm.lower() != 's':
        print("Compactación cancelada")
        return
    
    print("Iniciando compactación...")
    start_time = time.time()
    vector_index.compact_pages()
    elapsed_time = time.time() - start_time
    
    stats_after = vector_index.get_storage_stats()
    
    print(f"Compactación completada en {elapsed_time:.2f} segundos")
    print("\nEstado después de la compactación:")
    print(f"  Páginas: {stats_after['total_pages']} (antes: {stats_before['total_pages']})")
    print(f"  Fragmentación: {stats_after['fragmentation_ratio']:.2%} (antes: {stats_before['fragmentation_ratio']:.2%})")
    print(f"  Uso de disco: {stats_after['disk_usage_bytes']} bytes (antes: {stats_before['disk_usage_bytes']} bytes)")
    
    pages_saved = stats_before['total_pages'] - stats_after['total_pages']
    if pages_saved > 0:
        print(f"✓ {pages_saved} páginas eliminadas")
    else:
        print("• No se eliminaron páginas (poca fragmentación)")

def handle_storage_stats(vector_index):
    """Muestra estadísticas detalladas de almacenamiento"""
    clear_screen()
    print("=== ESTADÍSTICAS DETALLADAS DE ALMACENAMIENTO ===")
    
    stats = vector_index.get_storage_stats()
    cache_info = vector_index.get_cache_info()
    
    print("Vectores y Páginas:")
    print(f"  Total vectores: {stats['total_vectors']}")
    print(f"  Total páginas: {stats['total_pages']}")
    print(f"  Vectores por página (promedio): {stats['average_vectors_per_page']:.2f}")
    print(f"  Fragmentación: {stats['fragmentation_ratio']:.2%}")
    
    print("\nAlmacenamiento:")
    print(f"  Uso de disco: {stats['disk_usage_bytes']} bytes ({stats['disk_usage_bytes']/1024:.2f} KB)")
    
    print("\nCache en Memoria:")
    print(f"  Páginas en cache: {cache_info['pages_in_cache']}/{cache_info['cache_size_limit']}")
    print(f"  Páginas dirty (sin guardar): {cache_info['dirty_pages']}")
    
    if cache_info['pages_in_cache'] == cache_info['cache_size_limit']:
        print("  ⚠ Cache completo - próximas cargas causarán evictions")
    
    print("\nEficiencia:")
    if stats['total_vectors'] > 0:
        bytes_per_vector = stats['disk_usage_bytes'] / stats['total_vectors']
        print(f"  Bytes por vector: {bytes_per_vector:.2f}")
    
    if stats['fragmentation_ratio'] > 0.5:
        print("  ⚠ Alta fragmentación - considere compactación")
    elif stats['fragmentation_ratio'] > 0.3:
        print("  • Fragmentación moderada")
    else:
        print("  ✓ Baja fragmentación")

def handle_mass_load_test(vector_index):
    """Test de carga masiva para demostrar paginación"""
    clear_screen()
    print("=== TEST DE CARGA MASIVA (DEMOSTRACIÓN DE PAGINACIÓN) ===")
    
    try:
        num_vectors = int(input("Número de vectores a cargar (sugerido: 100-500): "))
        dimension = int(input("Dimensión de vectores (sugerido: 64): ") or "64")
        
        if num_vectors <= 0:
            print("Error: Número debe ser positivo")
            return
        
        print(f"\nCargando {num_vectors} vectores de {dimension} dimensiones...")
        print("Monitoreo detallado de paginación:\n")
        
        start_time = time.time()
        
        for i in range(num_vectors):
            vector_id = f"test_{i:06d}"
            vector = generate_random_vector(dimension)
            vector_index.add_vector(vector_id, vector)
            
            # Reporte cada 25 vectores
            if (i + 1) % 25 == 0:
                elapsed = time.time() - start_time
                stats = vector_index.get_storage_stats()
                cache_info = vector_index.get_cache_info()
                
                print(f"[{i+1:4d}/{num_vectors}] "
                      f"Páginas: {stats['total_pages']:3d}, "
                      f"Cache: {cache_info['pages_in_cache']}/{cache_info['cache_size_limit']}, "
                      f"Fragmentación: {stats['fragmentation_ratio']:5.1%}, "
                      f"Velocidad: {(i+1)/elapsed:6.1f} vec/s")
        
        total_time = time.time() - start_time
        final_stats = vector_index.get_storage_stats()
        
        print("=== RESUMEN DE CARGA MASIVA ===")
        print(f"Vectores cargados: {num_vectors}")
        print(f"Tiempo total: {total_time:.2f} segundos")
        print(f"Velocidad promedio: {num_vectors/total_time:.1f} vectores/segundo")
        print(f"Páginas creadas: {final_stats['total_pages']}")
        print(f"Uso de disco: {final_stats['disk_usage_bytes']/1024:.2f} KB")
        print(f"Fragmentación final: {final_stats['fragmentation_ratio']:.2%}")
        
        # Test de búsqueda rápida
        print("\nPrueba de búsqueda rápida:")
        query_vector = generate_random_vector(dimension)
        search_start = time.time()
        results = vector_index.search_knn(query_vector, k=5)
        search_time = time.time() - search_start
        
        print(f"Búsqueda KNN completada en {search_time*1000:.2f} ms")
        print(f"Resultados encontrados: {len(results)}")
        
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except Exception as e:
        print(f"Error durante carga masiva: {e}")

def main():
    clear_screen()
    print("=== PRUEBA DEL ÍNDICE DE VECTORES CON PAGINACIÓN ===")
    
    vector_index = create_test_vector_index()
    
    while True:
        print_menu()
        option = input("Elija una opción (1-14): ")
        
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
            handle_compact_pages(vector_index)
        elif option == "12":
            handle_storage_stats(vector_index)
        elif option == "13":
            handle_mass_load_test(vector_index)
        elif option == "14":
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida. Por favor, elija una opción del 1 al 14.")
        
        input("\nPresione Enter para continuar...")
        clear_screen()

if __name__ == "__main__":
    main()
