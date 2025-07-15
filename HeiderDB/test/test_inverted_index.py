#!/usr/bin/env python3
"""
Script de prueba para el índice invertido
Demuestra el funcionamiento completo del InvertedIndex integrado con la clase Table
"""

import os
import sys
import time
import shutil
import random

# Añadir el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from HeiderDB.database.table import Table  # Importar la clase Table modificada
from HeiderDB.database.indexes.inverted_index import InvertedIndex


def clear_screen():
    """Limpia la pantalla."""
    os.system("cls" if os.name == "nt" else "clear")


def clean_previous_data():
    """Limpia datos de ejecuciones anteriores."""
    data_dirs = ["data/tables", "data/indexes", "test_data"]

    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            try:
                shutil.rmtree(data_dir)
                print(f"✓ Directorio limpio: {data_dir}")
            except Exception as e:
                print(f"Advertencia limpiando {data_dir}: {e}")


def create_text_table():
    """Crea una tabla con columnas de texto."""
    print("Creando tabla con datos textuales...")

    # Definir columnas de la tabla
    columns = {
        "id": "INT",
        "title": "VARCHAR(100)",
        "content": "VARCHAR(1000)",
        "category": "VARCHAR(50)",
        "tags": "VARCHAR(200)"
    }

    # Crear tabla con índice B+ Tree para la clave primaria
    data_dir = os.path.join(os.getcwd(), "test_data")
    os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
    
    table = Table(
        name="documents",
        columns=columns,
        primary_key="id",
        page_size=4096,
        index_type="bplus_tree",
        data_dir=data_dir
    )

    print(f"Tabla '{table.name}' creada exitosamente")
    print(f"Columnas: {list(columns.keys())}")

    return table


def create_inverted_index(table, column_name="content"):
    """Crea un índice invertido para la columna especificada."""
    print(f"Creando índice invertido para columna '{column_name}'...")
    
    # Inicializar el diccionario de índices de texto si no existe
    if not hasattr(table, 'text_indexes'):
        table.text_indexes = {}
    
    # Crear el índice invertido
    text_index = InvertedIndex(
        table_name=table.name,
        column_name=column_name,
        data_path=table.data_path,
        table_ref=table,
        page_size=table.page_size
    )
    
    # Añadir el índice a la tabla
    table.text_indexes[column_name] = text_index
    
    print(f"Índice invertido creado para columna '{column_name}'")
    return text_index


def generate_random_text():
    """Genera texto aleatorio para pruebas."""
    topics = ["python", "database", "programming", "algorithm", "data structure", 
              "machine learning", "web development", "software engineering",
              "computer science", "artificial intelligence", "network security"]
    
    verbs = ["is", "enables", "provides", "requires", "supports", "implements",
             "defines", "uses", "contains", "includes", "processes"]
    
    adjectives = ["powerful", "efficient", "modern", "flexible", "reliable",
                 "advanced", "innovative", "scalable", "secure", "robust"]
    
    nouns = ["language", "framework", "algorithm", "solution", "system",
            "methodology", "approach", "technique", "concept", "paradigm"]
    
    # Generar una cantidad aleatoria de oraciones
    num_sentences = random.randint(3, 8)
    sentences = []
    
    for _ in range(num_sentences):
        topic = random.choice(topics)
        verb = random.choice(verbs)
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        
        # Estructura básica de oración
        sentence = f"{topic} {verb} a {adj} {noun}"
        
        # A veces añadir una cláusula adicional
        if random.random() > 0.6:
            sentence += f" that {random.choice(verbs)} {random.choice(adjectives)} {random.choice(nouns)}"
        
        # A veces añadir una segunda parte
        if random.random() > 0.7:
            sentence += f". It also {random.choice(verbs)} {random.choice(adjectives)} {random.choice(nouns)}"
        
        sentences.append(sentence + ".")
    
    return " ".join(sentences)


