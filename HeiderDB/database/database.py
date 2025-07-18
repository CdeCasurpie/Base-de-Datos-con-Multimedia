import os
import json
import sys
from HeiderDB.database.table import Table
from HeiderDB.database.parser import parse_query


class Database:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.tables = {}

        os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)

        self._load_tables()

    def create_table(
        self,
        table_name,
        columns,
        primary_key=None,
        index_type="sequential",
        spatial_columns=None,
        page_size=4096,
        text_columns=None,
    ):
        """
        Crea una nueva tabla en la base de datos.

        Params:
            table_name (str): Nombre de la tabla.
            columns (dict): Diccionario con columnas y sus tipos.
            primary_key (str): Columna que será clave primaria.
            index_type (str): Tipo de índice a utilizar.
            spatial_columns (list): Columnas espaciales para índices R-Tree.
            page_size (int): Tamaño de página para estructuras de índice.

        Returns:
            tuple: (bool, str) - Éxito y mensaje informativo.
        """
        if table_name in self.tables:
            return False, f"La tabla '{table_name}' ya existe"

        if not primary_key and columns:
            # Si no se especifica primary_key, usar primera columna
            primary_key = list(columns.keys())[0]

        try:
            start_time = __import__("time").time()

            table = Table(
                name=table_name,
                columns=columns,
                primary_key=primary_key,
                page_size=page_size,
                index_type=index_type,
                spatial_columns=spatial_columns,
                text_columns=text_columns,
            )

            self.tables[table_name] = table

            elapsed = __import__("time").time() - start_time

            return True, f"Tabla '{table_name}' creada exitosamente en {elapsed:.3f}s"
        except Exception as e:
            return False, f"Error al crear tabla: {e}"

    def create_table_from_file(
        self,
        table_name,
        file_path,
        index_type="sequential",
        primary_key=None,
        page_size=4096,
    ):
        """
        Crea una tabla a partir de un archivo JSON o CSV sin cargar todo en memoria.

        Params:
            table_name (str): Nombre de la tabla.
            file_path (str): Ruta al archivo de datos.
            index_type (str): Tipo de índice a usar.
            primary_key (str): Clave primaria a usar.
            page_size (int): Tamaño de página.

        Returns:
            tuple: (bool, str) - Éxito y mensaje informativo.
        """
        if table_name in self.tables:
            return False, f"La tabla '{table_name}' ya existe"

        if not os.path.exists(file_path):
            return False, f"El archivo '{file_path}' no existe"

        try:
            import json
            import csv
            from datetime import datetime

            # Determinar tipo de archivo por extensión
            if file_path.lower().endswith(".json"):
                # Para JSON, usaremos un enfoque de streaming
                import ijson  # Necesitarías instalar ijson: pip install ijson

                # Primera pasada: determinar estructura
                columns = {}
                sample_count = 0
                with open(file_path, "rb") as f:
                    # Leer el archivo JSON como un stream
                    parser = ijson.parse(f)
                    current_path = []
                    current_record = {}

                    for prefix, event, value in parser:
                        if event == "start_array" and not prefix:
                            continue
                        elif event == "end_array" and not prefix:
                            break

                        # Navegar por la estructura del JSON
                        if event == "start_map":
                            current_record = {}
                        elif event == "end_map":
                            # Procesar record completo
                            if sample_count < 100:  # Limitar muestras
                                for col, val in current_record.items():
                                    if col not in columns:
                                        columns[col] = self._infer_column_type(val)
                                    else:
                                        # Actualizar tipo si es necesario (ej: de INT a VARCHAR)
                                        columns[col] = self._reconcile_types(
                                            columns[col], val
                                        )

                                sample_count += 1
                        elif event == "map_key":
                            current_path.append(value)
                        elif event in ("string", "number", "boolean", "null"):
                            if current_path:
                                key = current_path[-1]
                                current_record[key] = value
                                current_path.pop()

                # Detectar columnas espaciales
                spatial_columns = [
                    col
                    for col, tipo in columns.items()
                    if tipo in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]
                ]

                # Si no se especificó primary_key, usar la primera columna
                if not primary_key and columns:
                    primary_key = list(columns.keys())[0]

                # Crear la tabla con la estructura inferida
                table = Table(
                    name=table_name,
                    columns=columns,
                    primary_key=primary_key,
                    page_size=page_size,
                    index_type=index_type,
                    spatial_columns=spatial_columns,
                )

                # Segunda pasada: cargar datos
                records_loaded = 0
                records_total = 0

                print(f"Cargando datos desde {file_path}...")
                start_time = __import__("time").time()
                batch_size = 1000
                batch = []

                with open(file_path, "rb") as f:
                    # Leer el archivo JSON como un stream nuevamente
                    parser = ijson.items(f, "item")

                    for record in parser:
                        records_total += 1

                        try:
                            # Procesar datos para que coincidan con los tipos definidos
                            processed_record = self._process_record_for_table(
                                record, columns
                            )

                            # Añadir al batch
                            batch.append(processed_record)

                            # Insertar batch cuando alcanza el tamaño definido
                            if len(batch) >= batch_size:
                                for rec in batch:
                                    table.add(rec)
                                    records_loaded += 1

                                batch = []

                                # Mostrar progreso
                                elapsed = __import__("time").time() - start_time
                                print(
                                    f"Progreso: {records_loaded} registros cargados en {elapsed:.2f}s",
                                    end="\r",
                                )

                        except Exception as e:
                            print(f"\nError cargando registro #{records_total}: {e}")

                    # Cargar registros restantes del batch
                    for rec in batch:
                        try:
                            table.add(rec)
                            records_loaded += 1
                        except Exception as e:
                            print(f"\nError cargando registro: {e}")

            elif file_path.lower().endswith(".csv"):
                # Primera pasada: contar registros y analizar estructura
                total_records = 0
                columns = {}

                print("Analizando estructura del CSV...")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)
                    total_records += 1

                    # Inicializar diccionario para almacenar información sobre columnas
                    column_stats = {
                        col: {"types_seen": set(), "max_length": 0, "sample_values": []}
                        for col in headers
                    }

                    # Analizar una muestra de registros para inferir tipos
                    for i, row in enumerate(csv_reader):
                        total_records += 1

                        # Limitar análisis detallado a primeros 1000 registros
                        if i < 1000:
                            for j, val in enumerate(row):
                                if j < len(headers):
                                    col = headers[j]
                                    val_len = len(val)

                                    # Actualizar longitud máxima
                                    if val_len > column_stats[col]["max_length"]:
                                        column_stats[col]["max_length"] = val_len

                                    # Determinar tipo
                                    if self._is_int(val):
                                        column_stats[col]["types_seen"].add("INT")
                                    elif self._is_float(val):
                                        column_stats[col]["types_seen"].add("FLOAT")
                                    elif val.lower() in ("true", "false", "1", "0"):
                                        column_stats[col]["types_seen"].add("BOOLEAN")
                                    elif val.upper().startswith(
                                        ("POINT", "POLYGON", "LINESTRING", "GEOMETRY")
                                    ):
                                        spatial_type = val.split("(")[0].upper()
                                        column_stats[col]["types_seen"].add(
                                            spatial_type
                                        )
                                        column_stats[col]["sample_values"].append(val)
                                    else:
                                        column_stats[col]["types_seen"].add("VARCHAR")

                        # Solo contar el resto de registros
                        if i % 10000 == 0:
                            print(f"Analizados {i} registros...", end="\r")

                # Determinar el tipo final para cada columna
                for col, stats in column_stats.items():
                    types = stats["types_seen"]

                    # Priorizar tipos espaciales
                    if any(
                        t in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]
                        for t in types
                    ):
                        for val in stats["sample_values"]:
                            if val and val.upper().startswith(
                                ("POINT", "POLYGON", "LINESTRING", "GEOMETRY")
                            ):
                                columns[col] = val.split("(")[0].upper()
                                break
                    # Si hay mezcla de tipos numéricos, usar el más flexible
                    elif "VARCHAR" in types:
                        max_len = max(30, stats["max_length"] + 10)
                        columns[col] = f"VARCHAR({max_len})"
                    elif "FLOAT" in types:
                        columns[col] = "FLOAT"
                    elif "INT" in types:
                        columns[col] = "INT"
                    elif "BOOLEAN" in types:
                        columns[col] = "BOOLEAN"
                    else:
                        # Por defecto, usar VARCHAR
                        max_len = max(30, stats["max_length"] + 10)
                        columns[col] = f"VARCHAR({max_len})"

                # Detectar columnas espaciales
                spatial_columns = [
                    col
                    for col, tipo in columns.items()
                    if tipo in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]
                ]

                # Si no se especificó primary_key, usar la primera columna
                if not primary_key and columns:
                    primary_key = list(columns.keys())[0]

                print(f"\nEstructura de tabla inferida: {len(columns)} columnas")

                # Crear la tabla con la estructura inferida
                table = Table(
                    name=table_name,
                    columns=columns,
                    primary_key=primary_key,
                    page_size=page_size,
                    index_type=index_type,
                    spatial_columns=spatial_columns,
                )

                # Segunda pasada: cargar datos
                records_loaded = 0
                batch_size = 1000
                batch = []

                print(f"Cargando {total_records} registros desde {file_path}...")
                start_time = __import__("time").time()

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)  # Leer headers de nuevo

                    for i, row in enumerate(csv_reader):
                        try:
                            record = {}
                            for j, col in enumerate(headers):
                                if j < len(row):
                                    val = row[j]
                                    # Convertir según tipo inferido
                                    col_type = columns[col]

                                    if col_type == "INT" and val:
                                        record[col] = int(val)
                                    elif col_type == "FLOAT" and val:
                                        record[col] = float(val)
                                    elif col_type == "BOOLEAN":
                                        record[col] = val.lower() in ("true", "1")
                                    else:
                                        record[col] = val

                            # Añadir al batch
                            batch.append(record)

                            # Insertar batch cuando alcanza el tamaño definido
                            if len(batch) >= batch_size:
                                for rec in batch:
                                    table.add(rec)
                                    records_loaded += 1

                                batch = []

                                # Mostrar progreso cada 10,000 registros
                                if records_loaded % 10000 == 0:
                                    elapsed = __import__("time").time() - start_time
                                    rate = (
                                        records_loaded / elapsed if elapsed > 0 else 0
                                    )
                                    eta = (
                                        (total_records - records_loaded) / rate
                                        if rate > 0
                                        else "desconocido"
                                    )
                                    eta_str = (
                                        f"{eta:.0f}s" if isinstance(eta, float) else eta
                                    )
                                    print(
                                        f"Progreso: {records_loaded}/{total_records} registros ({records_loaded/total_records*100:.1f}%) - Velocidad: {rate:.1f} reg/s - ETA: {eta_str}",
                                        end="\r",
                                    )

                        except Exception as e:
                            print(f"\nError cargando registro #{i+2}: {e}")

                    # Cargar registros restantes del batch
                    for rec in batch:
                        try:
                            table.add(rec)
                            records_loaded += 1
                        except Exception as e:
                            print(f"\nError cargando registro: {e}")

            else:
                return False, "Formato de archivo no soportado. Use JSON o CSV."

            self.tables[table_name] = table

            elapsed_total = __import__("time").time() - start_time
            print(f"\nCarga completada en {elapsed_total:.2f}s")
            return True, f"Tabla '{table_name}' creada con {records_loaded} registros"

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, f"Error creando tabla desde archivo: {e}"

    def execute_query(self, query):
        """
        Ejecuta una consulta SQL.

        Params:
            query (str): Consulta SQL a ejecutar.

        Returns:
            tuple: (results, error) - Resultados o mensaje de error.
        """
        try:
            parsed = parse_query(query)

            if parsed.get("error_message"):
                return None, parsed["error_message"]

            query_type = parsed.get("type", "").upper()

            print(query_type)

            # CREATE TABLE
            if query_type == "CREATE_TABLE":
                success, message = self.create_table(
                    table_name=parsed["table_name"],
                    columns=parsed["columns"],
                    primary_key=parsed["primary_key"],
                    index_type=parsed["index_type"],
                    spatial_columns=parsed.get("spatial_columns", []),
                    text_columns=parsed.get("text_columns", []),
                )
                return message, not success

            # CREATE TABLE FROM FILE
            elif query_type == "CREATE_TABLE_FROM_FILE":
                success, message = self.create_table_from_file(
                    table_name=parsed["table_name"],
                    file_path=parsed["file_path"],
                    index_type=parsed["index_type"],
                    primary_key=parsed["primary_key"],
                )
                print(f"CREATE TABLE FROM FILE: {message}")
                print(f"CREATE TABLE FROM FILE: {not success}")
                return message, not success

            # DROP TABLE
            elif query_type == "DROP_TABLE":
                table_name = parsed["table_name"]
                success, message = self.drop_table(table_name)
                return message, not success

            # CREATE INVERTED INDEX
            elif query_type == "CREATE_INVERTED_INDEX":
                table_name = parsed["table_name"]
                column_name = parsed["column_name"]

                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"

                table = self.tables[table_name]

                if column_name not in table.columns:
                    return (
                        None,
                        f"Columna '{column_name}' no encontrada en tabla '{table_name}'",
                    )

                # Verificar que es un tipo de texto válido (VARCHAR)
                col_type = table.columns[column_name]
                if not col_type.startswith("VARCHAR"):
                    return (
                        None,
                        f"La columna '{column_name}' no es un tipo de texto válido (VARCHAR)",
                    )

                if column_name not in table.text_columns:
                    table.text_columns.append(column_name)
                    table._create_text_indexes()
                    table._save_metadata()
                    return f"Índice invertido creado para '{column_name}'", None
                else:
                    return None, f"Ya existe un índice invertido para '{column_name}'"

            # CREATE SPATIAL INDEX
            elif query_type == "CREATE_SPATIAL_INDEX":
                table_name = parsed["table_name"]
                column_name = parsed["column_name"]

                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"

                table = self.tables[table_name]

                if column_name not in table.columns:
                    return (
                        None,
                        f"Columna '{column_name}' no encontrada en tabla '{table_name}'",
                    )

                # Verificar que es un tipo espacial válido
                col_type = table.columns[column_name]
                if (
                    col_type not in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]
                    and not col_type.startswith("POINT")
                    and not col_type.startswith("POLYGON")
                ):
                    return (
                        None,
                        f"La columna '{column_name}' no es un tipo espacial válido",
                    )

                # Añadir a columnas espaciales si no está ya
                if column_name not in table.spatial_columns:
                    table.spatial_columns.append(column_name)
                    table._create_spatial_indexes()
                    table._save_metadata()
                    return f"Índice espacial creado para '{column_name}'", None
                else:
                    return None, f"Ya existe un índice espacial para '{column_name}'"

            # CREATE MULTIMEDIA INDEX
            elif query_type == "CREATE_MULTIMEDIA_INDEX":
                table_name = parsed["table_name"]
                column_name = parsed["column_name"]
                media_type = parsed["media_type"]
                method = parsed["method"]
                train_folder = parsed.get("train_folder")  # Nuevo: folder de entrenamiento

                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"

                table = self.tables[table_name]

                if column_name not in table.columns:
                    return (
                        None,
                        f"Columna '{column_name}' no encontrada en tabla '{table_name}'",
                    )

                # Verificar que es un tipo multimedia válido
                col_type = table.columns[column_name]
                if col_type not in ["IMAGE", "AUDIO", "VIDEO"]:
                    return (
                        None,
                        f"La columna '{column_name}' no es un tipo multimedia válido (IMAGE, AUDIO, VIDEO)",
                    )

                # Verificar que el media_type coincide con el tipo de columna
                if (
                    (media_type == "image" and col_type != "IMAGE")
                    or (media_type == "audio" and col_type not in ["AUDIO", "VIDEO"])
                    or (media_type == "video" and col_type != "VIDEO")
                ):
                    return (
                        None,
                        f"El tipo multimedia '{media_type}' no coincide con el tipo de columna '{col_type}'",
                    )

                try:
                    # Crear el índice multimedia usando table.create_index
                    multimedia_index = table.create_index(
                        column_name, "multimedia", media_type=media_type, method=method
                    )

                    # Inicializar el índice multimedia
                    multimedia_index.initialize(media_type=media_type, method=method)


                    print("holi")
                    # NUEVO: Entrenar vocabulario visual si se proporcionó folder
                    if train_folder:
                        import os 
                        if not os.path.exists(train_folder):
                            return None, f"Folder de entrenamiento no encontrado: {train_folder}"
                        
                        print(f"Entrenando vocabulario visual desde: {train_folder}")
                        
                        # Verificar que el índice multimedia tiene vector_index
                        if not hasattr(multimedia_index, 'vector_index') or multimedia_index.vector_index is None:
                            return None, "Error: índice vectorial no inicializado correctamente"
                        
                        # Verificar que tiene feature_extractor
                        if not hasattr(multimedia_index, 'feature_extractor') or multimedia_index.feature_extractor is None:
                            return None, "Error: extractor de características no inicializado"
                        
                        try:
                            # Entrenar el vocabulario visual
                            multimedia_index.vector_index.train_visual_vocabulary(
                                folder_path=train_folder,
                                feature_extractor=multimedia_index.feature_extractor
                            )
                            print(f"✓ Vocabulario visual entrenado exitosamente con {multimedia_index.vector_index.num_clusters} clusters")
                        except Exception as e:
                            return None, f"Error entrenando vocabulario visual: {e}"


                    print("oli 2")
                    # Indexar registros existentes en la tabla
                    records = table.get_all()

                    for i, record in enumerate(records):
                        if column_name in record and record[column_name]:
                            # Obtener la clave primaria del registro
                            primary_key_column = table.primary_key
                            if primary_key_column and primary_key_column in record:
                                key = record[primary_key_column]
                                image_path = record[column_name]
                                if isinstance(image_path, bytes):
                                    image_path = image_path.decode("utf-8").rstrip("\x00")

                                try:
                                    multimedia_index.add(record, key)
                                except Exception as e:
                                    print(f"⚠ Error indexando registro {key}: {e}")

                    success_msg = f"Índice multimedia creado exitosamente para '{column_name}' con método '{method}'"
                    if train_folder:
                        success_msg += f" y vocabulario entrenado desde '{train_folder}'"
                    
                    return success_msg, None
                    
                except Exception as e:
                    return None, f"Error creando índice multimedia no uwu: {e}"

            # SELECT
            elif query_type == "SELECT":
                table_name = parsed["table_name"]

                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"

                table = self.tables[table_name]

                # Determinar columnas a seleccionar
                if parsed["columns"] == "*":
                    selected_columns = table.get_column_names()
                else:
                    selected_columns = [
                        col.strip() for col in parsed["columns"].split(",")
                    ]

                # Manejo especial para SELECT TOP N
                top_limit = None
                if selected_columns and selected_columns[0].upper().startswith("TOP "):
                    try:
                        top_limit = int(selected_columns[0].split(" ")[1])
                        selected_columns = (
                            table.get_column_names()
                        )  # Si es TOP N, seleccionamos todas las columnas
                    except (IndexError, ValueError):
                        return None, f"Error en cláusula TOP: formato incorrecto"

                # Verificar columnas
                for col in selected_columns:
                    if col not in table.columns:
                        return (
                            None,
                            f"Columna '{col}' no encontrada en tabla '{table_name}'",
                        )

                # Ejecutar búsqueda según tipo de condición
                if "condition_type" in parsed:
                    condition = parsed["condition_type"]

                    # Búsqueda textual - CONTAINS
                    if condition == "TEXT_CONTAINS":
                        column = parsed["column"]
                        query_text = parsed["query"]

                        print(
                            f"DEBUG: Ejecutando TEXT_CONTAINS en columna '{column}' con query '{query_text}'"
                        )

                        # Verificar que existe el índice invertido
                        if (
                            not hasattr(table, "text_indexes")
                            or column not in table.text_indexes
                        ):
                            return (
                                None,
                                f"No hay índice invertido en columna '{column}'. Utilice CREATE INVERTED INDEX.",
                            )

                        # Ejecutar búsqueda con el índice invertido
                        try:
                            results = table.text_indexes[column].search(query_text)
                            if not results:
                                return [], None  # No se encontraron resultados
                        except Exception as e:
                            return None, f"Error en búsqueda de texto: {str(e)}"

                    # Búsqueda textual por relevancia - RANKED BY
                    elif condition == "TEXT_RANKED":
                        column = parsed["column"]
                        query_text = parsed["query"]
                        limit = parsed.get("limit", 5)  # Límite por defecto: 5

                        # Verificar que existe el índice invertido
                        if (
                            not hasattr(table, "text_indexes")
                            or column not in table.text_indexes
                        ):
                            return (
                                None,
                                f"No hay índice invertido en columna '{column}'. Utilice CREATE INVERTED INDEX.",
                            )

                        # Ejecutar búsqueda por relevancia
                        try:
                            results = table.text_indexes[column].search_ranked(
                                query_text, limit
                            )
                            if not results:
                                return [], None  # No se encontraron resultados
                        except Exception as e:
                            return None, f"Error en búsqueda por relevancia: {str(e)}"

                    # Búsqueda espacial - dentro de radio
                    elif condition in ["SPATIAL_WITHIN", "SPATIAL"]:
                        column = parsed["column"]
                        point = parsed["point"]
                        radius = parsed["radius"]

                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"

                        results = table.spatial_search(column, point, radius)

                    # Búsqueda espacial - intersección
                    elif condition == "SPATIAL_INTERSECTS":
                        column = parsed["column"]
                        geometry = parsed["geometry"]

                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"

                        results = table.intersection_search(column, geometry)

                    # Búsqueda espacial - vecinos más cercanos
                    elif condition == "SPATIAL_NEAREST":
                        column = parsed["column"]
                        point = parsed["point"]
                        limit = parsed["limit"]

                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"

                        results = table.nearest_search(column, point, limit)

                    # Búsqueda espacial - rango
                    elif condition == "SPATIAL_RANGE":
                        column = parsed["column"]
                        min_point = parsed["min_point"]
                        max_point = parsed["max_point"]

                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"

                        results = table.range_search_spatial(
                            column, min_point, max_point
                        )

                    # Búsqueda por similitud multimedia
                    elif condition == "MULTIMEDIA_SIMILARITY":
                        column = parsed["column"]
                        query_file = parsed["query_file"]
                        limit = parsed.get("limit", 5)

                        # Verificar que existe el índice multimedia
                        multimedia_index = None
                        if hasattr(table, "indexes") and table.indexes:
                            for index_name, index_obj in table.indexes.items():
                                if (
                                    hasattr(index_obj, "column_name")
                                    and index_obj.column_name == column
                                ):
                                    if hasattr(
                                        index_obj, "knn_search"
                                    ):  # Es un MultimediaIndex
                                        multimedia_index = index_obj
                                        break

                        if not multimedia_index:
                            return (
                                None,
                                f"No hay índice multimedia en columna '{column}'. Utilice CREATE MULTIMEDIA INDEX.",
                            )

                        # Verificar que el archivo de consulta existe
                        import os

                        if not os.path.exists(query_file):
                            return (
                                None,
                                f"Archivo de consulta no encontrado: {query_file}",
                            )

                        # Ejecutar búsqueda por similitud
                        try:
                            similarity_results = multimedia_index.knn_search(
                                query_file, k=limit
                            )

                            if not similarity_results:
                                return (
                                    [],
                                    None,
                                )  # No se encontraron resultados similares

                            # Convertir resultados a registros completos
                            results = []

                            for i, (vector_id, distance) in enumerate(
                                similarity_results
                            ):
                                # Buscar registro completo por ID
                                try:
                                    record = table.search(table.primary_key, vector_id)

                                    if record:
                                        # Convertir tupla a diccionario si es necesario
                                        if isinstance(record, tuple):
                                            record_dict = dict(
                                                zip(table.get_column_names(), record)
                                            )
                                        elif isinstance(record, dict):
                                            record_dict = record.copy()
                                        else:
                                            continue

                                        # Añadir distancia de similitud
                                        record_dict["_similarity_distance"] = distance
                                        record_dict["_similarity_score"] = 1.0 / (
                                            1.0 + distance
                                        )  # Score normalizado
                                        results.append(record_dict)
                                except Exception as e:
                                    continue

                            # Ordenar por distancia (menor distancia = mayor similitud)
                            results.sort(key=lambda x: x["_similarity_distance"])

                            return results, None

                        except Exception as e:
                            return None, f"Error en búsqueda por similitud: {str(e)}"

                    # Búsqueda por rango
                    elif condition == "RANGE":
                        column = parsed["column"]
                        begin_value = parsed["begin_value"]
                        end_value = parsed["end_value"]

                        results = table.range_search(column, begin_value, end_value)

                    # Búsqueda por comparación
                    elif condition == "COMPARISON":
                        column = parsed["column"]
                        operator = parsed["operator"]
                        value = parsed["value"]

                        if operator == "=":
                            results = table.search(column, value)
                            if not isinstance(results, list):
                                results = [results] if results else []
                        else:
                            # Para otros operadores, realizar búsqueda completa y filtrar
                            all_records = table.get_all()
                            results = []

                            for record in all_records:
                                record_val = record.get(column)

                                if operator == "!=":
                                    if record_val != value:
                                        results.append(record)
                                elif operator == "<":
                                    if record_val < value:
                                        results.append(record)
                                elif operator == ">":
                                    if record_val > value:
                                        results.append(record)
                                elif operator == "<=":
                                    if record_val <= value:
                                        results.append(record)
                                elif operator == ">=":
                                    if record_val >= value:
                                        results.append(record)
                    else:
                        return None, f"Tipo de condición no soportado: {condition}"

                else:
                    # Sin condiciones, recuperar todos los registros
                    results = table.get_all()

                # Aplicar límite TOP N si está especificado
                if top_limit is not None and isinstance(results, list):
                    results = results[:top_limit]

                print(results)

                # Filtrar solo las columnas solicitadas
                filtered_results = []
                for record in results:
                    filtered_record = {
                        col: record[col] for col in selected_columns if col in record
                    }
                    filtered_results.append(filtered_record)

                return filtered_results, None

            # INSERT
            elif query_type == "INSERT":
                table_name = parsed["table_name"]
                values = parsed["values"]

                success, message = self.insert_into_table(table_name, values)
                if success:
                    return f"Registro insertado en '{table_name}'", None
                else:
                    return None, message

            # DELETE
            elif query_type == "DELETE":
                table_name = parsed["table_name"]
                column = parsed["column"]
                value = parsed["value"]

                success, message = self.delete_from_table(table_name, column, value)
                if success:
                    return f"Registro eliminado de '{table_name}'", None
                else:
                    return None, message

            else:
                return None, f"Tipo de consulta no soportado: {query_type}"

        except Exception as e:
            import traceback

            traceback.print_exc()
            return None, f"Error ejecutando consulta: {e}"

    def list_tables(self):
        """
        Returns:
            list: Lista de nombres de tablas en la base de datos.
        """
        return list(self.tables.keys())

    def get_table(self, table_name):
        """
        Params:
            table_name (str): Nombre de la tabla a recuperar.

        Returns:
            Table: Instancia de la clase Table o None si no existe.
        """
        return self.tables.get(table_name)

    def _load_tables(self):
        """
        Carga todas las tablas desde los archivos de metadatos.
        """
        tables_dir = os.path.join(self.data_dir, "tables")
        if not os.path.exists(tables_dir):
            return

        # Buscar archivos de metadatos
        for filename in os.listdir(tables_dir):
            if filename.endswith(".json"):
                table_name = filename[:-5]  # Quitar extensión .json
                try:
                    # Cargar la tabla con su página por defecto
                    table = Table.from_table_name(table_name, 4096, self.data_dir)
                    self.tables[table_name] = table
                except Exception as e:
                    pass

    def _is_int(self, value):
        """Verifica si un string puede convertirse a entero."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_float(self, value):
        """Verifica si un string puede convertirse a flotante."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def select_from_table(
        self, selected_columns, table_name, where_clause=None, spatial_clause=None
    ):
        """
        Ejecuta una consulta SELECT.

        Params:
            selected_columns (list): Columnas a seleccionar.
            table_name (str): Tabla de consulta.
            where_clause (dict, optional): Condición de filtrado.
            spatial_clause (dict, optional): Condición espacial.

        Returns:
            list: Registros seleccionados según la consulta.
        """
        if table_name not in self.tables:
            return [], f"Tabla '{table_name}' no encontrada"

        table = self.tables[table_name]

        # Verificar columnas
        if selected_columns != ["*"]:
            for col in selected_columns:
                if col not in table.columns:
                    return [], f"Columna '{col}' no encontrada en tabla '{table_name}'"

        # Ejecutar consulta
        try:
            # Primero aplicar filtro espacial si existe
            if spatial_clause:
                spatial_type = spatial_clause.get("type")
                column = spatial_clause.get("column")

                if spatial_type == "within":
                    point = spatial_clause.get("point")
                    radius = spatial_clause.get("radius")
                    results = table.spatial_search(column, point, radius)

                elif spatial_type == "intersects":
                    geometry = spatial_clause.get("geometry")
                    results = table.intersection_search(column, geometry)

                elif spatial_type == "nearest":
                    point = spatial_clause.get("point")
                    limit = spatial_clause.get("limit", 1)
                    results = table.nearest_search(column, point, limit)

                elif spatial_type == "range":
                    min_point = spatial_clause.get("min_point")
                    max_point = spatial_clause.get("max_point")
                    results = table.range_search_spatial(column, min_point, max_point)

                else:
                    return [], f"Tipo de consulta espacial no soportado: {spatial_type}"

            # Luego aplicar filtro convencional
            elif where_clause:
                column = where_clause.get("column")

                if "operator" in where_clause:
                    operator = where_clause.get("operator")
                    value = where_clause.get("value")

                    if operator == "=":
                        result = table.search(column, value)
                        results = [result] if result else []
                    elif operator == "between":
                        begin_value = where_clause.get("begin_value")
                        end_value = where_clause.get("end_value")
                        results = table.range_search(column, begin_value, end_value)
                    else:
                        # Operadores !=, <, >, <=, >= requieren filtro secuencial
                        all_records = table.get_all()
                        results = []

                        for record in all_records:
                            record_val = record.get(column)

                            if operator == "!=":
                                if record_val != value:
                                    results.append(record)
                            elif operator == "<":
                                if record_val < value:
                                    results.append(record)
                            elif operator == ">":
                                if record_val > value:
                                    results.append(record)
                            elif operator == "<=":
                                if record_val <= value:
                                    results.append(record)
                            elif operator == ">=":
                                if record_val >= value:
                                    results.append(record)
                else:
                    return [], "Condición WHERE no válida"

            # Sin filtros, recuperar todos los registros
            else:
                results = table.get_all()

            # Filtrar solo las columnas solicitadas
            if selected_columns == ["*"]:
                return results, None
            else:
                filtered_results = []
                for record in results:
                    filtered_record = {
                        col: record[col] for col in selected_columns if col in record
                    }
                    filtered_results.append(filtered_record)
                return filtered_results, None

        except Exception as e:
            return [], f"Error en consulta: {e}"

    def insert_into_table(self, table_name, values):
        """
        Inserta un registro en una tabla.

        Params:
            table_name (str): Nombre de la tabla.
            values (list or dict): Valores a insertar.

        Returns:
            tuple: (bool, str) - Éxito y mensaje.
        """
        if table_name not in self.tables:
            return False, f"Tabla '{table_name}' no encontrada"

        table = self.tables[table_name]

        try:
            # Si values es una lista, convertir a diccionario usando nombres de columnas
            if isinstance(values, list):
                columns = table.get_column_names()

                if len(values) != len(columns):
                    return (
                        False,
                        f"Número incorrecto de valores. Se esperan {len(columns)} valores",
                    )

                record = dict(zip(columns, values))
            else:
                record = values

            # Validar que el registro contiene todas las columnas necesarias
            for col in table.columns:
                if col not in record:
                    return (
                        False,
                        f"Falta la columna '{col}' en los valores de inserción",
                    )

            # Intentar insertar
            table.add(record)
            return True, f"Registro insertado en tabla '{table_name}'"

        except Exception as e:
            return False, f"Error insertando registro: {e}"

    def delete_from_table(self, table_name, column=None, value=None):
        """
        Elimina registros de una tabla.

        Params:
            table_name (str): Nombre de la tabla.
            column (str): Columna para filtrar (debe ser primary key).
            value: Valor para filtrar.

        Returns:
            tuple: (bool, str) - Éxito y mensaje.
        """
        if table_name not in self.tables:
            return False, f"Tabla '{table_name}' no encontrada"

        table = self.tables[table_name]

        try:
            # Verificar que column es primary key
            if column and column != table.primary_key:
                return (
                    False,
                    f"Solo se puede eliminar por clave primaria ({table.primary_key})",
                )

            # Si no se especifica columna/valor, error (no se permite DELETE sin WHERE)
            if not column or value is None:
                return False, "Se requiere condición WHERE para DELETE"

            # Eliminar registro
            result = table.remove(column, value)

            if result:
                return (
                    True,
                    f"Registro con {column}={value} eliminado de '{table_name}'",
                )
            else:
                return False, f"No se encontró registro con {column}={value}"

        except Exception as e:
            return False, f"Error eliminando registro: {e}"

    def get_record_count(self, table_name):
        """
        Obtiene la cantidad de registros en una tabla específica.

        Params:
            table_name (str): Nombre de la tabla.

        Returns:
            int: Número de registros en la tabla, o None si la tabla no existe.
        """
        if table_name not in self.tables:
            return None

        table = self.tables[table_name]
        return table.get_record_count()

    def get_table_info(self, table_name):
        """
        Obtiene información detallada de una tabla.

        Params:
            table_name (str): Nombre de la tabla.

        Returns:
            str: Información formateada de la tabla, o None si no existe.
        """
        if table_name not in self.tables:
            return None

        table = self.tables[table_name]

        try:
            # Información básica
            info = f"Estructura de tabla: {table.name}\n"
            info += "=" * 50 + "\n"
            info += f"Registros: {table.get_record_count()}\n"
            info += f"Índice primario: {table.index_type} en '{table.primary_key}'\n\n"

            # Información de columnas
            info += "Columnas:\n"
            info += "-" * 50 + "\n"
            info += f"{'Nombre':<20} | {'Tipo':<15} | {'Clave':<5} | {'Índice':<15}\n"
            info += "-" * 50 + "\n"

            for col_name, col_type in table.columns.items():
                # Determinar si es clave primaria
                is_key = "PK" if col_name == table.primary_key else ""

                # Determinar tipo de índice
                index_info = ""
                if col_name == table.primary_key:
                    index_info = table.index_type
                elif (
                    hasattr(table, "spatial_columns")
                    and table.spatial_columns
                    and col_name in table.spatial_columns
                ):
                    index_info = "spatial"
                elif (
                    hasattr(table, "text_columns")
                    and table.text_columns
                    and col_name in table.text_columns
                ):
                    index_info = "invertido"
                else:
                    # Verificar si tiene índice multimedia
                    if (
                        hasattr(table, "indexes")
                        and table.indexes
                        and isinstance(table.indexes, dict)
                    ):
                        try:
                            for index_name, index_obj in table.indexes.items():
                                if (
                                    hasattr(index_obj, "column_name")
                                    and index_obj.column_name == col_name
                                    and hasattr(index_obj, "knn_search")
                                ):
                                    index_info = "multimedia"
                                    break
                        except Exception:
                            pass

                info += f"{col_name:<20} | {col_type:<15} | {is_key:<5} | {index_info:<15}\n"

            # Información de índices espaciales
            if hasattr(table, "spatial_columns") and table.spatial_columns:
                info += "\nÍndices espaciales:\n"
                info += "-" * 50 + "\n"
                try:
                    if hasattr(table, "get_spatial_index_stats"):
                        spatial_stats = table.get_spatial_index_stats()
                        if spatial_stats and isinstance(spatial_stats, dict):
                            for col, stats in spatial_stats.items():
                                count = (
                                    stats.get("count", "unknown")
                                    if isinstance(stats, dict)
                                    else "unknown"
                                )
                                info += f"Columna: {col} | Registros: {count}\n"
                        else:
                            for col in table.spatial_columns:
                                info += f"Columna: {col} | Registros: unknown\n"
                except Exception:
                    for col in table.spatial_columns:
                        info += f"Columna: {col} | Registros: error\n"

            # Información de índices multimedia
            if (
                hasattr(table, "indexes")
                and table.indexes
                and isinstance(table.indexes, dict)
            ):
                multimedia_indexes = []
                try:
                    for index_name, index_obj in table.indexes.items():
                        if hasattr(index_obj, "knn_search"):  # Es un MultimediaIndex
                            try:
                                multimedia_info = {
                                    "column": getattr(
                                        index_obj, "column_name", "unknown"
                                    ),
                                    "media_type": "unknown",
                                    "method": "unknown",
                                    "vector_count": 0,
                                }

                                # Obtener información del feature_extractor de forma segura
                                if (
                                    hasattr(index_obj, "feature_extractor")
                                    and index_obj.feature_extractor
                                ):
                                    multimedia_info["media_type"] = getattr(
                                        index_obj.feature_extractor,
                                        "media_type",
                                        "unknown",
                                    )
                                    multimedia_info["method"] = getattr(
                                        index_obj.feature_extractor, "method", "unknown"
                                    )

                                # Obtener conteo de vectores de forma segura
                                if hasattr(index_obj, "count"):
                                    try:
                                        multimedia_info["vector_count"] = (
                                            index_obj.count()
                                        )
                                    except:
                                        multimedia_info["vector_count"] = "error"

                                multimedia_indexes.append(multimedia_info)
                            except Exception:
                                continue
                except Exception:
                    pass

                if multimedia_indexes:
                    info += "\nÍndices multimedia:\n"
                    info += "-" * 50 + "\n"
                    for mm_idx in multimedia_indexes:
                        info += f"Columna: {mm_idx['column']} | Tipo: {mm_idx['media_type']} | Método: {mm_idx['method']} | Vectores: {mm_idx['vector_count']}\n"

            # Información del índice primario
            info += "\nÍndice primario:\n"
            info += "-" * 50 + "\n"
            try:
                if table.index_type == "bplus_tree":
                    height = (
                        getattr(table.index, "height", "unknown")
                        if hasattr(table, "index")
                        else "unknown"
                    )
                    order = (
                        getattr(table.index, "order", "unknown")
                        if hasattr(table, "index")
                        else "unknown"
                    )
                    info += f"height: {height}\norder: {order}\n"
                elif table.index_type == "sequential_file":
                    overflow_count = (
                        getattr(table.index, "overflow_count", "unknown")
                        if hasattr(table, "index")
                        else "unknown"
                    )
                    info += f"overflow_count: {overflow_count}\n"
                elif table.index_type == "extendible_hash":
                    global_depth = (
                        getattr(table.index, "global_depth", "unknown")
                        if hasattr(table, "index")
                        else "unknown"
                    )
                    buckets = "unknown"
                    if hasattr(table, "index") and hasattr(table.index, "directory"):
                        try:
                            buckets = len(set(table.index.directory.values()))
                        except:
                            buckets = "unknown"
                    info += f"global_depth: {global_depth}\nbuckets: {buckets}\n"
                else:
                    info += f"Tipo: {table.index_type}\n"
            except Exception as e:
                info += f"Error obteniendo información del índice: {str(e)}\n"

            return info

        except Exception as e:
            return f"Error obteniendo información de tabla: {e}"

    # Métodos adicionales para capacidades espaciales
    def create_spatial_index(self, table_name, column):
        """
        Crea un índice espacial para una columna existente.

        Params:
            table_name (str): Nombre de la tabla.
            column (str): Nombre de la columna para indexar espacialmente.

        Returns:
            tuple: (bool, str) - Éxito y mensaje.
        """
        if table_name not in self.tables:
            return False, f"Tabla '{table_name}' no encontrada"

        table = self.tables[table_name]

        if column not in table.columns:
            return False, f"Columna '{column}' no encontrada en tabla '{table_name}'"

        # Verificar que es un tipo espacial válido
        col_type = table.columns[column]
        if col_type not in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]:
            return False, f"La columna '{column}' no es un tipo espacial válido"

        # Añadir a columnas espaciales si no está ya
        if column not in table.spatial_columns:
            table.spatial_columns.append(column)
            table._create_spatial_indexes()
            table._save_metadata()
            return True, f"Índice espacial creado para la columna '{column}'"
        else:
            return False, f"Ya existe un índice espacial para la columna '{column}'"

    def drop_table(self, table_name):
        """
        Elimina una tabla de la base de datos incluyendo todos sus archivos asociados.

        Params:
            table_name (str): Nombre de la tabla a eliminar.

        Returns:
            tuple: (bool, str) - Éxito y mensaje informativo.
        """
        if table_name not in self.tables:
            return False, f"La tabla '{table_name}' no existe"

        try:
            # Inicializar variables de control
            files_deleted = 0
            errors = []

            # Obtener objeto de la tabla y rutas a archivos
            table = self.tables[table_name]

            # Eliminar archivos de datos y metadatos
            tables_path = os.path.join(self.data_dir, "tables")
            data_file = os.path.join(tables_path, f"{table_name}.dat")
            metadata_file = os.path.join(tables_path, f"{table_name}.json")

            # Eliminar archivos de índice primario
            index_files = []
            if table.index_type == "sequential":
                index_files.extend(
                    [
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_seq_index.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_seq_overflow.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_seq_metadata.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_seq_metadata.json",
                        ),
                    ]
                )
            elif table.index_type == "bplus_tree":
                index_files.extend(
                    [
                        os.path.join(
                            tables_path, f"{table_name}_{table.primary_key}_index.dat"
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_index_metadata.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_index_metadata.json",
                        ),
                    ]
                )
            elif table.index_type == "extendible_hash":
                index_files.extend(
                    [
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_hash_dir.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_hash_dir.json",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_hash_buckets.dat",
                        ),
                    ]
                )
            elif table.index_type == "isam_sparse":
                index_files.extend(
                    [
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_isam_index.dat",
                        ),
                        os.path.join(
                            tables_path,
                            f"{table_name}_{table.primary_key}_isam_index.json",
                        ),
                    ]
                )

            # Eliminar archivos de índices espaciales
            if hasattr(table, "spatial_columns") and table.spatial_columns:
                for col in table.spatial_columns:
                    rtree_path = os.path.join(self.data_dir, "indexes", "rtree")
                    spatial_files = [
                        os.path.join(rtree_path, f"{table_name}_{col}.dat"),
                        os.path.join(rtree_path, f"{table_name}_{col}.idx"),
                        os.path.join(rtree_path, f"{table_name}_{col}_metadata.json"),
                    ]
                    index_files.extend(spatial_files)

            # Eliminar archivos de índices multimedia
            if hasattr(table, "indexes") and table.indexes:
                for index_name, index_obj in table.indexes.items():
                    if hasattr(index_obj, "knn_search"):  # Es un MultimediaIndex
                        try:
                            # Eliminar archivos del VectorIndex
                            if (
                                hasattr(index_obj, "vector_index")
                                and index_obj.vector_index
                            ):
                                vector_files = [
                                    getattr(index_obj.vector_index, "index_file", ""),
                                    getattr(
                                        index_obj.vector_index, "metadata_file", ""
                                    ),
                                ]
                                index_files.extend([f for f in vector_files if f])

                            # Eliminar archivos del MultimediaStorage
                            if hasattr(index_obj, "storage") and index_obj.storage:
                                storage_dir = getattr(
                                    index_obj.storage, "storage_dir", ""
                                )
                                if storage_dir and os.path.exists(storage_dir):
                                    import shutil

                                    try:
                                        shutil.rmtree(storage_dir)
                                        files_deleted += 1
                                    except Exception as e:
                                        errors.append(
                                            f"Error eliminando directorio multimedia {storage_dir}: {e}"
                                        )

                            # Eliminar archivo de metadatos del MultimediaIndex
                            metadata_file_mm = getattr(index_obj, "metadata_file", "")
                            if metadata_file_mm:
                                index_files.append(metadata_file_mm)

                        except Exception as e:
                            errors.append(
                                f"Error eliminando índice multimedia {index_name}: {e}"
                            )

            # Eliminar archivos físicamente
            # Eliminar archivos de datos primero
            if os.path.exists(data_file):
                try:
                    os.remove(data_file)
                    files_deleted += 1
                except Exception as e:
                    errors.append(f"Error al eliminar {data_file}: {e}")

            if os.path.exists(metadata_file):
                try:
                    os.remove(metadata_file)
                    files_deleted += 1
                except Exception as e:
                    errors.append(f"Error al eliminar {metadata_file}: {e}")

            # Eliminar archivos de índices
            for file_path in index_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                    except Exception as e:
                        errors.append(f"Error al eliminar {file_path}: {e}")

            # Eliminar la tabla del diccionario de tablas
            del self.tables[table_name]

            if errors:
                return (
                    True,
                    f"Tabla '{table_name}' eliminada con algunas advertencias: {'; '.join(errors)}",
                )
            else:
                return (
                    True,
                    f"Tabla '{table_name}' eliminada completamente ({files_deleted} archivos eliminados)",
                )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, f"Error al eliminar tabla '{table_name}': {e}"

    def create_multimedia_index(
        self, table_name, column_name, media_type="image", method="sift"
    ):
        """
        Crea un índice multimedia para una columna existente.

        Params:
            table_name (str): Nombre de la tabla.
            column_name (str): Nombre de la columna multimedia.
            media_type (str): Tipo de media (image, audio, video).
            method (str): Método de extracción (sift, mfcc, etc.).

        Returns:
            tuple: (bool, str) - Éxito y mensaje.
        """
        if table_name not in self.tables:
            return False, f"Tabla '{table_name}' no encontrada"

        table = self.tables[table_name]

        if column_name not in table.columns:
            return (
                False,
                f"Columna '{column_name}' no encontrada en tabla '{table_name}'",
            )

        # Verificar que es un tipo multimedia válido
        col_type = table.columns[column_name]
        if col_type not in ["IMAGE", "AUDIO", "VIDEO"]:
            return False, f"La columna '{column_name}' no es un tipo multimedia válido"

        try:
            # Crear el índice multimedia
            multimedia_index = table.create_index(
                column_name, "multimedia", media_type=media_type, method=method
            )

            # Inicializar el índice
            multimedia_index.initialize(media_type=media_type, method=method)

            # ¡IMPORTANTE! Indexar todos los registros existentes
            print(f"DEBUG: Indexando registros existentes en tabla '{table_name}'...")
            records = table.get_all()
            print(f"DEBUG: Encontrados {len(records)} registros para indexar")
            print(
                f"DEBUG: Primeros 2 records: {records[:2] if len(records) > 0 else 'ninguno'}"
            )
            print(
                f"DEBUG: Tipo del primer record: {type(records[0]) if len(records) > 0 else 'ninguno'}"
            )

            for i, record in enumerate(records):
                try:
                    print(f"DEBUG: Tipo de record: {type(record)}")
                    print(
                        f"DEBUG: Record keys: {list(record.keys()) if isinstance(record, dict) else 'No es dict'}"
                    )
                    print(f"DEBUG: table.primary_key: {table.primary_key}")

                    if column_name in record and record[column_name]:
                        # Obtener la clave primaria del registro
                        key = (
                            record[table.primary_key]
                            if table.primary_key
                            else record.get("id", i + 1)
                        )

                        # Obtener el path de la imagen desde el registro
                        image_path = record[column_name]
                        if isinstance(image_path, bytes):
                            image_path = image_path.decode("utf-8").rstrip("\x00")

                        print(
                            f"DEBUG: Indexando registro {i+1}/{len(records)} - Key: {key}, Path: {image_path}"
                        )

                        # Agregar al índice multimedia (record completo y key)
                        multimedia_index.add(record, key)
                    else:
                        print(
                            f"DEBUG: Registro {i+1} no tiene columna {column_name} o está vacía"
                        )

                except Exception as e:
                    print(f"DEBUG: Error indexando registro {i+1}: {e}")
                    import traceback

                    traceback.print_exc()

            print(
                f"DEBUG: Indexación completada. Total vectores: {multimedia_index.count()}"
            )

            return True, f"Índice multimedia creado para la columna '{column_name}'"
        except Exception as e:
            return False, f"Error creando índice multimedia uwu: {e}"

    def get_multimedia_index_stats(self, table_name, column_name):
        """
        Obtiene estadísticas de un índice multimedia.

        Params:
            table_name (str): Nombre de la tabla.
            column_name (str): Nombre de la columna multimedia.

        Returns:
            dict: Estadísticas del índice o None si no existe.
        """
        if table_name not in self.tables:
            return None

        table = self.tables[table_name]

        # Buscar el índice multimedia
        if hasattr(table, "indexes") and table.indexes:
            for index_name, index_obj in table.indexes.items():
                if (
                    hasattr(index_obj, "column_name")
                    and index_obj.column_name == column_name
                ):
                    if hasattr(index_obj, "knn_search"):  # Es un MultimediaIndex
                        stats = {
                            "index_type": "multimedia",
                            "column": column_name,
                            "total_vectors": (
                                index_obj.count() if hasattr(index_obj, "count") else 0
                            ),
                            "media_type": (
                                getattr(
                                    index_obj.feature_extractor, "media_type", "unknown"
                                )
                                if hasattr(index_obj, "feature_extractor")
                                else "unknown"
                            ),
                            "method": (
                                getattr(
                                    index_obj.feature_extractor, "method", "unknown"
                                )
                                if hasattr(index_obj, "feature_extractor")
                                else "unknown"
                            ),
                            "vector_dimension": (
                                getattr(
                                    index_obj.feature_extractor,
                                    "get_vector_dimension",
                                    lambda: "unknown",
                                )()
                                if hasattr(index_obj, "feature_extractor")
                                else "unknown"
                            ),
                        }

                        # Estadísticas del almacenamiento multimedia
                        if hasattr(index_obj, "storage") and hasattr(
                            index_obj.storage, "get_storage_stats"
                        ):
                            try:
                                storage_stats = index_obj.storage.get_storage_stats()
                                stats.update(
                                    {
                                        "storage_files": storage_stats.get("files", 0),
                                        "storage_size": storage_stats.get(
                                            "total_size", 0
                                        ),
                                        "storage_dir": storage_stats.get(
                                            "storage_dir", "unknown"
                                        ),
                                    }
                                )
                            except:
                                pass

                        return stats

        return None
