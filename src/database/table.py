import os
import json
import struct
import pickle
from database.indexes.b_plus import BPlusTree
from database.indexes.extendible_hash import ExtendibleHash   

class Table:
    DATA_TYPES = {
        "INT": {"size": 4, "format": "i"},
        "FLOAT": {"size": 8, "format": "d"},
        "VARCHAR": {"variable": True},
        "DATE": {"size": 8, "format": "q"},
        "BOOLEAN": {"size": 1, "format": "?"}
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
        
    def __init__(self, name, columns, primary_key, page_size, index_type="bplus_tree", file_path=None, data_dir=os.path.join(os.getcwd(), "data")):
        self.name = name
        self.columns = columns
        self.index_type = index_type
        self.primary_key = primary_key
        self.page_size = page_size
        
        self.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        self.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        self.record_count = 0
        self.index = None

        # el pack string es el que se usa para serializar los datos:
        self.pack_string = "".join([self._get_single_data_pack_string(col_type) for col_type in columns.values()])
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        
        # Create empty data file if it doesn't exist
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'wb') as f:
                pass
                
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
        table = cls(name, columns, metadata.get("primary_key", None), page_size, index_type=index_type, data_dir=data_dir)
        table.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        table.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        table.metadata = metadata
        table.pack_string = metadata.get("pack_string", "")
        table.record_count = metadata.get("record_count", 0)
        
        # Create index
        table._create_primary_index()
        
        return table
    
    def _create_primary_index(self):
        """
        This method will create the index for the table based on the specified index type.
        """
        if self.index_type == "bplus_tree":
            self.index = BPlusTree(
                table_name=self.name,
                column_name=self.primary_key,
                data_path=self.data_path,
                table_ref=self,
                page_size=self.page_size
            )
        elif self.index_type == "extendible_hash":
            self.index = ExtendibleHash(
                table_name=self.name,
                column_name=self.primary_key,
                data_path=self.data_path,
                table_ref=self,
                page_size=self.page_size
            )
    
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
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        for record in data:
            self.add(record)
    
    def _get_record_size(self):
        return struct.calcsize(self.pack_string)
    
    def search(self, column, value):
        if column == self.primary_key:
            return self.index.search(value)
        else:
            # Full scan for non-indexed columns
            results = []
            all_records = self.get_all()
            for record in all_records:
                if record[column] == value:
                    results.append(record)
            return results
    
    def range_search(self, column, begin_key, end_key):
        if column == self.primary_key:
            return self.index.range_search(begin_key, end_key)
        else:
            # Full scan for non-indexed columns
            results = []
            all_records = self.get_all()
            for record in all_records:
                if begin_key <= record[column] <= end_key:
                    results.append(record)
            return results
    
    def spatial_search(self, column, point, radius):
        # Specialized search for spatial data - could be enhanced for spatial indices
        results = []
        all_records = self.get_all()
        for record in all_records:
            # Simple Euclidean distance for 2D points
            if isinstance(record[column], tuple) and len(record[column]) == 2:
                x1, y1 = point
                x2, y2 = record[column]
                distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                if distance <= radius:
                    results.append(record)
        return results
    
    def add(self, record):
        # Validate record structure
        for col_name in self.columns:
            if col_name not in record:
                raise ValueError(f"Missing column {col_name} in record")
                
        # Check if primary key already exists
        primary_key_value = record[self.primary_key]
        existing_record = self.index.search(primary_key_value)
        
        if existing_record:
            raise ValueError(f"Record with primary key {primary_key_value} already exists")
        
        # Add the record to the index
        self.index.add(record, primary_key_value)
        
        # Update record count
        self.record_count += 1
        
        # Save metadata
        self._save_metadata()
        
        return True
    
    def remove(self, column, value):
        if column != self.primary_key:
            raise ValueError(f"Can only remove records by primary key ({self.primary_key})")
            
        # Remove the record from the index
        result = self.index.remove(value)
        
        if result:
            self.record_count -= 1
            self._save_metadata()
            
        return result
    
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
        return self.index.get_all()
    
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
        # Verificar si el tamaño de bytes_data coincide con lo esperado
        expected_size = self._get_record_size()
        
        if len(bytes_data) != expected_size:
            # Si no coincide, ajustar el buffer
            if len(bytes_data) < expected_size:
                # Si es más pequeño, completar con ceros
                bytes_data = bytes_data.ljust(expected_size, b'\x00')
            else:
                # Si es más grande, truncar
                bytes_data = bytes_data[:expected_size]
        
        # el unpack retorna una tupla con los datos
        try:
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
            
            return record
        except struct.error as e:
            print(f"Error deserializando registro: {e}")
            print(f"Tamaño esperado: {expected_size}, tamaño recibido: {len(bytes_data)}")
            print(f"Pack string: {self.pack_string}")
            raise

    def get_column_size(self, column):
        """
        Get the size of a column based on its data type.
        
        Params:
            column (str): The name of the column.
        
        Returns:
            int: The size of the column in bytes.
        """
        if column not in self.columns:
            raise ValueError(f"Column {column} not found in table {self.name}")
        
        col_type = self.columns[column]
        if col_type in self.DATA_TYPES:
            return self.DATA_TYPES[col_type]["size"]
        elif col_type.startswith("VARCHAR"):
            size = int(col_type.split("(")[1].split(")")[0])
            return size
        else:
            raise ValueError(f"Unsupported data type: {col_type}")

    def serialize_column(self, col_type, value):
        """
        Serialize a column value based on its data type.
        
        Params:
            col_type (str): The data type of the column.
            value: The value to serialize.
        
        Returns:
            bytes: The serialized value as bytes.
        """
        try:
            if col_type == "INT":
                return struct.pack('!i', value)
            elif col_type == "FLOAT":
                return struct.pack('!d', value)
            elif col_type == "BOOLEAN":
                return struct.pack('!?', value)
            elif col_type == "DATE":
                return struct.pack('!q', value)
            elif col_type.startswith("VARCHAR"):
                size = int(col_type.split("(")[1].split(")")[0])
                encoded = value.encode('utf-8')
                if len(encoded) > size:
                    encoded = encoded[:size]
                return encoded.ljust(size, b'\x00')
            else:
                fmt = self._get_single_data_pack_string(col_type)
                return struct.pack(fmt, value)
        except Exception as e:
            # Fallback to original method as a last resort
            fmt = self._get_single_data_pack_string(col_type)
            if 's' in fmt:
                size = int(fmt[:-1])
                encoded = value.encode('utf-8')
                if len(encoded) > size:
                    raise ValueError(f"Value for {column} exceeds VARCHAR({size}) limit")
                return encoded.ljust(size, b'\x00')
            else:
                return struct.pack(fmt, value)
    
    def deserialize_column(self, col_type, bytes_data):
        """
        Deserialize a column value from bytes based on its data type.
        
        Params:
            col_type (str): The data type of the column.
            bytes_data (bytes): The serialized value as bytes.
        
        Returns:
            The deserialized value.
        """
        
        try:
            if col_type == "INT":
                return struct.unpack('!i', bytes_data)[0]
            elif col_type == "FLOAT":
                return struct.unpack('!d', bytes_data)[0]
            elif col_type == "BOOLEAN":
                return bool(struct.unpack('!?', bytes_data)[0])
            elif col_type == "DATE":
                return struct.unpack('!q', bytes_data)[0]
            elif col_type.startswith("VARCHAR"):
                return bytes_data.decode('utf-8').rstrip('\x00')
            else:
                fmt = self._get_single_data_pack_string(col_type)
                return struct.unpack(fmt, bytes_data)[0]
        except Exception as e:
            # Fallback to original method as a last resort
            fmt = self._get_single_data_pack_string(col_type)
            if 's' in fmt:
                size = int(fmt[:-1])
                return bytes_data[:size].decode('utf-8').rstrip('\x00')
            else:
                return struct.unpack(fmt, bytes_data)[0]