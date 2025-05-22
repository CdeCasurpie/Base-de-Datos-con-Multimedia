import os
import json
import struct
from database.indexes.b_plus import BPlusTree
from database.indexes.r_tree import RTreeIndex


class Table:
    DATA_TYPES = {
        "INT": {"size": 4, "format": "i"},
        "FLOAT": {"size": 8, "format": "d"},
        "VARCHAR": {"variable": True},
        "DATE": {"size": 8, "format": "q"},
        "BOOLEAN": {"size": 1, "format": "?"},
        "POINT": {"variable": True, "spatial": True},
        "POLYGON": {"variable": True, "spatial": True},
        "LINESTRING": {"variable": True, "spatial": True},
        "GEOMETRY": {"variable": True, "spatial": True},
    }

    def _get_single_data_pack_string(self, col_type):
        """Returns the pack string for a single data type."""
        if col_type in self.DATA_TYPES:
            if self.DATA_TYPES[col_type].get("variable", False):
                if col_type.startswith("VARCHAR"):
                    size = int(col_type.split("(")[1].split(")")[0])
                    return f"{size}s"
                elif col_type in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]:
                    # Para tipos espaciales, usar un tamaño fijo para WKT
                    return "500s"  # 200 caracteres para WKT
            else:
                return self.DATA_TYPES[col_type]["format"]
        elif col_type.startswith("VARCHAR"):
            size = int(col_type.split("(")[1].split(")")[0])
            return f"{size}s"
        else:
            raise ValueError(f"Unsupported data type: {col_type}")

    def __init__(
        self,
        name,
        columns,
        primary_key,
        page_size,
        index_type="bplus_tree",
        spatial_columns=None,
        file_path=None,
        data_dir=os.path.join(os.getcwd(), "data"),
        from_table=False,
    ):
        self.name = name
        self.columns = columns
        self.index_type = index_type
        self.primary_key = primary_key
        self.page_size = page_size

        self.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        self.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        self.record_count = 0
        self.index = None
        self.spatial_columns = spatial_columns or []
        self.spatial_indexes = {}


        # el pack string es el que se usa para serializar los datos:
        self.pack_string = "".join(
            [
                self._get_single_data_pack_string(col_type)
                for col_type in columns.values()
            ]
        )

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

        # Create empty data file if it doesn't exist
        if not os.path.exists(self.data_path):
            with open(self.data_path, "wb") as f:
                pass
        if not os.path.exists(self.metadata_path):
            with open(self.metadata_path, "wb") as f:
                pass

        if not from_table:
            self._create_primary_index()
            self._create_spatial_indexes()
            self._save_metadata()

        if file_path:
            self._load_from_file(file_path)

    @classmethod
    def from_table_name(
        cls, name, page_size, data_dir=os.path.join(os.getcwd(), "data")
    ):
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
        table = cls(
            name,
            columns,
            metadata.get("primary_key", None),
            page_size,
            index_type=index_type,
            data_dir=data_dir,
            from_table=True,
        )
        table.metadata_path = os.path.join(data_dir, "tables", f"{name}.json")
        table.data_path = os.path.join(data_dir, "tables", f"{name}.dat")
        table.metadata = metadata
        table.pack_string = metadata.get("pack_string", "")
        table.record_count = metadata.get("record_count", 0)
        table.spatial_columns = metadata.get("spatial_columns", [])

        # Create index
        table._create_primary_index()
        table._create_spatial_indexes()

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
                page_size=self.page_size,
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
            "spatial_columns": self.spatial_columns,
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
        with open(file_path, "r") as f:
            data = json.load(f)

        for record in data:
            self.add(record)

    def _get_record_size(self):
        return struct.calcsize(self.pack_string)

    def search(self, column, value):
        """
        Busca registros por columna y valor.

        Args:
            column (str): Nombre de la columna
            value: Valor a buscar

        Returns:
            dict o list: Registro encontrado (si es primary key) o lista de registros
        """
        if column == self.primary_key:
            return self.index.search(value)
        else:
            # Full scan para columnas no indexadas
            results = []
            all_records = self.get_all()
            for record in all_records:
                if record.get(column) == value:
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
            raise ValueError(
                f"Record with primary key {primary_key_value} already exists"
            )

        # Add the record to the index
        self.index.add(record, primary_key_value)

        # Serialize the record
        for column, spatial_index in self.spatial_indexes.items():
            if column in record:
                try:
                    spatial_index.add(record, primary_key_value)
                except Exception as e:
                    print(f"Error adding spatial index for {column}: {e}")

        # Update record count
        self.record_count += 1

        # Save metadata
        self._save_metadata()

        return True

    def remove(self, column, value):
        """
        Elimina un registro de la tabla.

        Args:
            column (str): Nombre de la columna (debe ser primary key)
            value: Valor de la primary key a eliminar

        Returns:
            bool: True si se eliminó exitosamente
        """
        if column != self.primary_key:
            raise ValueError(
                f"Can only remove records by primary key ({self.primary_key})"
            )
        
        # buscar
        existing_record = self.search(self.primary_key, value)
        if not existing_record:
            print(f"Record with primary key {value} not found")
            return False

        # Remove from spatial indexes first
        for spatial_index in self.spatial_indexes.values():
            try:
                spatial_index.remove(value)
            except Exception as e:
                print(f"Warning: Error removing from spatial index: {e}")

        # Remove the record from the primary index
        try:
            result = self.index.remove(value)
            if result:
                self.record_count -= 1
                self._save_metadata()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error removing from primary index: {e}")
            return False

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

            # Manejar tipos espaciales
            if col_type in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]:
                # Convertir geometría a WKT string
                if hasattr(value, "wkt"):
                    wkt_str = value.wkt
                elif isinstance(value, str):
                    wkt_str = value
                elif isinstance(value, tuple) and len(value) == 2:
                    wkt_str = f"POINT({value[0]} {value[1]})"
                else:
                    wkt_str = str(value)

                encoded = wkt_str.encode("utf-8")
                if len(encoded) > 500:  # Límite definido arriba
                    raise ValueError(f"Geometry WKT too large for {col_name}")
                values.append(encoded.ljust(500, b"\x00"))
            else:
                # Código existente para otros tipos
                fmt = self._get_single_data_pack_string(col_type)
                if "s" in fmt and not col_type.startswith(
                    ("POINT", "POLYGON", "LINESTRING", "GEOMETRY")
                ):
                    size = int(fmt[:-1])
                    encoded = value.encode("utf-8")
                    if len(encoded) > size:
                        raise ValueError(
                            f"Value for {col_name} exceeds VARCHAR({size}) limit"
                        )
                    values.append(encoded.ljust(size, b"\x00"))
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
                bytes_data = bytes_data.ljust(expected_size, b"\x00")
            else:
                # Si es más grande, truncar
                bytes_data = bytes_data[:expected_size]

        # el unpack retorna una tupla con los datos
        try:
            unpacked_data = struct.unpack(self.pack_string, bytes_data)

            record = {}
            offset = 0
            for col_name, col_type in self.columns.items():
                if col_type in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]:
                    # Deserializar tipo espacial
                    wkt_bytes = unpacked_data[offset]
                    wkt_str = wkt_bytes.decode("utf-8").rstrip("\x00")
                    record[col_name] = wkt_str  # Mantener como WKT string
                    offset += 1
                elif col_type in self.DATA_TYPES:
                    record[col_name] = unpacked_data[offset]
                    offset += 1
                elif col_type.startswith("VARCHAR"):
                    record[col_name] = (
                        unpacked_data[offset].decode("utf-8").rstrip("\x00")
                    )
                    offset += 1
                else:
                    raise ValueError(f"Unsupported data type: {col_type}")

            return record

        except struct.error as e:
            print(f"Error deserializando registro: {e}")
            print(
                f"Tamaño esperado: {expected_size}, tamaño recibido: {len(bytes_data)}"
            )
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
                return struct.pack("!i", value)
            elif col_type == "FLOAT":
                return struct.pack("!d", value)
            elif col_type == "BOOLEAN":
                return struct.pack("!?", value)
            elif col_type == "DATE":
                return struct.pack("!q", value)
            elif col_type.startswith("VARCHAR"):
                size = int(col_type.split("(")[1].split(")")[0])
                encoded = value.encode("utf-8")
                if len(encoded) > size:
                    encoded = encoded[:size]
                return encoded.ljust(size, b"\x00")
            else:
                fmt = self._get_single_data_pack_string(col_type)
                return struct.pack(fmt, value)
        except Exception as e:
            # Fallback to original method as a last resort
            fmt = self._get_single_data_pack_string(col_type)
            if "s" in fmt:
                size = int(fmt[:-1])
                encoded = value.encode("utf-8")
                if len(encoded) > size:
                    raise ValueError(f"Value exceeds VARCHAR({size}) limit")
                return encoded.ljust(size, b"\x00")
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
                return struct.unpack("!i", bytes_data)[0]
            elif col_type == "FLOAT":
                return struct.unpack("!d", bytes_data)[0]
            elif col_type == "BOOLEAN":
                return bool(struct.unpack("!?", bytes_data)[0])
            elif col_type == "DATE":
                return struct.unpack("!q", bytes_data)[0]
            elif col_type.startswith("VARCHAR"):
                return bytes_data.decode("utf-8").rstrip("\x00")
            else:
                fmt = self._get_single_data_pack_string(col_type)
                return struct.unpack(fmt, bytes_data)[0]
        except Exception as e:
            # Fallback to original method as a last resort
            fmt = self._get_single_data_pack_string(col_type)
            if "s" in fmt:
                size = int(fmt[:-1])
                return bytes_data[:size].decode("utf-8").rstrip("\x00")
            else:
                return struct.unpack(fmt, bytes_data)[0]

    def _create_spatial_indexes(self):
        """Crea índices espaciales para las columnas especificadas."""
        for column in self.spatial_columns:
            if column in self.columns:
                col_type = self.columns[column]
                if col_type in ["POINT", "POLYGON", "LINESTRING", "GEOMETRY"]:
                    self.spatial_indexes[column] = RTreeIndex(
                        table_name=self.name,
                        column_name=column,
                        data_path=self.data_path,
                        table_ref=self,
                        page_size=self.page_size,
                    )
                    print(f"Índice espacial creado para columna: {column}")

    def spatial_search(self, column, center_point, radius):
        """Búsqueda espacial por radio."""
        if column in self.spatial_indexes:
            return self.spatial_indexes[column].spatial_search(center_point, radius)
        else:
            # Fallback al método original
            return super().spatial_search(column, center_point, radius)

    def intersection_search(self, column, geometry):
        """Búsqueda por intersección geométrica."""
        if column in self.spatial_indexes:
            return self.spatial_indexes[column].intersection(geometry)
        else:
            raise ValueError(f"No spatial index found for column {column}")

    def nearest_search(self, column, point, k=1):
        """Búsqueda de k vecinos más cercanos."""
        if column in self.spatial_indexes:
            return self.spatial_indexes[column].nearest(point, k)
        else:
            raise ValueError(f"No spatial index found for column {column}")

    def range_search_spatial(self, column, min_point, max_point):
        """Búsqueda por rango espacial."""
        if column in self.spatial_indexes:
            return self.spatial_indexes[column].range_search(min_point, max_point)
        else:
            # Fallback to original range_search if not spatial
            return self.range_search(column, min_point, max_point)

    def get_spatial_index_stats(self):
        """Obtiene estadísticas de todos los índices espaciales."""
        stats = {}
        for column, spatial_index in self.spatial_indexes.items():
            stats[column] = spatial_index.get_stats()
        return stats