def generate_random_title():
    """Genera un título aleatorio."""
    topics = ["Introduction to", "Advanced", "The Art of", "Understanding", 
             "Practical", "Essential", "Modern", "Guide to"]
    
    subjects = ["Python", "Databases", "Programming", "Algorithms", "Data Structures", 
               "Machine Learning", "Web Development", "Software Engineering",
               "Computer Science", "Artificial Intelligence"]
    
    return f"{random.choice(topics)} {random.choice(subjects)}"


def generate_random_tags():
    """Genera etiquetas aleatorias."""
    all_tags = ["python", "database", "programming", "algorithms", "data", 
               "machine_learning", "web", "software", "computer_science", "ai",
               "tutorial", "guide", "advanced", "beginner", "research"]
    
    # Seleccionar entre 2 y 5 etiquetas aleatorias
    num_tags = random.randint(2, 5)
    tags = random.sample(all_tags, num_tags)
    
    return ", ".join(tags)


def insert_sample_data(table, num_records=50):
    """Inserta datos de muestra en la tabla."""
    print(f"Insertando {num_records} registros de muestra...")

    categories = ["Tutorial", "Article", "Research", "Documentation", "Blog"]

    for i in range(1, num_records + 1):
        # Generar datos aleatorios
        title = generate_random_title()
        content = generate_random_text()
        category = random.choice(categories)
        tags = generate_random_tags()

        record = {
            "id": i,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags
        }

        try:
            table.add(record)
        except Exception as e:
            print(f"Error insertando registro {i}: {e}")

    print(f"Datos insertados. Total de registros: {table.get_record_count()}")
    
    # Indexar los datos insertados
    index_columns = ["content", "title"]
    for column in index_columns:
        if column in table.text_indexes:
            print(f"Indexando columna '{column}'...")
            for record in table.get_all():
                table.text_indexes[column].add(record, record["id"])
            print(f"Indexación de '{column}' completada")


