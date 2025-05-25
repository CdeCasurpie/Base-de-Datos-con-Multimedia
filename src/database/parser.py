import re

def parse_query(query):
    """
    Parser SQL para el sistema de base de datos.
    
    Gramática soportada:
    
    CREATE_TABLE ::= "CREATE TABLE" table_name "(" column_definitions ")" [table_options]
    column_definitions ::= column_def ("," column_def)*
    column_def ::= column_name data_type [constraints]
    data_type ::= "INT" | "FLOAT" | "VARCHAR" "(" size ")" | "DATE" | "BOOLEAN" | "ARRAY" "[" data_type "]"
    constraints ::= "KEY" | "INDEX" index_type
    table_options ::= "using index" index_type "(" column_name ")"
    
    SELECT ::= "select" ("*" | column_list) "from" table_name [where_clause] [spatial_clause]
    column_list ::= column_name ("," column_name)*
    where_clause ::= "where" condition
    condition ::= column_name operator value | column_name "between" value "and" value
    spatial_clause ::= "where" column_name "in" "(" point "," radius ")"
    operator ::= "=" | "!=" | "<" | ">" | "<=" | ">="
    
    INSERT ::= "insert into" table_name "values" "(" value_list ")"
    value_list ::= value ("," value)*
    
    DELETE ::= "delete from" table_name "where" column_name "=" value
    
    LOAD ::= "create table" table_name "from file" file_path "using index" index_type "(" column_name ")"
    
    Retorna siempre un diccionario con 'error_message' (None si no hay error).
    """
    
    query = query.strip()
    
    try:
        
        # CREATE TABLE con definición completa de columnas
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
            
            # Dividir por comas, pero respetando paréntesis en VARCHAR y ARRAY
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
                
                # Patrón más flexible para diferentes combinaciones:
                # column_name data_type [KEY] [INDEX index_type]
                # column_name data_type [INDEX index_type]
                col_pattern = r'''
                    (\w+)\s+                                    # column name
                    ((?:VARCHAR\(\d+\)|ARRAY\[\w+\]|\w+))\s*    # data type  
                    (?:(KEY)\s*)?                               # optional KEY
                    (?:INDEX\s+(\w+))?                          # optional INDEX type
                '''
                
                col_match = re.match(col_pattern, col_def, re.IGNORECASE | re.VERBOSE)
                
                if col_match:
                    col_name = col_match.group(1)
                    data_type = col_match.group(2).upper()
                    is_key = col_match.group(3) is not None
                    col_index_type = col_match.group(4)
                    
                    columns[col_name] = data_type
                    
                    if is_key:
                        primary_key_found = col_name
                        if col_index_type:
                            table_index_type = col_index_type.lower()
                            # Mapear nombres de índices
                            if table_index_type == 'seq':
                                table_index_type = 'sequential'
                            elif table_index_type == 'btree':
                                table_index_type = 'bplus_tree'
                            elif table_index_type == 'rtree':
                                table_index_type = 'rtree'
                else:
                    # Si no coincide el patrón completo, intentar patrón más simple
                    simple_pattern = r'(\w+)\s+((?:VARCHAR\(\d+\)|ARRAY\[\w+\]|\w+))'
                    simple_match = re.match(simple_pattern, col_def, re.IGNORECASE)
                    if simple_match:
                        col_name = simple_match.group(1)
                        data_type = simple_match.group(2).upper()
                        columns[col_name] = data_type
            
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
                'index_type': match.group(3).lower(),
                'primary_key': match.group(4),
                'error_message': None
            }
        
        # SELECT simple
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
                # Parsear condición WHERE
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
    
    Tipos de condiciones soportadas:
    - column = value
    - column != value  
    - column < value
    - column > value
    - column <= value
    - column >= value
    - column between value1 and value2
    - column in (point, radius)  # Para búsqueda espacial
    
    Retorna diccionario con 'error_message' (None si no hay error).
    """
    where_clause = where_clause.strip()
    
    try:
    
        # Búsqueda espacial: column in (point, radius)
        spatial_pattern = r'(\w+)\s+in\s*\(\s*\(([^)]+)\)\s*,\s*(\d+(?:\.\d+)?)\s*\)'
        match = re.match(spatial_pattern, where_clause, re.IGNORECASE)
        if match:
            column = match.group(1)
            point_str = match.group(2)
            radius = float(match.group(3))
            
            # Parsear punto (x, y)
            point_coords = [float(x.strip()) for x in point_str.split(',')]
            
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


def parse_values(values_str):
    """
    Parsea una lista de valores separados por comas.
    Maneja strings entre comillas, números, booleanos, etc.
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
    
    # String entre comillas
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    # Array/Tuple notation (x, y)
    if value_str.startswith('(') and value_str.endswith(')'):
        inner = value_str[1:-1]
        elements = [parse_value(elem.strip()) for elem in inner.split(',')]
        return tuple(elements)
    
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


if __name__ == "__main__":
    test_queries = [
        """CREATE TABLE Restaurantes (
            id INT KEY INDEX SEQ,
            nombre VARCHAR(20) INDEX BTree,
            fechaRegistro DATE,
            ubicacion ARRAY[FLOAT] INDEX RTree
        );""",
        
        "create table Restaurantes from file 'C:\\restaurantes.csv' using index isam('id')",
        
        "select * from Restaurantes where id = x",
        
        "select * from Restaurantes where nombre between x and y",
        
        "insert into Restaurantes values (1, 'Pizza Hut', '2023-01-15', (40.7128, -74.0060))",
        
        "delete from Restaurantes where id = 5",
        
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

    print("All tests completed.")

    while True:
        user_query = input("Ingrese una consulta SQL para analizar (o 'exit' para salir): ")
        if user_query.lower() == 'exit':
            break
        result = parse_query(user_query)
        if result.get('error_message'):
            print(f"ERROR: {result['error_message']}")
            if result.get('error_location'):
                print(f"Location: {result['error_location']}")
        else:
            print(f"Parsed: {result}")
    
