#!/usr/bin/env python3
"""
Test simple y directo para verificar que el KNN multimedia funciona correctamente.
"""

import os
import sys

sys.path.append(".")

from HeiderDB.database.database import Database


def test_multimedia_knn():
    print("=" * 60)
    print("TEST MULTIMEDIA KNN - VERIFICACION COMPLETA")
    print("=" * 60)

    # Inicializar database
    db = Database()

    # 1. Crear tabla de prueba
    print("\n1. Creando tabla test_galeria...")
    success, message = db.create_table(
        table_name="test_galeria",
        columns={"id": "INT", "imagen": "IMAGE"},
        primary_key="id",
    )
    print(f"   Resultado: {success}, Mensaje: {message}")

    # 2. Insertar algunos registros
    print("\n2. Insertando registros de prueba...")
    image_path = "HeiderDB/test_images/messi.jpg"
    if os.path.exists(image_path):
        success, message = db.insert_into_table("test_galeria", [1, image_path])
        print(f"   Registro 1: {success}, {message}")

        success, message = db.insert_into_table(
            "test_galeria", [2, "HeiderDB/test_images/messi2.jpg"]
        )
        print(f"   Registro 2: {success}, {message}")
    else:
        print(f"   ERROR: No existe imagen de prueba en {image_path}")
        return False

    # 3. Verificar contenido de la tabla
    print("\n3. Verificando contenido de la tabla...")
    table = db.get_table("test_galeria")
    records = table.get_all()
    print(f"   Total registros: {len(records)}")
    for i, record in enumerate(records):
        print(f"   Record {i+1}: {record}")

    # 4. Crear índice multimedia
    print("\n4. Creando índice multimedia...")
    try:
        result, error = db.execute_query(
            "CREATE MULTIMEDIA INDEX idx_imagen ON test_galeria (imagen) WITH TYPE image METHOD sift"
        )
        if error:
            print(f"   ERROR: {error}")
            return False
        else:
            print(f"   SUCCESS: {result}")
    except Exception as e:
        print(f"   EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 5. Verificar que el índice se creó correctamente
    print("\n5. Verificando índice multimedia...")
    if hasattr(table, "indexes") and table.indexes:
        for index_name, index_obj in table.indexes.items():
            if hasattr(index_obj, "knn_search"):
                print(f"   Índice encontrado: {index_name}")
                count = index_obj.count() if hasattr(index_obj, "count") else 0
                print(f"   Total vectores: {count}")

                # Verificar VectorIndex
                if hasattr(index_obj, "vector_index") and index_obj.vector_index:
                    vi = index_obj.vector_index
                    print(f"   VectorIndex total_vectors: {vi.total_vectors}")
                    print(
                        f"   VectorIndex vector_index keys: {list(vi.vector_index.keys())}"
                    )
                    print(
                        f"   VectorIndex page_directory: {list(vi.page_directory.keys())}"
                    )
                break
    else:
        print("   ERROR: No se encontró índice multimedia")
        return False

    # 6. Probar búsqueda KNN
    print("\n6. Probando búsqueda KNN...")
    try:
        result, error = db.execute_query(
            f"SELECT * FROM test_galeria WHERE imagen SIMILAR TO '{image_path}' LIMIT 2"
        )
        if error:
            print(f"   ERROR en KNN: {error}")
            return False
        else:
            print(f"   SUCCESS KNN: {len(result)} resultados")
            for i, res in enumerate(result):
                print(f"   Resultado {i+1}: {res}")
    except Exception as e:
        print(f"   EXCEPTION en KNN: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("TEST COMPLETADO EXITOSAMENTE!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_multimedia_knn()
