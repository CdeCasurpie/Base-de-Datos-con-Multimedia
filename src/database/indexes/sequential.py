import os
import pickle
from ..index_base import IndexBase

class SequentialIndex(IndexBase):
    def __init__(self, table_name, column_name, data_path):
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        
        self.main_file = os.path.join(os.path.dirname(data_path), "indexes", f"{table_name}_{column_name}_seq.dat")
        self.aux_file = os.path.join(os.path.dirname(data_path), "indexes", f"{table_name}_{column_name}_seq_aux.dat")
        
        os.makedirs(os.path.dirname(self.main_file), exist_ok=True)
        
        if not os.path.exists(self.main_file):
            with open(self.main_file, 'wb') as f:
                pickle.dump([], f)
        
        if not os.path.exists(self.aux_file):
            with open(self.aux_file, 'wb') as f:
                pickle.dump([], f)
        
        self.max_aux_size = 10
    
    def search(self, key):
        pass
    
    def range_search(self, begin_key, end_key=None):
        pass
    
    def add(self, record):
        pass
    
    def remove(self, key):
        pass
    
    def rebuild(self):
        pass
    
    def get_all(self):
        pass
    
    def count(self):
        pass
    
    def _load_records(self, file_path):
        pass