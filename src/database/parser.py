import re

def parse_query(query):
    """
    Parser SQL para el sistema de base de datos con soporte espacial.
    
    Gramática soportada:
    
    CREATE_TABLE ::= "CREATE TABLE" table_name "(" column_definitions ")" [table_options]
    column_definitions ::= column_def ("," column_def)*
    column_def ::= column_name data_type [constraints]
    data_type ::= "INT" | "FLOAT" | "VARCHAR" "(" size ")" | "DATE" | "BOOLEAN" | 
                  "POINT" | "POLYGON" | "LINESTRING" | "GEOMETRY"
    constraints ::= "KEY" | "INDEX" index_type | "SPATIAL INDEX"
    table_options ::= "using index" index_type "(" column_name ")"
    
    CREATE_SPATIAL_INDEX ::= "CREATE SPATIAL INDEX" index_name "ON" table_name "(" column_name ")"
    
    DROP_TABLE ::= "DROP TABLE" table_name
    
    SELECT ::= "select" ("*" | column_list) "from" table_name [where_clause] [spatial_clause]
    column_list ::= column_name ("," column_name)*
    where_clause ::= "where" condition
    condition ::= column_name operator value | column_name "between" value "and" value
    spatial_clause ::= "where" spatial_condition
    spatial_condition ::= column_name "within" "(" point "," radius ")" |
                         column_name "intersects" geometry |
                         column_name "nearest" point ["limit" number] |
                         column_name "in_range" "(" min_point "," max_point ")"
    operator ::= "=" | "!=" | "<" | ">" | "<=" | ">="
    
    INSERT ::= "insert into" table_name "values" "(" value_list ")"
    value_list ::= value ("," value)*
    
    DELETE ::= "delete from" table_name "where" column_name "=" value
    
    LOAD ::= "create table" table_name "from file" file_path "using index" index_type "(" column_name ")"   
    
    Retorna siempre un diccionario con 'error_message' (None si no hay error).
    """
    
    query = query.strip()
    
    index_map = {
        'sequential': 'sequential',
        'seq': 'sequential',
        'sequential_index': 'sequential',
        'sequential_indexed': 'sequential',
        'sequential_indexed_table': 'sequential',
        'seq_index': 'sequential',
        'seq_idx': 'sequential',
        'bplus_tree': 'bplus_tree',
        'btree': 'bplus_tree',
        'b_tree': 'bplus_tree',
        'b_tree_index': 'bplus_tree',
        'bplus_tree_index': 'bplus_tree',
        'bplus': 'bplus_tree',
        'b_plus': 'bplus_tree',
        'extendible_hash': 'extendible_hash',
        'ext_hash': 'extendible_hash',
        'hash': 'extendible_hash',
        'hash_index': 'extendible_hash',
        'hash_table': 'extendible_hash',
        'isam_sparse': 'isam_sparse',
        'isam': 'isam_sparse',
        'isam_index': 'isam_sparse',
        'isam_sparse_index': 'isam_sparse',
        'isam_table': 'isam_sparse',
        'rtree': 'rtree',
        'rtree_sparse': 'rtree_sparse',
        'rtree_index': 'rtree',
        'rtree_table': 'rtree',
        'rtree_spatial': 'rtree',
        'rtree_spatial_index': 'rtree',
        'spatial': 'rtree'
    }

    try:
        # DROP TABLE
        drop_table_pattern = r'''
            DROP\s+TABLE\s+(\w+)
            \s*;?$
        '''
        
        match = re.match(drop_table_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            return {
                'type': 'DROP_TABLE',
                'table_name': match.group(1),
                'error_message': None
            }
            
        # CREATE INVERTED INDEX
        create_inverted_index_pattern = r'''
            CREATE\s+INVERTED\s+INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*(\w+)\s*\)
            \s*;?$
        '''
        
        match = re.match(create_inverted_index_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            return {
                'type': 'CREATE_INVERTED_INDEX',
                'index_name': match.group(1),
                'table_name': match.group(2),
                'column_name': match.group(3),
                'error_message': None
            }

        # CREATE SPATIAL INDEX
        spatial_index_pattern = r'''
            CREATE\s+SPATIAL\s+INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*(\w+)\s*\)
            \s*;?$
        '''
        
        match = re.match(spatial_index_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            return {
                'type': 'CREATE_SPATIAL_INDEX',
                'index_name': match.group(1),
                'table_name': match.group(2),
                'column_name': match.group(3),
                'error_message': None
            }

        # CREATE TABLE con definición completa de columnas (incluyendo tipos espaciales)
        create_table_pattern = r'''
            CREATE\s+TABLE\s+(\w+)\s*\(
            \s*(.+?)\s*
            \)\s*
            (?:using\s+index\s+(\w+)\s*\(\s*(\w+)\s*\))?
            \s*;?$
        '''
        
        match = re.match(create_table_pattern, query, re.IGNORECASE | re.VERBOSE | re.DOTALL)
        if match:
            table_name = match.group(1)
            columns_def = match.group(2)
            index_type = match.group(3) if match.group(3) else 'sequential'
            primary_key = match.group(4) if match.group(4) else None
            
            # Parsear definiciones de columnas
            columns = {}
            primary_key_found = None
            table_index_type = index_type
            spatial_columns = []
            
            # Dividir por comas, pero respetando paréntesis en VARCHAR y geometrías
            column_defs = []
            paren_count = 0
            bracket_count = 0
            current_def = ""
            
            for char in columns_def:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == ',' and paren_count == 0 and bracket_count == 0:
                    column_defs.append(current_def.strip())
                    current_def = ""
                    continue
                current_def += char
            
            if current_def.strip():
                column_defs.append(current_def.strip())
            
            # Parsear cada definición de columna
            for col_def in column_defs:
                col_def = col_def.strip()
                
                # Patrón flexible para diferentes combinaciones incluyendo SPATIAL INDEX:
                # column_name data_type [KEY] [INDEX index_type] [SPATIAL INDEX]
                col_pattern = r'''
                    (\w+)\s+                                                # column name
                    ((?:VARCHAR\(\d+\)|POINT|POLYGON|LINESTRING|GEOMETRY|\w+))\s*  # data type  
                    (?:(KEY)\s*)?                                           # optional KEY
                    (?:INDEX\s+(\w+)\s*)?                                   # optional INDEX type
                    (?:(SPATIAL\s+INDEX)\s*)?                               # optional SPATIAL INDEX
                '''
                
                col_match = re.match(col_pattern, col_def, re.IGNORECASE | re.VERBOSE)
                
                if col_match:
                    col_name = col_match.group(1)
                    data_type = col_match.group(2).upper()
                    is_key = col_match.group(3) is not None
                    col_index_type = col_match.group(4)
                    is_spatial_index = col_match.group(5) is not None
                    
                    columns[col_name] = data_type
                    
                    if is_key:
                        primary_key_found = col_name
                        if col_index_type:
                            table_index_type = col_index_type.lower()
                            table_index_type = index_map.get(table_index_type, 'sequential')
                    
                    # Si tiene SPATIAL INDEX o es un tipo espacial, agregarlo a spatial_columns
                    if is_spatial_index or data_type in ['POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY']:
                        spatial_columns.append(col_name)
                        
                else:
                    # Si no coincide el patrón completo, intentar patrón más simple
                    simple_pattern = r'(\w+)\s+((?:VARCHAR\(\d+\)|POINT|POLYGON|LINESTRING|GEOMETRY|\w+))'
                    simple_match = re.match(simple_pattern, col_def, re.IGNORECASE)
                    if simple_match:
                        col_name = simple_match.group(1)
                        data_type = simple_match.group(2).upper()
                        columns[col_name] = data_type
                        
                        # Si es tipo espacial, agregarlo automáticamente
                        if data_type in ['POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY']:
                            spatial_columns.append(col_name)
            
            # Si no se especificó primary key en using clause, usar el encontrado con KEY
            if not primary_key and primary_key_found:
                primary_key = primary_key_found
            
            # Si aún no hay primary key, usar la primera columna
            if not primary_key and columns:
                primary_key = list(columns.keys())[0]
            
            return {
                'type': 'CREATE_TABLE',
                'table_name': table_name,
                'columns': columns,
                'primary_key': primary_key,
                'index_type': table_index_type,
                'spatial_columns': spatial_columns,
                'error_message': None
            }
        
        # CREATE TABLE desde archivo
        create_from_file_pattern = r'''
            create\s+table\s+(\w+)\s+from\s+file\s+
            ['"]([^'"]+)['"]
            \s+using\s+index\s+(\w+)\s*\(\s*['"]?(\w+)['"]?\s*\)
            \s*;?$
        '''
        
        match = re.match(create_from_file_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            return {
                'type': 'CREATE_TABLE_FROM_FILE',
                'table_name': match.group(1),
                'file_path': match.group(2),
                'index_type': index_map.get(match.group(3).lower(), 'sequential'),
                'primary_key': match.group(4),
                'error_message': None
            }
        
        # SELECT con soporte para consultas espaciales
        select_pattern = r'''
            select\s+(\*|[\w\s,]+)\s+from\s+(\w+)
            (?:\s+where\s+(.+?))?
            \s*;?$
        '''
        
        match = re.match(select_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            columns = match.group(1).strip()
            table_name = match.group(2)
            where_clause = match.group(3)
            
            result = {
                'type': 'SELECT',
                'columns': columns,
                'table_name': table_name,
                'error_message': None
            }
            
            if where_clause:
                # Parsear condición WHERE (incluyendo espaciales)
                where_condition = parse_where_clause(where_clause)
                if where_condition.get('error_message'):
                    return {
                        'type': 'SELECT',
                        'error_message': f"Error en WHERE clause: {where_condition['error_message']}",
                        'error_location': 'WHERE clause'
                    }
                result.update(where_condition)
            
            return result
        
        # INSERT
        insert_pattern = r'''
            insert\s+into\s+(\w+)\s+values\s*\(
            \s*(.+?)\s*
            \)\s*;?$
        '''
        
        match = re.match(insert_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            table_name = match.group(1)
            values_str = match.group(2)
            
            # Parsear valores
            values = parse_values(values_str)
            
            return {
                'type': 'INSERT',
                'table_name': table_name,
                'values': values,
                'error_message': None
            }
        
        # DELETE
        delete_pattern = r'''
            delete\s+from\s+(\w+)\s+where\s+
            (\w+)\s*=\s*(.+?)
            \s*;?$
        '''
        
        match = re.match(delete_pattern, query, re.IGNORECASE | re.VERBOSE)
        if match:
            return {
                'type': 'DELETE',
                'table_name': match.group(1),
                'column': match.group(2),
                'value': parse_value(match.group(3).strip()),
                'error_message': None
            }
        
        # Si no coincide con ningún patrón
        return {
            'type': 'UNKNOWN',
            'error_message': 'Consulta no reconocida - sintaxis incorrecta',
            'error_location': 'Query syntax',
            'query': query
        }
        
    except Exception as e:
        return {
            'type': 'ERROR',
            'error_message': f'Error interno del parser: {str(e)}',
            'error_location': 'Parser internal error',
            'query': query
        }


def parse_where_clause(where_clause):
    """
    Parsea la cláusula WHERE y retorna información sobre la condición.
    Incluye soporte para condiciones espaciales.
    
    Tipos de condiciones soportadas:
    - column = value (comparación estándar)
    - column != value  
    - column < value, column > value, column <= value, column >= value
    - column between value1 and value2 (rango)
    - column within (point, radius) (búsqueda espacial por radio)
    - column intersects geometry (intersección geométrica)
    - column nearest point [limit k] (k vecinos más cercanos)
    - column in_range (min_point, max_point) (rango espacial)
    - column CONTAINS term (búsqueda de texto por término)
    - column CONTAINS term1 AND/OR term2 (búsqueda booleana de texto)
    - column RANKED BY query (búsqueda por relevancia de texto)
    
    Retorna diccionario con 'error_message' (None si no hay error).
    """
    where_clause = where_clause.strip()
    
    try:
        # Búsqueda de texto: CONTAINS para términos simples o operadores booleanos
        contains_pattern = r'(\w+)\s+CONTAINS\s+([\'"]?.+?[\'"]?)$'
        match = re.match(contains_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            query = match.group(2).strip()
            
            # Eliminar comillas si existen
            if (query.startswith('"') and query.endswith('"')) or \
               (query.startswith("'") and query.endswith("'")):
                query = query[1:-1]
            
            return {
                'condition_type': 'TEXT_CONTAINS',
                'column': column,
                'query': query,
                'error_message': None
            }
        
        # Búsqueda de texto por relevancia: RANKED BY
        ranked_pattern = r'(\w+)\s+RANKED\s+BY\s+([\'"]?.+?[\'"]?)(?:\s+LIMIT\s+(\d+))?$'
        match = re.match(ranked_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            query = match.group(2).strip()
            limit = int(match.group(3)) if match.group(3) else 5  # Default limit 5
            
            # Eliminar comillas si existen
            if (query.startswith('"') and query.endswith('"')) or \
               (query.startswith("'") and query.endswith("'")):
                query = query[1:-1]
            
            return {
                'condition_type': 'TEXT_RANKED',
                'column': column,
                'query': query,
                'limit': limit,
                'error_message': None
            }
            
        # Búsqueda espacial: WITHIN (punto, radio)
        within_pattern = r'(\w+)\s+within\s*\(\s*(.+?)\s*,\s*(\d+(?:\.\d+)?)\s*\)'
        match = re.match(within_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            point_str = match.group(2)
            radius = float(match.group(3))
            
            # Parsear punto - puede ser (x, y) o POINT(x y)
            point = parse_spatial_value(point_str)
            
            return {
                'condition_type': 'SPATIAL_WITHIN',
                'column': column,
                'point': point,
                'radius': radius,
                'error_message': None
            }
        
        # Búsqueda por intersección: INTERSECTS
        intersects_pattern = r'(\w+)\s+intersects\s+(.+?)$'
        match = re.match(intersects_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            geometry_str = match.group(2)
            geometry = parse_spatial_value(geometry_str)
            
            return {
                'condition_type': 'SPATIAL_INTERSECTS',
                'column': column,
                'geometry': geometry,
                'error_message': None
            }
        
        # Búsqueda de vecinos más cercanos: NEAREST
        nearest_pattern = r'(\w+)\s+nearest\s+(.+?)(?:\s+limit\s+(\d+))?$'
        match = re.match(nearest_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            point_str = match.group(2)
            limit = int(match.group(3)) if match.group(3) else 1
            
            point = parse_spatial_value(point_str)
            
            return {
                'condition_type': 'SPATIAL_NEAREST',
                'column': column,
                'point': point,
                'limit': limit,
                'error_message': None
            }
        
        # Búsqueda por rango espacial: IN_RANGE
        range_spatial_pattern = r'(\w+)\s+in_range\s*\(\s*(.+?)\s*,\s*(.+?)\s*\)'
        match = re.match(range_spatial_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            min_point_str = match.group(2)
            max_point_str = match.group(3)
            
            min_point = parse_spatial_value(min_point_str)
            max_point = parse_spatial_value(max_point_str)
            
            return {
                'condition_type': 'SPATIAL_RANGE',
                'column': column,
                'min_point': min_point,
                'max_point': max_point,
                'error_message': None
            }
        
        # Búsqueda espacial original: IN (point, radius) para compatibilidad
        spatial_pattern = r'(\w+)\s+in\s*\(\s*\(([^)]+)\)\s*,\s*(\d+(?:\.\d+)?)\s*\)'
        match = re.match(spatial_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            point_coords = [float(x.strip()) for x in match.group(2).split(',')]
            radius = float(match.group(3))
            
            return {
                'condition_type': 'SPATIAL',
                'column': column,
                'point': tuple(point_coords),
                'radius': radius,
                'error_message': None
            }
        
        # BETWEEN condition
        between_pattern = r'(\w+)\s+between\s+(.+?)\s+and\s+(.+?)$'
        match = re.match(between_pattern, where_clause, re.IGNORECASE)
        if match:
            return {
                'condition_type': 'RANGE',
                'column': match.group(1),
                'begin_value': parse_value(match.group(2).strip()),
                'end_value': parse_value(match.group(3).strip()),
                'error_message': None
            }
        
        # Operadores de comparación
        comparison_pattern = r'(\w+)\s*(=|!=|<>|<=|>=|<|>)\s*(.+?)$'
        match = re.match(comparison_pattern, where_clause, re.IGNORECASE)
        if match:
            operator = match.group(2)
            # Normalizar operador
            if operator == '<>':
                operator = '!='
                
            return {
                'condition_type': 'COMPARISON',
                'column': match.group(1),
                'operator': operator,
                'value': parse_value(match.group(3).strip()),
                'error_message': None
            }
        
        return {
            'condition_type': 'ERROR',
            'error_message': f'Condición WHERE no reconocida: {where_clause}',
            'error_location': 'WHERE clause syntax'
        }
        
    except Exception as e:
        return {
            'condition_type': 'ERROR',
            'error_message': f'Error parseando WHERE clause: {str(e)}',
            'error_location': 'WHERE clause parsing'
        }


def parse_spatial_value(value_str):
    """
    Parsea valores espaciales en diferentes formatos:
    - (x, y) -> tupla
    - POINT(x y) -> tupla
    - 'POLYGON(...)' -> string WKT
    - etc.
    """
    value_str = value_str.strip()
    
    # Formato (x, y)
    if value_str.startswith('(') and value_str.endswith(')'):
        coords_str = value_str[1:-1]
        coords = [float(x.strip()) for x in coords_str.split(',')]
        return tuple(coords)
    
    # Formato WKT: POINT(x y), POLYGON(...), etc.
    if value_str.upper().startswith(('POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY')):
        return value_str  # Retornar como string WKT
    
    # Si está entre comillas, es un string WKT
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    # Intentar parsear como coordenadas separadas por espacio (formato WKT interno)
    try:
        coords = [float(x) for x in value_str.split()]
        if len(coords) == 2:
            return tuple(coords)
    except ValueError:
        pass
    
    # Si no se puede parsear, retornar como string
    return value_str


def parse_values(values_str):
    """
    Parsea una lista de valores separados por comas.
    Maneja strings entre comillas, números, booleanos, geometrías WKT, etc.
    """
    values = []
    current_value = ""
    in_quotes = False
    quote_char = None
    paren_count = 0
    
    i = 0
    while i < len(values_str):
        char = values_str[i]
        
        if char in ['"', "'"] and not in_quotes:
            in_quotes = True
            quote_char = char
            i += 1
            continue
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
            i += 1
            continue
        elif char == '(' and not in_quotes:
            paren_count += 1
        elif char == ')' and not in_quotes:
            paren_count -= 1
        elif char == ',' and not in_quotes and paren_count == 0:
            values.append(parse_value(current_value.strip()))
            current_value = ""
            i += 1
            continue
        
        current_value += char
        i += 1
    
    if current_value.strip():
        values.append(parse_value(current_value.strip()))
    
    return values


def parse_value(value_str):
    """
    Parsea un valor individual y retorna el tipo correcto de dato.
    Incluye soporte para geometrías WKT.
    """
    value_str = value_str.strip()
    
    # Null
    if value_str.lower() == 'null':
        return None
    
    # Boolean
    if value_str.lower() == 'true':
        return True
    elif value_str.lower() == 'false':
        return False
    
    # Geometrías WKT
    if value_str.upper().startswith(('POINT', 'POLYGON', 'LINESTRING', 'GEOMETRY')):
        return value_str
    
    # String entre comillas
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    # Array/Tuple notation (x, y) para puntos
    if value_str.startswith('(') and value_str.endswith(')'):
        inner = value_str[1:-1]
        try:
            elements = [parse_value(elem.strip()) for elem in inner.split(',')]
            return tuple(elements)
        except:
            return value_str
    
    # Número flotante
    if '.' in value_str:
        try:
            return float(value_str)
        except ValueError:
            pass
    
    # Número entero
    try:
        return int(value_str)
    except ValueError:
        pass
    
    # Si no se puede parsear como otro tipo, retornar como string
    return value_str


# Función de prueba
if __name__ == "__main__":
    # Ejemplos de prueba con soporte espacial
    test_queries = [
        # CREATE TABLE con tipos espaciales
        """CREATE TABLE Restaurantes (
            id INT KEY INDEX SEQ,
            nombre VARCHAR(20) INDEX BTree,
            fechaRegistro DATE,
            ubicacion POINT SPATIAL INDEX
        );""",
        
        # CREATE SPATIAL INDEX
        "CREATE SPATIAL INDEX idx_ubicacion ON Restaurantes (ubicacion);",
        
        # CREATE TABLE desde archivo
        "create table Restaurantes from file 'C:\\restaurantes.csv' using index isam('id')",
        
        # SELECT con búsqueda espacial - WITHIN
        "select * from Restaurantes where ubicacion within ((40.7128, -74.0060), 5.0)",
        
        # SELECT con búsqueda espacial - INTERSECTS
        "select nombre from Restaurantes where ubicacion intersects 'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))'",
        
        # SELECT con búsqueda de vecinos más cercanos
        "select * from Restaurantes where ubicacion nearest (40.7128, -74.0060) limit 3",
        
        # SELECT con rango espacial
        "select * from Restaurantes where ubicacion in_range ((0, 0), (50, 50))",
        
        # SELECT tradicional
        "select * from Restaurantes where id = 5",
        
        # INSERT con geometría
        "insert into Restaurantes values (1, 'Pizza Hut', '2023-01-15', 'POINT(40.7128 -74.0060)')",
        
        # DELETE
        "delete from Restaurantes where id = 5",
        
        # SELECT con búsqueda espacial original (compatibilidad)
        "select * from Restaurantes where ubicacion in ((40.7128, -74.0060), 5.0)"
    ]
    
    for query in test_queries:
        try:
            result = parse_query(query)
            print(f"Query: {query}")
            if result.get('error_message'):
                print(f"ERROR: {result['error_message']}")
                if result.get('error_location'):
                    print(f"Location: {result['error_location']}")
            else:
                print(f"Parsed: {result}")
            print("-" * 50)
        except Exception as e:
            print(f"Unexpected error parsing: {query}")
            print(f"Error: {e}")
            print("-" * 50)