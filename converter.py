#!/usr/bin/env python3
"""
Script genérico para convertir cualquier CSV agregando una columna espacial POINT
"""

import csv
import sys
import os

def analyze_csv(file_path):
    """
    Analiza el CSV y muestra las columnas disponibles
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            # Leer algunas filas de muestra
            sample_rows = []
            for i, row in enumerate(reader):
                if i >= 3:  # Solo 3 filas de muestra
                    break
                sample_rows.append(row)
            
        return headers, sample_rows
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return None, None

def show_columns(headers, sample_rows):
    """
    Muestra las columnas disponibles con ejemplos
    """
    print("\n📊 COLUMNAS DISPONIBLES EN EL CSV:")
    print("=" * 60)
    print(f"{'#':<3} {'Columna':<25} {'Ejemplos':<30}")
    print("-" * 60)
    
    for i, header in enumerate(headers):
        # Obtener ejemplos de esta columna
        examples = []
        for row in sample_rows:
            if i < len(row) and row[i].strip():
                examples.append(row[i].strip())
        
        examples_str = ", ".join(examples[:3])  # Solo 3 ejemplos
        if len(examples_str) > 28:
            examples_str = examples_str[:25] + "..."
            
        print(f"{i+1:<3} {header:<25} {examples_str:<30}")

def get_user_selection(headers, prompt):
    """
    Obtiene la selección del usuario para una columna
    """
    while True:
        try:
            print(f"\n{prompt}")
            choice = input("Ingresa el número de columna (o nombre): ").strip()
            
            # Intentar como número
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(headers):
                    return headers[idx], idx
                else:
                    print(f"❌ Número inválido. Debe estar entre 1 y {len(headers)}")
                    continue
            
            # Intentar como nombre de columna
            for i, header in enumerate(headers):
                if header.lower() == choice.lower():
                    return header, i
            
            print("❌ Columna no encontrada. Intenta de nuevo.")
            
        except KeyboardInterrupt:
            print("\n👋 Cancelado por el usuario")
            sys.exit(0)

def select_output_columns(headers):
    """
    Permite al usuario seleccionar qué columnas incluir en el output
    """
    print("\n📝 SELECCIÓN DE COLUMNAS DE SALIDA:")
    print("=" * 50)
    print("¿Qué columnas quieres incluir en el archivo final?")
    print("(Puedes seleccionar todas o solo algunas)")
    print()
    
    # Mostrar opciones
    print("Opciones:")
    print("1. Todas las columnas originales + columna espacial")
    print("2. Solo columnas seleccionadas + columna espacial")
    
    while True:
        choice = input("\nElige una opción (1 o 2): ").strip()
        
        if choice == "1":
            return headers, list(range(len(headers)))
        
        elif choice == "2":
            print("\nSelecciona las columnas que quieres incluir:")
            show_columns(headers, [])
            
            selected_columns = []
            selected_indices = []
            
            while True:
                col_input = input("\nIngresa número de columna (o 'done' para terminar): ").strip()
                
                if col_input.lower() == 'done':
                    if not selected_columns:
                        print("❌ Debes seleccionar al menos una columna")
                        continue
                    break
                
                try:
                    if col_input.isdigit():
                        idx = int(col_input) - 1
                        if 0 <= idx < len(headers) and idx not in selected_indices:
                            selected_columns.append(headers[idx])
                            selected_indices.append(idx)
                            print(f"✅ Agregada: {headers[idx]}")
                        elif idx in selected_indices:
                            print("⚠️  Ya seleccionada esa columna")
                        else:
                            print(f"❌ Número inválido. Debe estar entre 1 y {len(headers)}")
                    else:
                        print("❌ Ingresa un número válido")
                except ValueError:
                    print("❌ Ingresa un número válido")
            
            return selected_columns, selected_indices
        
        else:
            print("❌ Opción inválida. Elige 1 o 2.")

def convert_csv_with_spatial(input_file, output_file, lat_col, lng_col, selected_cols, selected_indices, spatial_col_name="ubicacion", max_rows=None):
    """
    Convierte el CSV agregando columna espacial
    """
    print(f"\n🔄 Convirtiendo archivo...")
    print(f"   Entrada: {input_file}")
    print(f"   Salida: {output_file}")
    print(f"   Latitud: {lat_col}")
    print(f"   Longitud: {lng_col}")
    print(f"   Columna espacial: {spatial_col_name}")
    
    rows_processed = 0
    rows_written = 0
    errors = 0
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        
        # Definir columnas de salida
        output_fieldnames = selected_cols + [spatial_col_name]
        
        writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
        writer.writeheader()
        
        for row in reader:
            rows_processed += 1
            
            # Límite de filas si se especifica
            if max_rows and rows_processed > max_rows:
                break
            
            try:
                # Extraer y validar coordenadas
                lat_str = row[lat_col].strip()
                lng_str = row[lng_col].strip()
                
                if not lat_str or not lng_str:
                    errors += 1
                    continue
                
                lat = float(lat_str)
                lng = float(lng_str)
                
                # Validar rangos de coordenadas
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    errors += 1
                    continue
                
                # Crear registro de salida
                output_row = {}
                
                # Copiar columnas seleccionadas
                for col in selected_cols:
                    output_row[col] = row[col].strip()
                
                # Agregar columna espacial en formato WKT
                output_row[spatial_col_name] = f"POINT({lng} {lat})"
                
                writer.writerow(output_row)
                rows_written += 1
                
                # Mostrar progreso
                if rows_written % 1000 == 0:
                    print(f"   Procesadas: {rows_written:,} filas")
                
            except (ValueError, KeyError) as e:
                errors += 1
                continue
    
    print(f"\n✅ Conversión completada!")
    print(f"   Filas procesadas: {rows_processed:,}")
    print(f"   Filas válidas escritas: {rows_written:,}")
    print(f"   Errores/omitidas: {errors:,}")
    print(f"   Archivo generado: {output_file}")
    
    return rows_written

def create_multiple_sizes(base_output_file, input_file, lat_col, lng_col, selected_cols, selected_indices, spatial_col_name):
    """
    Crear archivos de diferentes tamaños
    """
    sizes = [
        {"suffix": "_pequeno", "max_rows": 100, "desc": "100 registros"},
        {"suffix": "_mediano", "max_rows": 1000, "desc": "1,000 registros"},
        {"suffix": "_grande", "max_rows": 5000, "desc": "5,000 registros"}
    ]
    
    base_name = os.path.splitext(base_output_file)[0]
    
    print(f"\n📁 Creando archivos de diferentes tamaños...")
    
    results = []
    
    for size_config in sizes:
        output_file = f"{base_name}{size_config['suffix']}.csv"
        
        print(f"\n📄 Creando {output_file} ({size_config['desc']})...")
        
        count = convert_csv_with_spatial(
            input_file, 
            output_file,
            lat_col,
            lng_col, 
            selected_cols,
            selected_indices,
            spatial_col_name,
            size_config['max_rows']
        )
        
        results.append({
            'file': output_file,
            'count': count,
            'desc': size_config['desc']
        })
    
    return results

def show_usage_examples(results, spatial_col_name):
    """
    Muestra ejemplos de uso
    """
    print("\n" + "=" * 60)
    print("🚀 ARCHIVOS CREADOS Y CÓMO USARLOS")
    print("=" * 60)
    
    for result in results:
        print(f"✅ {result['file']:<30} - {result['count']:>6,} registros")
    
    print(f"\n📝 COMANDOS SQL PARA TU SISTEMA:")
    print("-" * 40)
    
    for i, result in enumerate(results):
        index_types = ["bplus_tree", "extendible_hash", "sequential_file"]
        index_type = index_types[i % len(index_types)]
        
        table_name = os.path.splitext(result['file'])[0].replace('_', '')
        
        print(f'CREATE TABLE {table_name} FROM FILE "{result["file"]}" USING INDEX {index_type}("id");')
    
    print(f"\n🔍 EJEMPLOS DE CONSULTAS ESPACIALES:")
    print("-" * 45)
    print(f'-- Buscar puntos cerca de una ubicación')
    print(f'SELECT * FROM datos WHERE {spatial_col_name} WITHIN ((lng, lat), radio);')
    print()
    print(f'-- Buscar en un área rectangular')
    print(f'SELECT * FROM datos WHERE {spatial_col_name} IN_RANGE ((lng1, lat1), (lng2, lat2));')
    print()
    print(f'-- Vecinos más cercanos')
    print(f'SELECT * FROM datos WHERE {spatial_col_name} NEAREST (lng, lat) LIMIT 5;')

def main():
    """
    Función principal
    """
    print("🌍 CONVERTIDOR CSV GENÉRICO - AGREGAR COLUMNA ESPACIAL")
    print("=" * 65)
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("\n📋 Uso:")
        print("   python generic_csv_converter.py <archivo.csv>")
        print("\n📝 Ejemplos:")
        print("   python generic_csv_converter.py ciudades.csv")
        print("   python generic_csv_converter.py restaurantes.csv")
        print("   python generic_csv_converter.py ubicaciones.csv")
        return
    
    input_file = sys.argv[1]
    
    # Verificar que el archivo existe
    if not os.path.exists(input_file):
        print(f"❌ Error: No se encontró el archivo {input_file}")
        return
    
    # Analizar el CSV
    print(f"\n🔍 Analizando archivo: {input_file}")
    headers, sample_rows = analyze_csv(input_file)
    
    if not headers:
        return
    
    # Mostrar columnas disponibles
    show_columns(headers, sample_rows)
    
    # Seleccionar columna de latitud
    lat_col, lat_idx = get_user_selection(headers, "🌐 Selecciona la columna de LATITUD:")
    print(f"✅ Latitud: {lat_col}")
    
    # Seleccionar columna de longitud
    lng_col, lng_idx = get_user_selection(headers, "🌐 Selecciona la columna de LONGITUD:")
    print(f"✅ Longitud: {lng_col}")
    
    # Seleccionar columnas de salida
    selected_cols, selected_indices = select_output_columns(headers)
    print(f"✅ Columnas seleccionadas: {', '.join(selected_cols)}")
    
    # Nombre de la columna espacial
    spatial_col_name = input(f"\n📍 Nombre para la columna espacial [ubicacion]: ").strip() or "ubicacion"
    
    # Archivo de salida base
    base_name = os.path.splitext(input_file)[0]
    output_base = f"{base_name}_espacial.csv"
    
    # Preguntar si crear múltiples tamaños
    create_multiple = input(f"\n🗂️  ¿Crear archivos de diferentes tamaños? (s/N): ").strip().lower()
    
    if create_multiple in ['s', 'si', 'y', 'yes']:
        results = create_multiple_sizes(
            output_base, input_file, lat_col, lng_col, 
            selected_cols, selected_indices, spatial_col_name
        )
        show_usage_examples(results, spatial_col_name)
    else:
        # Solo crear un archivo completo
        count = convert_csv_with_spatial(
            input_file, output_base, lat_col, lng_col,
            selected_cols, selected_indices, spatial_col_name
        )
        
        results = [{'file': output_base, 'count': count, 'desc': 'completo'}]
        show_usage_examples(results, spatial_col_name)

if __name__ == "__main__":
    main()