def test_text_searches(table):
    """Prueba diferentes tipos de búsquedas textuales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE BÚSQUEDAS TEXTUALES")
    print("=" * 50)

    # 1. Búsqueda simple por término
    print("\n1. Búsqueda simple por término:")
    search_term = "python"
    print(f"Buscando documentos que contienen '{search_term}'")

    try:
        text_index = table.text_indexes["content"]
        results = text_index.search_term(search_term)
        print(f"Encontrados {len(results)} resultados:")
        for i, result in enumerate(results[:5]):  # Mostrar solo los primeros 5
            print(f"  {i+1}. {result['title']} - {result['category']}")
            print(f"     ID: {result['id']}")
    except Exception as e:
        print(f"Error en búsqueda por término: {e}")

    # 2. Búsqueda booleana AND
    print("\n2. Búsqueda booleana AND:")
    search_query = "python AND database"
    print(f"Buscando: {search_query}")

    try:
        results = table.text_indexes["content"].search_boolean(search_query)
        print(f"Encontrados {len(results)} resultados:")
        for i, result in enumerate(results[:5]):
            print(f"  {i+1}. {result['title']} - {result['category']}")
            print(f"     ID: {result['id']}")
    except Exception as e:
        print(f"Error en búsqueda booleana AND: {e}")

    # 3. Búsqueda booleana OR
    print("\n3. Búsqueda booleana OR:")
    search_query = "algorithm OR data"
    print(f"Buscando: {search_query}")

    try:
        results = table.text_indexes["content"].search_boolean(search_query)
        print(f"Encontrados {len(results)} resultados:")
        for i, result in enumerate(results[:5]):
            print(f"  {i+1}. {result['title']} - {result['category']}")
            print(f"     ID: {result['id']}")
    except Exception as e:
        print(f"Error en búsqueda booleana OR: {e}")

    # 4. Búsqueda rankeada (multi-término)
    print("\n4. Búsqueda rankeada (multi-término):")
    search_query = "python database algorithm"
    k = 5
    print(f"Buscando top-{k} documentos relevantes para: '{search_query}'")

    try:
        results = table.text_indexes["content"].search_ranked(search_query, k)
        print(f"Top {len(results)} resultados:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['title']} - {result['category']}")
            if '_score' in result:
                print(f"     Score: {result['_score']:.4f}")
            print(f"     ID: {result['id']}")
    except Exception as e:
        print(f"Error en búsqueda rankeada: {e}")


def test_crud_operations(table):
    """Prueba operaciones CRUD con datos textuales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE OPERACIONES CRUD")
    print("=" * 50)

    # CREATE - Insertar nuevo registro
    print("\n1. Insertando nuevo documento...")
    new_record = {
        "id": 999,
        "title": "Test Document",
        "content": "This is a test document about Python and databases. It contains specific terms for testing the inverted index functionality.",
        "category": "Test",
        "tags": "test, python, database"
    }

    try:
        table.add(new_record)
        print("✓ Documento insertado exitosamente")
    except Exception as e:
        print(f"✗ Error insertando: {e}")

    # READ - Buscar el registro insertado
    print("\n2. Buscando el documento insertado por ID...")
    try:
        result = table.search("id", 999)
        if result:
            print(f"✓ Documento encontrado: {result['title']}")
        else:
            print("✗ Documento no encontrado")
    except Exception as e:
        print(f"✗ Error buscando: {e}")

    # Buscar por texto
    print("\n3. Buscando el documento por contenido...")
    try:
        results = table.text_indexes["content"].search_term("testing")
        if any(r['id'] == 999 for r in results):
            print("✓ Documento encontrado mediante índice invertido")
        else:
            print("✗ Documento no encontrado mediante índice invertido")
    except Exception as e:
        print(f"✗ Error en búsqueda textual: {e}")

    # DELETE - Eliminar el registro
    print("\n4. Eliminando el documento de prueba...")
    try:
        table.remove("id", 999)
        print("✓ Documento eliminado exitosamente")

        # Verificar eliminación
        result = table.search("id", 999)
        if not result:
            print("✓ Eliminación verificada - documento no encontrado")
        else:
            print("✗ El documento aún existe después de eliminación")
            
        # Verificar que también se eliminó del índice invertido
        results = table.text_indexes["content"].search_term("testing")
        if not any(r['id'] == 999 for r in results):
            print("✓ Documento también eliminado del índice invertido")
        else:
            print("✗ Documento aún presente en el índice invertido")
    except Exception as e:
        print(f"✗ Error eliminando: {e}")


def test_performance(table):
    """Prueba el rendimiento de las búsquedas textuales."""
    print("\n" + "=" * 50)
    print("PRUEBAS DE RENDIMIENTO")
    print("=" * 50)

    num_tests = 20

    # Test 1: Búsquedas por término simple
    print(f"\n1. Rendimiento de búsquedas por término simple ({num_tests} pruebas):")
    terms = ["python", "database", "algorithm", "system", "language", 
             "framework", "approach", "technique", "concept", "paradigm"]
    start_time = time.time()

    for _ in range(num_tests):
        term = random.choice(terms)
        try:
            results = table.text_indexes["content"].search_term(term)
        except Exception:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000  # En milisegundos
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")

    # Test 2: Búsquedas booleanas
    print(f"\n2. Rendimiento de búsquedas booleanas ({num_tests} pruebas):")
    boolean_queries = [
        "python AND database",
        "algorithm OR data",
        "machine AND learning",
        "web OR development",
        "software AND engineering"
    ]
    start_time = time.time()

    for _ in range(num_tests):
        query = random.choice(boolean_queries)
        try:
            results = table.text_indexes["content"].search_boolean(query)
        except Exception:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")

    # Test 3: Búsquedas rankeadas
    print(f"\n3. Rendimiento de búsquedas rankeadas ({num_tests} pruebas):")
    ranked_queries = [
        "python database algorithm",
        "machine learning data",
        "web development framework",
        "software engineering principles",
        "computer science concepts"
    ]
    start_time = time.time()

    for _ in range(num_tests):
        query = random.choice(ranked_queries)
        try:
            results = table.text_indexes["content"].search_ranked(query, 5)
        except Exception:
            pass

    end_time = time.time()
    avg_time = (end_time - start_time) / num_tests * 1000
    print(f"Tiempo promedio: {avg_time:.2f} ms por búsqueda")


