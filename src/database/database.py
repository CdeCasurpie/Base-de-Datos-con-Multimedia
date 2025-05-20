import os
import json
from table import Table

class Database:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.tables = {}
        
        os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)
        
        self._load_tables()
    
    def create_table(self, table_name, columns, index_type="sequential"):
        """
        Params:
            table_name (str): The name of the table to create.
            columns (list): A list of tuples representing the columns and their types.
            index_type (str, optional): The type of index to use. Defaults to "sequential".

        Returns:
            bool: True if the table was created successfully, False otherwise.
            string: An information message about the table creation (time, errors, etc.).
        """
        pass

    def create_table_from_file(self, table_name, file_path, index_type="sequential"):
        """
        Params:
            table_name (str): The name of the table to create.
            file_path (str): The path to the file containing the data.
            index_type (str, optional): The type of index to use. Defaults to "sequential".

        Returns:
            bool: True if the table was created successfully, False otherwise.

        The function should read the file and deduce the columns and types automatically.
        """
        pass
    
    def execute_query(self, query):
        """
        Params:
            query (str): The SQL-like query to execute.
        
        Returns:
            list: A list of results based on the query.
            error (str): An error message if the query fails.
        """
        pass
    
    def list_tables(self):
        """
        Returns:
            list: A list of table names in the database.
        """
        pass
    
    def get_table(self, table_name):
        """
        Params:
            table_name (str): The name of the table to retrieve.

        Returns:
            Table: An instance of the Table class representing the requested table.
        """
        pass
    
    def _load_tables(self):
        """
        Func:
            Loads all tables to self.tables from the metadata files in the data directory. (Uses get_table)
        """
        pass

    def select_from_table(self, selected_columns, table_name, where_clause=None):
        """
        Params:
            selected_columns (list): The columns to select from the table.
            table_name (str): The name of the table to select from.
            where_clause (str, optional): The condition to filter the results. Defaults to None.
            
        Returns:
            list: A list of selected rows from the table based on the query.
        """
        pass

    def insert_into_table(self, table_name, values):
        """
        Params:
            table_name (str): The name of the table to insert into.
            values (list): The values to insert into the table.
            
        Returns:
            bool: True if the insertion was successful, False otherwise.
        """
        pass

    def delete_from_table(self, table_name, where_clause=None):
        """
        Params:
            table_name (str): The name of the table to delete from.
            where_clause (str, optional): The condition to filter the rows to delete. Defaults to None.
            
        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        pass