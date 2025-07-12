from abc import ABC, abstractmethod
import os


class IndexBase(ABC):
    """
    The index will have a index_File, that will be diferent from the data file.
    """

    @abstractmethod
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        """
        Initialize index with reference to its table for serialization/deserialization

        Params:
            table_name (str): Name of the table this index belongs to
            column_name (str): Name of the column being indexed
            data_path (str): Path to the table's data file
            table_ref (Table): Reference to the Table object for record serialization/deserialization and get record in pos
        """
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size
        pass

    @abstractmethod
    def search(self, key):
        """
        Search for a record with the specified key

        Params:
            key: The key to search for

        Returns:
            dict: The record found in the data file
        """
        pass

    @abstractmethod
    def range_search(self, begin_key, end_key=None):
        """
        Search for records with keys in the given range

        Params:
            begin_key: The start of the range (inclusive)
            end_key: The end of the range (inclusive) or None for open-ended

        Returns:
            list: List of records in the data file
        """
        pass

    @abstractmethod
    def add(self, record, key):
        """
        Add a record to the index

        Params:
            record: The record to add
            key: The key to index
        """
        pass

    @abstractmethod
    def remove(self, key):
        """
        Remove a record with the given key

        Params:
            key: The key to remove

        Returns:
            bool: True if record was removed, False if not found
        """
        pass

    @abstractmethod
    def rebuild(self):
        """
        Reorganize the index structure (e.g., after many updates)
        """
        pass

    @abstractmethod
    def get_all(self):
        """
        Get all record positions in the index

        Returns:
            list: List of all records in the data file
        """
        pass

    @abstractmethod
    def count(self):
        """
        Count the number of records in the index

        Returns:
            int: Number of records indexed
        """
        pass
