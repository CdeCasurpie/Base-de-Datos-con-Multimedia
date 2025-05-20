import os
import struct
from database.index_base import IndexBase

class BPlusTree(IndexBase):
    """
    B+ Tree Index implementation for a table.
    This class is responsible for creating, searching, and managing the B+ tree index.
    """
    
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size
        self.index_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_index.dat")