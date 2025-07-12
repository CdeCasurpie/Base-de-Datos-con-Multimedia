import os
import pickle
import struct
from rtree import index
from shapely.geometry import Point, Polygon, box, LineString
from shapely.wkt import loads as wkt_loads
import json
from HeiderDB.database.index_base import IndexBase


class RTreeIndex(IndexBase):
    def __init__(self, table_name, column_name, data_path, table_ref, page_size=4096):
        """
        Inicializa el índice R-Tree para una columna espacial específica.

        Args:
            table_name (str): Nombre de la tabla
            column_name (str): Nombre de la columna espacial
            data_path (str): Ruta al archivo de datos de la tabla
            table_ref: Referencia a la tabla
            page_size (int): Tamaño de página
        """
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size

        # Configurar directorios
        self.index_dir = os.path.join(os.path.dirname(data_path), "indexes", "rtree")
        os.makedirs(self.index_dir, exist_ok=True)

        self.index_path = os.path.join(self.index_dir, f"{table_name}_{column_name}")
        self.metadata_path = f"{self.index_path}_metadata.json"

        # Configurar propiedades del R-Tree
        self.props = index.Property()
        self.props.dimension = 2
        self.props.leaf_capacity = max(10, page_size // 64)  # Ajustar según page_size
        self.props.index_capacity = max(5, self.props.leaf_capacity // 2)
        self.props.fill_factor = 0.7
        self.props.dat_extension = "dat"
        self.props.idx_extension = "idx"

        # Contadores y mapeos
        self.id_counter = 0
        self.record_id_to_spatial_id = {}  # Mapea record_id -> spatial_id
        self.spatial_id_to_record_id = {}  # Mapea spatial_id -> record_id

        # Inicializar índice
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Carga el índice existente o crea uno nuevo."""
        try:
            # Intentar cargar índice existente
            self.idx = index.Index(self.index_path, properties=self.props)
            self._load_metadata()
            print(f"Índice R-Tree cargado para {self.table_name}.{self.column_name}")
        except:
            # Crear nuevo índice
            self.idx = index.Index(self.index_path, properties=self.props)
            self._save_metadata()
            print(
                f"Nuevo índice R-Tree creado para {self.table_name}.{self.column_name}"
            )

    def _save_metadata(self):
        """Guarda metadatos del índice."""
        metadata = {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "id_counter": self.id_counter,
            "record_id_to_spatial_id": self.record_id_to_spatial_id,
            "spatial_id_to_record_id": self.spatial_id_to_record_id,
            "total_entries": len(self.record_id_to_spatial_id),
        }

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self):
        """Carga metadatos del índice."""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                metadata = json.load(f)
                self.id_counter = metadata.get("id_counter", 0)
                self.record_id_to_spatial_id = metadata.get(
                    "record_id_to_spatial_id", {}
                )
                self.spatial_id_to_record_id = metadata.get(
                    "spatial_id_to_record_id", {}
                )

    def _parse_geometry(self, geom_value):
        """
        Parsea diferentes formatos de geometría a objetos Shapely.

        Args:
            geom_value: Puede ser WKT string, tupla (x,y), dict, etc.

        Returns:
            shapely.geometry: Objeto geométrico
        """
        if isinstance(geom_value, str):
            # Asumir WKT format
            return wkt_loads(geom_value)
        elif isinstance(geom_value, tuple) and len(geom_value) == 2:
            # Punto como tupla (x, y)
            return Point(geom_value)
        elif isinstance(geom_value, dict):
            if geom_value.get("type") == "Point":
                coords = geom_value.get("coordinates", [])
                return Point(coords)
            elif geom_value.get("type") == "Polygon":
                coords = geom_value.get("coordinates", [[]])
                return Polygon(coords[0])  # Exterior ring
        else:
            raise ValueError(f"Formato de geometría no soportado: {type(geom_value)}")

    def add(self, record, record_id):
        """
        Añade un registro espacial al índice.

        Args:
            record (dict): Registro completo
            record_id: ID único del registro
        """
        if self.column_name not in record:
            raise ValueError(
                f"Columna espacial '{self.column_name}' no encontrada en el registro"
            )

        geom_value = record[self.column_name]
        geometry = self._parse_geometry(geom_value)

        # Generar ID espacial único
        spatial_id = self.id_counter
        self.id_counter += 1

        # Mapear IDs
        self.record_id_to_spatial_id[str(record_id)] = spatial_id
        self.spatial_id_to_record_id[spatial_id] = str(record_id)

        # Insertar en R-Tree
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        self.idx.insert(spatial_id, bounds, obj=record)

        # Guardar metadatos
        self._save_metadata()

    def remove(self, record_id):
        """
        Elimina un registro del índice espacial.

        Args:
            record_id: ID del registro a eliminar

        Returns:
            bool: True si se eliminó exitosamente
        """
        str_record_id = str(record_id)

        if str_record_id not in self.record_id_to_spatial_id:
            return False

        spatial_id = self.record_id_to_spatial_id[str_record_id]

        # Obtener el registro para conseguir la geometría
        record = self.search_by_id(record_id)
        if not record:
            return False

        geometry = self._parse_geometry(record[self.column_name])
        bounds = geometry.bounds

        # Eliminar del R-Tree
        self.idx.delete(spatial_id, bounds)

        # Limpiar mapeos
        del self.record_id_to_spatial_id[str_record_id]
        del self.spatial_id_to_record_id[spatial_id]

        self._save_metadata()
        return True

    def search_by_id(self, record_id):
        """Busca un registro por su ID."""
        str_record_id = str(record_id)
        if str_record_id not in self.record_id_to_spatial_id:
            return None

        spatial_id = self.record_id_to_spatial_id[str_record_id]

        # Buscar en el índice
        for item in self.idx.intersection(self.idx.bounds, objects=True):
            if item.id == spatial_id:
                return item.object
        return None

    def search(self, key):
        return self.search_by_id(key)

    def count(self):
        return len(self.record_id_to_spatial_id)

    def intersection(self, geometry_or_bounds):
        """
        Encuentra todos los registros que intersectan con la geometría dada.

        Args:
            geometry_or_bounds: Geometría Shapely o tupla de bounds (minx, miny, maxx, maxy)

        Returns:
            list: Lista de registros que intersectan
        """
        if hasattr(geometry_or_bounds, "bounds"):
            bounds = geometry_or_bounds.bounds
        else:
            bounds = geometry_or_bounds

        results = []
        for item in self.idx.intersection(bounds, objects=True):
            results.append(item.object)

        return results

    def nearest(self, point, k=1):
        """
        Encuentra los k registros más cercanos al punto dado.

        Args:
            point: Punto como tupla (x, y) o geometría Shapely
            k (int): Número de vecinos más cercanos

        Returns:
            list: Lista de los k registros más cercanos
        """
        if isinstance(point, tuple):
            bounds = (point[0], point[1], point[0], point[1])
        else:
            bounds = point.bounds

        results = []
        for item in self.idx.nearest(bounds, k, objects=True):
            results.append(item.object)

        return results

    def range_search(self, min_point, max_point):
        """
        Búsqueda por rango rectangular.

        Args:
            min_point: Punto mínimo (x_min, y_min)
            max_point: Punto máximo (x_max, y_max)

        Returns:
            list: Registros dentro del rango
        """
        bounds = (min_point[0], min_point[1], max_point[0], max_point[1])
        return self.intersection(bounds)

    def spatial_search(self, center_point, radius):
        """
        Búsqueda espacial dentro de un radio.

        Args:
            center_point: Punto central (x, y)
            radius (float): Radio de búsqueda

        Returns:
            list: Registros dentro del radio
        """
        # Crear bounding box aproximado
        x, y = center_point
        bounds = (x - radius, y - radius, x + radius, y + radius)

        # Obtener candidatos
        candidates = self.intersection(bounds)

        # Filtrar por distancia real
        center = Point(center_point)
        results = []

        for record in candidates:
            geom = self._parse_geometry(record[self.column_name])
            if center.distance(geom) <= radius:
                results.append(record)

        return results

    def get_all(self):
        """
        Obtiene todos los registros del índice.

        Returns:
            list: Todos los registros
        """
        results = []
        for item in self.idx.intersection(self.idx.bounds, objects=True):
            results.append(item.object)
        return results

    def get_stats(self):
        """
        Obtiene estadísticas del índice.

        Returns:
            dict: Estadísticas del índice
        """
        total_entries = len(self.record_id_to_spatial_id)

        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "total_entries": total_entries,
            "dimension": self.props.dimension,
            "leaf_capacity": self.props.leaf_capacity,
            "index_capacity": self.props.index_capacity,
            "fill_factor": self.props.fill_factor,
            "bounds": self.idx.bounds if total_entries > 0 else None,
        }

    def rebuild(self):
        """
        Reconstruye el índice completamente.
        """
        # Obtener todos los datos actuales
        all_records = self.get_all()

        # Recrear índice
        self.idx = index.Index(self.index_path, properties=self.props)
        self.id_counter = 0
        self.record_id_to_spatial_id.clear()
        self.spatial_id_to_record_id.clear()

        # Reinsertar datos
        for record in all_records:
            # Asumir que el primary key está en el registro
            primary_key = record.get(self.table_ref.primary_key)
            if primary_key:
                self.add(record, primary_key)

        print(f"Índice R-Tree reconstruido con {len(all_records)} entradas")

    def close(self):
        """Cierra el índice y guarda metadatos."""
        self._save_metadata()
        self.idx.close()
