import re

def parse_query(query):
    query = query.strip()
    
    # CREATE TABLE
    create_match = re.match(r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);?', query, re.IGNORECASE | re.DOTALL)
    if create_match:
        pass
    
    # CREATE TABLE FROM FILE
    create_file_match = re.match(r'CREATE\s+TABLE\s+(\w+)\s+FROM\s+(?:FILE\s+)?[\'"](.*?)[\'"]\s+USING\s+INDEX\s+(\w+)(?:\([\'"](.*?)[\'"]\))?;?', query, re.IGNORECASE)
    if create_file_match:
        pass
    
    # SELECT
    select_match = re.match(r'SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?;?', query, re.IGNORECASE)
    if select_match:
        pass
    
    # INSERT
    insert_match = re.match(r'INSERT\s+INTO\s+(\w+)\s+VALUES\s+\((.*?)\);?', query, re.IGNORECASE)
    if insert_match:
        pass
    
    # DELETE
    delete_match = re.match(r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?;?', query, re.IGNORECASE)
    if delete_match:
        pass
    
    # Si no coincide con ningún patrón
    raise ValueError(f"Consulta no reconocida: {query}")