def show_index_statistics(table):
    """Muestra estadísticas del índice invertido."""
    print("\n" + "=" * 50)
    print("ESTADÍSTICAS DEL ÍNDICE INVERTIDO")
    print("=" * 50)

    for column, index in table.text_indexes.items():
        print(f"\nÍndice para columna '{column}':")
        print(f"  - Documentos indexados: {index.count()}")
        print(f"  - Términos en el vocabulario: {len(index.dictionary)}")
        
        # Mostrar términos más comunes
        if index.dictionary:
            print("\n  Términos más comunes:")
            terms_by_frequency = sorted(
                [(term, data['df']) for term, data in index.dictionary.items()],
                key=lambda x: x[1],
                reverse=True
            )
            for i, (term, freq) in enumerate(terms_by_frequency[:10]):
                print(f"    {i+1}. '{term}' - en {freq} documentos")
        
        # Mostrar rutas de archivos
        print("\n  Archivos:")
        print(f"    - Diccionario: {os.path.basename(index.dictionary_file)}")
        print(f"    - Postings: {os.path.basename(index.postings_file)}")
        print(f"    - Metadata: {os.path.basename(index.metadata_file)}")


def interactive_search(table):
    """Permite al usuario realizar búsquedas interactivas."""
    print("\n" + "=" * 50)
    print("BÚSQUEDAS INTERACTIVAS")
    print("=" * 50)

    while True:
        print(
            """
Opciones de búsqueda:
1. Búsqueda por término simple
2. Búsqueda booleana (AND/OR)
3. Búsqueda rankeada (multi-término)
4. Volver al menú principal
"""
        )

        choice = input("Selecciona una opción (1-4): ").strip()

        if choice == "1":
            try:
                term = input("\nIngresa un término a buscar: ").strip()
                if not term:
                    print("Error: Término vacío")
                    continue
                    
                column = input("Columna a buscar (content/title): ").strip() or "content"
                if column not in table.text_indexes:
                    print(f"Error: No hay índice invertido para columna '{column}'")
                    continue
                    
                start_time = time.time()
                results = table.text_indexes[column].search_term(term)
                elapsed_time = time.time() - start_time
                
                print(f"\nEncontrados {len(results)} resultados en {elapsed_time*1000:.2f} ms:")
                for i, result in enumerate(results[:10]):
                    print(f"  {i+1}. {result['title']} - {result['category']}")
                    print(f"     ID: {result['id']}")
                    if len(results) > 10 and i == 9:
                        print(f"     ... y {len(results)-10} resultados más")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "2":
            try:
                print("\nIngresa una consulta booleana (ej: 'python AND database' o 'algorithm OR data')")
                query = input("> ").strip()
                if not query or " AND " not in query and " OR " not in query:
                    print("Error: Consulta inválida. Debe contener 'AND' o 'OR'")
                    continue
                    
                column = input("Columna a buscar (content/title): ").strip() or "content"
                if column not in table.text_indexes:
                    print(f"Error: No hay índice invertido para columna '{column}'")
                    continue
                    
                start_time = time.time()
                results = table.text_indexes[column].search_boolean(query)
                elapsed_time = time.time() - start_time
                
                print(f"\nEncontrados {len(results)} resultados en {elapsed_time*1000:.2f} ms:")
                for i, result in enumerate(results[:10]):
                    print(f"  {i+1}. {result['title']} - {result['category']}")
                    print(f"     ID: {result['id']}")
                    if len(results) > 10 and i == 9:
                        print(f"     ... y {len(results)-10} resultados más")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "3":
            try:
                print("\nIngresa múltiples términos separados por espacios:")
                query = input("> ").strip()
                if not query:
                    print("Error: Consulta vacía")
                    continue
                    
                column = input("Columna a buscar (content/title): ").strip() or "content"
                if column not in table.text_indexes:
                    print(f"Error: No hay índice invertido para columna '{column}'")
                    continue
                    
                k = int(input("Número de resultados a mostrar (top-k): ") or "5")
                
                start_time = time.time()
                results = table.text_indexes[column].search_ranked(query, k)
                elapsed_time = time.time() - start_time
                
                print(f"\nTop {len(results)} resultados en {elapsed_time*1000:.2f} ms:")
                for i, result in enumerate(results):
                    print(f"  {i+1}. {result['title']} - {result['category']}")
                    if '_score' in result:
                        print(f"     Score: {result['_score']:.4f}")
                    print(f"     ID: {result['id']}")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "4":
            break

        else:
            print("Opción inválida")

        input("\nPresiona Enter para continuar...")


