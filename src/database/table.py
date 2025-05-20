import os
import json
import struct
import pickle


class Table:
    DATA_TYPES = {
        "INT": {"size": 4, "format": "i"},
        "FLOAT": {"size": 8, "format": "d"},
        "VARCHAR": {"variable": True},
        "DATE": {"size": 8, "format": "q"},
        "BOOLEAN": {"size": 1, "format": "?"},
        "ARRAY": {"variable": True}
    }

    def _get_single_data_pack_string(self, col_type):
        """
        Returns the pack string for a single data type.
        
        Params:
            col_type (str): The data type of the column.
        
        Returns:
            str: The pack string for the specified data type.
        """
        if col_type in self.DATA_TYPES:
            return self.DATA_TYPES[col_type]["format"]
        elif col_type.startswith("VARCHAR"):
            size = int(col_type.split("(")[1].split(")")[0])
            return f"{size}s"
        else:
            raise ValueError(f"Unsupported data type: {col_type}")
        
    def __init__(self, name, columns, primary_key, page_size, index_type="sequential", file_path=None, data_dir=os.path.join(os.getcwd(), "data")):
        self.name = name
        self.columns = columns
        self.index_type = index_type
        self.primary_key = primary_key
        self.page_size = page_size
        
        self.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        self.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        self.record_count = 0

        # el pack string es el que se usa para serializar los datos:
        self.pack_string = "".join([self._get_single_data_pack_string(col_type) for col_type in columns.values()])
        self._create_primary_index()
        self._save_metadata()
        
        if file_path:
            self._load_from_file(file_path)
    
    @classmethod
    def from_table_name(cls, name, page_size, data_dir=os.path.join(os.getcwd(), "data")):
        """
        Params:
            name (str): The name of the table.
            metadata (dict): The metadata dictionary containing column names and types.
            data_dir (str): The directory where the table data is stored.
       
        Returns:
            Table: An instance of the Table class.
        """
        

        metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        columns = metadata.get("columns", {})
        index_type = metadata.get("index_type", "sequential")
        table = cls(name, columns, index_type, data_dir=data_dir)
        table.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        table.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        table.metadata = metadata
        table.pack_string = metadata.get("pack_string", "")
        table.record_count = metadata.get("record_count", 0)
        table.index_type = index_type
        table.columns = columns
        table.primary_key = metadata.get("primary_key", None)
        table.page_size = page_size
        
        return table
    
    def _create_primary_index(self):
        """
        This method will create the index for the table based on the specified index type.
        """
        pass
    
    def _save_metadata(self):
        """
        Save the table metadata to a JSON file.
        """
        metadata = {
            "name": self.name,
            "columns": self.columns,
            "index_type": self.index_type,
            "primary_key": self.primary_key,
            "record_count": self.record_count,
            "pack_string": self.pack_string,
        }
        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        pass
    
    def _load_from_file(self, file_path):
        """
        Params:
            file_path (str): The path to the file to load data from.
        
        Returns:
            None
        """
        pass
    
    def search(self, column, value):
        pass
    
    def range_search(self, column, begin_key, end_key):
        pass
    
    def spatial_search(self, column, point, radius):
        pass
    
    def add(self, record):
        pass
    
    def remove(self, column, value):
        pass
    
    def get_column_names(self):
        """
        Returns:
            list: A list of column names in the table.
        """
        return list(self.columns.keys())
    
    def get_column_info(self):
        """
        Returns:
            list: A list of tuples containing column names and their types.
        """
        return [(name, self.columns[name]) for name in self.columns]
    
    def get_record_count(self):
        """
        Returns:
            int: The number of records in the table.
        """
        return self.record_count
    
    def get_all(self):
        """
        Returns:
            list: A list of all records in the table.
        """
        pass
    
    def _serialize_record(self, record):
        values = []
        for col_name, col_type in self.columns.items():
            value = record[col_name]
            fmt = self._get_single_data_pack_string(col_type)

            if 's' in fmt:  # Es VARCHAR
                size = int(fmt[:-1])
                encoded = value.encode('utf-8')
                if len(encoded) > size:
                    raise ValueError(f"Value for {col_name} exceeds VARCHAR({size}) limit")
                values.append(encoded.ljust(size, b'\x00'))
            else:
                values.append(value)

        return struct.pack(self.pack_string, *values)

    
    def _deserialize_record(self, bytes_data):
        """
        Params:
            bytes_data (bytes): The serialized record as bytes.
        
        Returns:
            dict: The deserialized record as a dictionary.
        """ 
        # el unpack retorna una tupla con los datos
        unpacked_data = struct.unpack(self.pack_string, bytes_data)

        # Convert the unpacked data to a dictionary
        record = {}
        offset = 0
        for col_name, col_type in self.columns.items():
            if col_type in self.DATA_TYPES:
                record[col_name] = unpacked_data[offset]
                offset += 1
            elif col_type.startswith("VARCHAR"):
                size = int(col_type.split("(")[1].split(")")[0])
                record[col_name] = unpacked_data[offset].decode('utf-8').rstrip('\x00')
                offset += 1
            else:
                raise ValueError(f"Unsupported data type: {col_type}")



if __name__ == "__main__":
    # Example usage
    table = Table(name="example_table", columns={"id": "INT", "name": "VARCHAR(100)"}, primary_key="id", page_size=4096) # page_size of 4096 
    print(table.get_column_names())
    print(table.get_column_info())
    print(table.get_record_count())
    print(table.pack_string)

    table2 = Table.from_table_name("example_table", page_size=4096)
    print(table2.get_column_names())
    print(table2.get_column_info())
    print(table2.get_record_count())
    print(table2.pack_string)