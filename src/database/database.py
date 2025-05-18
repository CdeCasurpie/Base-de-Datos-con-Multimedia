import os
import json
from .table import Table

class Database:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.tables = {}
        
        os.makedirs(os.path.join(data_dir, "tables"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "indexes"), exist_ok=True)
        
        self._load_tables()
    
    def create_table(self, table_name, columns, file_path=None, index_type="sequential"):
        pass
    
    def execute_query(self, query):
        pass
    
    def list_tables(self):
        pass
    
    def get_table(self, table_name):
        pass
    
    def _load_tables(self):
        pass