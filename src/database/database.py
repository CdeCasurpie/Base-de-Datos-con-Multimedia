import os
import json
import sys
from .table import Table
from .parser import parse_query

class Database:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.tables = {}
        
        os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)
        
        self._load_tables()
    
    def create_table(self, table_name, columns, primary_key=None, index_type="sequential", spatial_columns=None, page_size=4096):
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
            start_time = __import__('time').time()
            
            table = Table(
                name=table_name,
                columns=columns,
                primary_key=primary_key,
                page_size=page_size,
                index_type=index_type,
                spatial_columns=spatial_columns
            )
            
            self.tables[table_name] = table
            
            elapsed = __import__('time').time() - start_time
            return True, f"Tabla '{table_name}' creada exitosamente en {elapsed:.3f}s"
        except Exception as e:
            return False, f"Error al crear tabla: {e}"

    def create_table_from_file(self, table_name, file_path, index_type="sequential", primary_key=None, page_size=4096):
        """
        Crea una tabla a partir de un archivo JSON o CSV.

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
            
            # Determinar tipo de archivo por extensión
            if file_path.lower().endswith('.json'):
                # Leer archivo JSON
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if not isinstance(data, list) or not data:
                    return False, "El archivo JSON debe contener una lista de registros"
                
                # Inferir estructura de columnas del primer registro
                first_record = data[0]
                columns = {}
                for col, value in first_record.items():
                    if isinstance(value, int):
                        columns[col] = "INT"
                    elif isinstance(value, float):
                        columns[col] = "FLOAT"
                    elif isinstance(value, bool):
                        columns[col] = "BOOLEAN"
                    elif isinstance(value, str):
                        # Detectar si es tipo espacial por formato WKT
                        if value.upper().startswith(('POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY')):
                            columns[col] = value.split('(')[0].upper()
                        else:
                            # Estimar longitud para VARCHAR
                            max_len = max(30, len(value) + 10)
                            columns[col] = f"VARCHAR({max_len})"
            
            elif file_path.lower().endswith('.csv'):
                # Leer archivo CSV
                with open(file_path, 'r') as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)  # Primera línea como cabeceras
                    
                    # Leer algunos registros para inferir tipos
                    sample_data = []
                    for i, row in enumerate(csv_reader):
                        if i >= 10:  # Limitar a 10 registros para análisis
                            break
                        sample_data.append(row)
                
                # Inferir tipos de columnas
                columns = {}
                for i, col in enumerate(headers):
                    # Analizar muestras de valores
                    sample_values = [row[i] for row in sample_data if i < len(row)]
                    
                    if all(self._is_int(val) for val in sample_values):
                        columns[col] = "INT"
                    elif all(self._is_float(val) for val in sample_values):
                        columns[col] = "FLOAT"
                    elif all(val.lower() in ('true', 'false', '1', '0') for val in sample_values):
                        columns[col] = "BOOLEAN"
                    else:
                        # Comprobar si es tipo espacial por formato WKT
                        if any(val.upper().startswith(('POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY')) 
                               for val in sample_values):
                            # Determinar tipo específico
                            for val in sample_values:
                                if val.upper().startswith(('POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY')):
                                    columns[col] = val.split('(')[0].upper()
                                    break
                        else:
                            # Estimar longitud para VARCHAR
                            max_len = max(30, max(len(val) for val in sample_values) + 10)
                            columns[col] = f"VARCHAR({max_len})"
                
                # Convertir datos CSV a formato JSON para carga
                data = []
                with open(file_path, 'r') as f:
                    csv_reader = csv.reader(f)
                    headers = next(csv_reader)
                    for row in csv_reader:
                        record = {}
                        for i, col in enumerate(headers):
                            if i < len(row):
                                val = row[i]
                                # Convertir según tipo inferido
                                col_type = columns[col]
                                if col_type == "INT":
                                    record[col] = int(val) if val else 0
                                elif col_type == "FLOAT":
                                    record[col] = float(val) if val else 0.0
                                elif col_type == "BOOLEAN":
                                    record[col] = val.lower() in ('true', '1')
                                else:
                                    record[col] = val
                        data.append(record)
            else:
                return False, "Formato de archivo no soportado. Use JSON o CSV."
            
            # Detectar columnas espaciales
            spatial_columns = [col for col, tipo in columns.items() 
                              if tipo in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]]
            
            # Si no se especificó primary_key, usar la primera columna
            if not primary_key and columns:
                primary_key = list(columns.keys())[0]
            
            # Crear la tabla
            table = Table(
                name=table_name,
                columns=columns,
                primary_key=primary_key,
                page_size=page_size,
                index_type=index_type,
                spatial_columns=spatial_columns
            )
            
            # Cargar datos
            records_loaded = 0
            for record in data:
                try:
                    table.add(record)
                    records_loaded += 1
                except Exception as e:
                    print(f"Error cargando registro: {e}")
            
            self.tables[table_name] = table
            
            return True, f"Tabla '{table_name}' creada con {records_loaded} registros de {len(data)}"
        
        except Exception as e:
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
            
            if parsed.get('error_message'):
                return None, parsed['error_message']
            
            query_type = parsed.get('type', '').upper()
            
            # CREATE TABLE
            if query_type == 'CREATE_TABLE':
                success, message = self.create_table(
                    table_name=parsed['table_name'],
                    columns=parsed['columns'],
                    primary_key=parsed['primary_key'],
                    index_type=parsed['index_type'],
                    spatial_columns=parsed.get('spatial_columns', [])
                )
                return message, not success 
            
            # CREATE TABLE FROM FILE
            elif query_type == 'CREATE_TABLE_FROM_FILE':
                success, message = self.create_table_from_file(
                    table_name=parsed['table_name'],
                    file_path=parsed['file_path'],
                    index_type=parsed['index_type'],
                    primary_key=parsed['primary_key']
                )
                return message, not success 
            
            # CREATE SPATIAL INDEX
            elif query_type == 'CREATE_SPATIAL_INDEX':
                table_name = parsed['table_name']
                column_name = parsed['column_name']
                
                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"
                
                table = self.tables[table_name]
                
                if column_name not in table.columns:
                    return None, f"Columna '{column_name}' no encontrada en tabla '{table_name}'"
                
                # Verificar que es un tipo espacial válido
                col_type = table.columns[column_name]
                if col_type not in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"] and not col_type.startswith("POINT") and not col_type.startswith("POLYGON"):
                    return None, f"La columna '{column_name}' no es un tipo espacial válido"
                
                # Añadir a columnas espaciales si no está ya
                if column_name not in table.spatial_columns:
                    table.spatial_columns.append(column_name)
                    table._create_spatial_indexes()
                    table._save_metadata()
                    return f"Índice espacial creado para '{column_name}'", None
                else:
                    return None, f"Ya existe un índice espacial para '{column_name}'"
            
            # SELECT
            elif query_type == 'SELECT':
                table_name = parsed['table_name']
                
                if table_name not in self.tables:
                    return None, f"Tabla '{table_name}' no encontrada"
                
                table = self.tables[table_name]
                
                # Determinar columnas a seleccionar
                if parsed['columns'] == '*':
                    selected_columns = table.get_column_names()
                else:
                    selected_columns = [col.strip() for col in parsed['columns'].split(',')]
                
                # Verificar columnas
                for col in selected_columns:
                    if col not in table.columns:
                        return None, f"Columna '{col}' no encontrada en tabla '{table_name}'"
                
                # Ejecutar búsqueda según tipo de condición
                if 'condition_type' in parsed:
                    condition = parsed['condition_type']
                    
                    # Búsqueda espacial - dentro de radio
                    if condition in ['SPATIAL_WITHIN', 'SPATIAL']:
                        column = parsed['column']
                        point = parsed['point']
                        radius = parsed['radius']
                        
                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"
                        
                        results = table.spatial_search(column, point, radius)
                    
                    # Búsqueda espacial - intersección
                    elif condition == 'SPATIAL_INTERSECTS':
                        column = parsed['column']
                        geometry = parsed['geometry']
                        
                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"
                        
                        results = table.intersection_search(column, geometry)
                    
                    # Búsqueda espacial - vecinos más cercanos
                    elif condition == 'SPATIAL_NEAREST':
                        column = parsed['column']
                        point = parsed['point']
                        limit = parsed['limit']
                        
                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"
                        
                        results = table.nearest_search(column, point, limit)
                    
                    # Búsqueda espacial - rango
                    elif condition == 'SPATIAL_RANGE':
                        column = parsed['column']
                        min_point = parsed['min_point']
                        max_point = parsed['max_point']
                        
                        if column not in table.spatial_columns:
                            return None, f"No hay índice espacial en columna '{column}'"
                        
                        results = table.range_search_spatial(column, min_point, max_point)
                    
                    # Búsqueda por rango
                    elif condition == 'RANGE':
                        column = parsed['column']
                        begin_value = parsed['begin_value']
                        end_value = parsed['end_value']
                        
                        results = table.range_search(column, begin_value, end_value)
                    
                    # Búsqueda por comparación
                    elif condition == 'COMPARISON':
                        column = parsed['column']
                        operator = parsed['operator']
                        value = parsed['value']
                        
                        if operator == '=':
                            results = table.search(column, value)
                            if not isinstance(results, list):
                                results = [results] if results else []
                        else:
                            # Para otros operadores, realizar búsqueda completa y filtrar
                            all_records = table.get_all()
                            results = []
                            
                            for record in all_records:
                                record_val = record.get(column)
                                
                                if operator == '!=':
                                    if record_val != value:
                                        results.append(record)
                                elif operator == '<':
                                    if record_val < value:
                                        results.append(record)
                                elif operator == '>':
                                    if record_val > value:
                                        results.append(record)
                                elif operator == '<=':
                                    if record_val <= value:
                                        results.append(record)
                                elif operator == '>=':
                                    if record_val >= value:
                                        results.append(record)
                    else:
                        return None, f"Tipo de condición no soportado: {condition}"
                    
                else:
                    # Sin condiciones, recuperar todos los registros
                    results = table.get_all()
                
                # Filtrar solo las columnas solicitadas
                filtered_results = []
                for record in results:
                    filtered_record = {col: record[col] for col in selected_columns if col in record}
                    filtered_results.append(filtered_record)
                
                return filtered_results, None
            
            # INSERT
            elif query_type == 'INSERT':
                table_name = parsed['table_name']
                values = parsed['values']
                
                success, message = self.insert_into_table(table_name, values)
                if success:
                    return f"Registro insertado en '{table_name}'", None
                else:
                    return None, message
            
            # DELETE
            elif query_type == 'DELETE':
                table_name = parsed['table_name']
                column = parsed['column']
                value = parsed['value']
                
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

    def select_from_table(self, selected_columns, table_name, where_clause=None, spatial_clause=None):
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
                    filtered_record = {col: record[col] for col in selected_columns if col in record}
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
                    return False, f"Número incorrecto de valores. Se esperan {len(columns)} valores"
                
                record = dict(zip(columns, values))
            else:
                record = values
            
            # Validar que el registro contiene todas las columnas necesarias
            for col in table.columns:
                if col not in record:
                    return False, f"Falta la columna '{col}' en los valores de inserción"
            
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
                return False, f"Solo se puede eliminar por clave primaria ({table.primary_key})"
            
            # Si no se especifica columna/valor, error (no se permite DELETE sin WHERE)
            if not column or value is None:
                return False, "Se requiere condición WHERE para DELETE"
            
            # Eliminar registro
            result = table.remove(column, value)
            
            if result:
                return True, f"Registro con {column}={value} eliminado de '{table_name}'"
            else:
                return False, f"No se encontró registro con {column}={value}"
            
        except Exception as e:
            return False, f"Error eliminando registro: {e}"

    def get_table_info(self, table_name):
        """
        Obtiene información detallada de una tabla.
        
        Params:
            table_name (str): Nombre de la tabla.
            
        Returns:
            dict: Información de la tabla, o None si no existe.
        """
        if table_name not in self.tables:
            return None
        
        table = self.tables[table_name]
        
        info = {
            "name": table.name,
            "columns": table.columns,
            "primary_key": table.primary_key,
            "index_type": table.index_type,
            "record_count": table.get_record_count(),
            "spatial_columns": table.spatial_columns
        }
        
        # Información de índices espaciales
        if table.spatial_columns:
            spatial_stats = table.get_spatial_index_stats()
            info["spatial_indexes"] = spatial_stats
        
        # Información del índice primario
        if table.index_type == "bplus_tree":
            info["index_info"] = {
                "height": getattr(table.index, "height", "unknown"),
                "order": getattr(table.index, "order", "unknown")
            }
        elif table.index_type == "sequential_file":
            info["index_info"] = {
                "overflow_count": getattr(table.index, "overflow_count", "unknown")
            }
        elif table.index_type == "extendible_hash":
            info["index_info"] = {
                "global_depth": getattr(table.index, "global_depth", "unknown"),
                "buckets": len(set(getattr(table.index, "directory", {}).values())) if hasattr(table.index, "directory") else "unknown"
            }
        
        return info

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