def main():
    """Función principal del script de prueba."""
    clear_screen()
    print("=" * 60)
    print("SCRIPT DE PRUEBA PARA ÍNDICES INVERTIDOS")
    print("=" * 60)

    # Preguntar si limpiar datos anteriores
    clean_choice = input("\n¿Limpiar datos de ejecuciones anteriores? (s/n): ").strip().lower()
    if clean_choice in ["s", "si", "y", "yes"]:
        clean_previous_data()

    # Crear tabla con datos textuales
    table = create_text_table()
    
    # Crear índices invertidos
    create_inverted_index(table, "content")
    create_inverted_index(table, "title")

    # Insertar datos de muestra
    insert_sample_data(table, 50)

    while True:
        print("\n" + "=" * 50)
        print("MENÚ PRINCIPAL")
        print("=" * 50)
        print(
            """
1. Ejecutar pruebas de búsquedas textuales
2. Ejecutar pruebas de rendimiento
3. Mostrar estadísticas del índice
4. Búsquedas interactivas
5. Probar operaciones CRUD
6. Insertar más datos de muestra
7. Reconstruir índice invertido
8. Mostrar todos los documentos
9. Salir
"""
        )

        choice = input("Selecciona una opción (1-9): ").strip()

        if choice == "1":
            test_text_searches(table)

        elif choice == "2":
            test_performance(table)

        elif choice == "3":
            show_index_statistics(table)

        elif choice == "4":
            interactive_search(table)

        elif choice == "5":
            test_crud_operations(table)

        elif choice == "6":
            try:
                num = int(input("¿Cuántos documentos adicionales? "))
                current_count = table.get_record_count()
                start_time = time.time()
                insert_sample_data(table, num)
                end_time = time.time()
                print(f"✓ Datos insertados en {end_time - start_time:.2f}s. Total: {table.get_record_count()}")
            except ValueError:
                print("Error: Ingresa un número válido")

        elif choice == "7":
            # Reconstruir índice invertido
            print("\nReconstruyendo índice invertido...")
            try:
                start_time = time.time()
                for column, index in table.text_indexes.items():
                    print(f"Reconstruyendo índice para columna '{column}'...")
                    index.rebuild()
                end_time = time.time()
                print(f"✓ Índices reconstruidos en {end_time - start_time:.2f}s")
            except Exception as e:
                print(f"Error reconstruyendo índices: {e}")

        elif choice == "8":
            print("\nTodos los documentos en la tabla:")
            try:
                all_records = table.get_all()
                for i, record in enumerate(all_records[:20]):  # Mostrar solo primeros 20
                    print(f"  {i+1}. ID: {record['id']}, Título: {record['title']}")
                    print(f"     Categoría: {record['category']}")
                    print(f"     Tags: {record['tags']}")
                if len(all_records) > 20:
                    print(f"  ... y {len(all_records) - 20} documentos más")
                print(f"\nTotal de documentos: {len(all_records)}")
            except Exception as e:
                print(f"Error obteniendo registros: {e}")

        elif choice == "9":
            print("\n¡Gracias por usar el script de prueba!")
            break

        else:
            print("Opción inválida. Por favor selecciona 1-9.")

        if choice in ["1", "2", "3", "5", "7"]:
            input("\nPresiona Enter para continuar...")
            clear_screen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrumpido por el usuario.")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        import traceback
        traceback.print_exc()