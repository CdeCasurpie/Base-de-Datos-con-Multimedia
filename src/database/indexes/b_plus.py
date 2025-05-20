import os
import struct
import json
import math
from database.index_base import IndexBase

class Node:
    """
    Nodo para el árbol B+. Puede ser interno o hoja.
    """
    def __init__(self, is_leaf=False, page_id=None):
        self.keys = []
        self.children = []  # Para nodos internos: IDs de página, para hojas: posiciones de registros
        self.is_leaf = is_leaf
        self.page_id = page_id
        self.next_leaf = None  # Para hojas: puntero al siguiente nodo hoja

class BPlusTree(IndexBase):
    """
    Implementación de índice B+ Tree para una tabla.
    """
    
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size
        self.index_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_index.dat")
        self.metadata_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_index_metadata.json")
        
        # Determinar tamaño de la clave según el tipo de columna
        self.key_size = table_ref.get_column_size(column_name)
        self.ptr_size = 8
        self.col_type = table_ref.columns.get(column_name)
        
        self.key_format = self._get_key_format()
        
        # Cálculo del orden: (orden-1) claves + orden punteros deben caber en una página
        self.order = math.floor((page_size - 20) / (self.key_size + self.ptr_size))
        
        # Asegurar orden mínimo de 3
        self.order = max(3, self.order)
        
        self.root_page_id = None
        self.height = 0
        self.num_pages = 0
        
        self._init_index()

    def _get_key_format(self):
        """Formato de struct para serializar/deserializar la clave"""
        if self.col_type == "INT":
            return "!i"
        elif self.col_type == "FLOAT":
            return "!d"
        elif self.col_type == "BOOLEAN":
            return "!?"
        elif self.col_type == "DATE":
            return "!q"
        elif self.col_type.startswith("VARCHAR"):
            size = int(self.col_type.split("(")[1].split(")")[0])
            return f"!{size}s"
        else:
            return "!i"

    def _init_index(self):
        """Inicializa o carga el índice desde archivos existentes"""
        if os.path.exists(self.metadata_file):
            self._load_metadata()
        else:
            if not os.path.exists(os.path.dirname(self.index_file)):
                os.makedirs(os.path.dirname(self.index_file))
            
            root = Node(is_leaf=True)
            root.page_id = self._allocate_page()
            self.root_page_id = root.page_id
            self.height = 1
            
            self._write_node(root)
            self._save_metadata()
    
    def _load_metadata(self):
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.root_page_id = metadata.get('root_page_id')
        self.order = metadata.get('order')
        self.height = metadata.get('height', 1)
        self.num_pages = metadata.get('num_pages', 0)
    
    def _save_metadata(self):
        metadata = {
            'table_name': self.table_name,
            'column_name': self.column_name,
            'root_page_id': self.root_page_id,
            'order': self.order,
            'height': self.height,
            'num_pages': self.num_pages,
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)
    
    def _allocate_page(self):
        page_id = self.num_pages
        self.num_pages += 1
        return page_id
    
    def _read_node(self, page_id):
        """Lee un nodo desde disco dado su ID de página"""
        if page_id is None:
            return None
            
        with open(self.index_file, 'rb') as f:
            f.seek(page_id * self.page_size)
            page_data = f.read(self.page_size)
            
            node = Node()
            node.page_id = page_id
            
            # Primer byte indica si es hoja
            node.is_leaf = bool(page_data[0])
            
            # Siguientes 4 bytes (int) indican número de claves
            num_keys = struct.unpack('!i', page_data[1:5])[0]
            
            # Si es hoja, leer puntero next_leaf (4 bytes)
            if node.is_leaf:
                next_leaf = struct.unpack('!i', page_data[5:9])[0]
                node.next_leaf = next_leaf if next_leaf != -1 else None
                offset = 9
            else:
                offset = 5
            
            # Leer claves y punteros
            for i in range(num_keys):
                key = self._deserialize_key(page_data[offset:offset+self.key_size])
                offset += self.key_size
                node.keys.append(key)
                
                ptr = struct.unpack('!q', page_data[offset:offset+8])[0]
                node.children.append(ptr)
                offset += 8
            
            # Para nodos internos, leer un puntero adicional
            if not node.is_leaf and num_keys > 0:
                ptr = struct.unpack('!q', page_data[offset:offset+8])[0]
                node.children.append(ptr)
            
            return node
    
    def _write_node(self, node):
        """Escribe un nodo al disco en su page_id"""
        page_data = bytearray(self.page_size)
        
        # Primer byte indica si es hoja
        page_data[0] = 1 if node.is_leaf else 0
        
        # Siguientes 4 bytes para número de claves
        num_keys = len(node.keys)
        page_data[1:5] = struct.pack('!i', num_keys)
        
        # Si es hoja, almacenar puntero next_leaf
        if node.is_leaf:
            next_leaf = node.next_leaf if node.next_leaf is not None else -1
            page_data[5:9] = struct.pack('!i', next_leaf)
            offset = 9
        else:
            offset = 5
        
        # Escribir claves y punteros
        for i in range(num_keys):
            key_bytes = self._serialize_key(node.keys[i])
            page_data[offset:offset+self.key_size] = key_bytes
            offset += self.key_size
            
            page_data[offset:offset+8] = struct.pack('!q', node.children[i])
            offset += 8
        
        # Para nodos internos, escribir un puntero adicional
        if not node.is_leaf and num_keys > 0:
            page_data[offset:offset+8] = struct.pack('!q', node.children[num_keys])
        
        with open(self.index_file, 'r+b' if os.path.exists(self.index_file) else 'wb') as f:
            f.seek(node.page_id * self.page_size)
            f.write(page_data)
    
    def _serialize_key(self, key):
        """Serializa la clave usando la lógica centralizada en Table"""
        return self.table_ref.serialize_column(self.col_type, key)
    
    def _deserialize_key(self, key_bytes):
        """Deserializa la clave usando la lógica centralizada en Table"""
        return self.table_ref.deserialize_column(self.col_type, key_bytes)

    def _find_leaf(self, key):
        """Encuentra el nodo hoja que debería contener la clave"""
        if self.root_page_id is None:
            return None
            
        current_node = self._read_node(self.root_page_id)
        
        while not current_node.is_leaf:
            i = 0
            while i < len(current_node.keys) and key >= current_node.keys[i]:
                i += 1
            
            current_node = self._read_node(current_node.children[i])
        
        return current_node
    
    def search(self, key):
        """Busca un registro con la clave especificada"""
        leaf = self._find_leaf(key)
        if leaf is None:
            return None
            
        for i, k in enumerate(leaf.keys):
            if k == key:
                record_pos = leaf.children[i]
                
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    return self.table_ref._deserialize_record(record_data)
        
        return None
    
    def range_search(self, begin_key, end_key=None):
        """Busca registros con claves en el rango dado"""
        result = []
        
        leaf = self._find_leaf(begin_key)
        if leaf is None:
            return result
        
        i = 0
        while i < len(leaf.keys) and leaf.keys[i] < begin_key:
            i += 1
        
        current_leaf = leaf
        while current_leaf is not None:
            while i < len(current_leaf.keys):
                current_key = current_leaf.keys[i]
                
                if end_key is not None and current_key > end_key:
                    return result
                
                record_pos = current_leaf.children[i]
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    result.append(self.table_ref._deserialize_record(record_data))
                
                i += 1
            
            if current_leaf.next_leaf is None:
                break
            
            current_leaf = self._read_node(current_leaf.next_leaf)
            i = 0
        
        return result
    
    def add(self, record, key):
        """Añade un registro al índice"""
        record_data = self.table_ref._serialize_record(record)
        record_pos = self._append_record_to_data_file(record_data)
        self._add_key_with_position(key, record_pos)
        self._save_metadata()
    
    def _append_record_to_data_file(self, record_data):
        """Añade un registro al archivo de datos y retorna su posición"""
        with open(self.data_path, 'ab') as f:
            record_pos = f.tell()
            f.write(record_data)
            return record_pos
    
    def _add_key_with_position(self, key, record_pos):
        """Añade una clave con su posición al árbol B+"""
        if self.root_page_id is None:
            root = Node(is_leaf=True)
            root.page_id = self._allocate_page()
            root.keys.append(key)
            root.children.append(record_pos)
            self._write_node(root)
            self.root_page_id = root.page_id
            return
        
        leaf = self._find_leaf(key)
        
        i = 0
        while i < len(leaf.keys) and key > leaf.keys[i]:
            i += 1
        
        # Si la clave ya existe, reemplazar la posición
        if i < len(leaf.keys) and key == leaf.keys[i]:
            leaf.children[i] = record_pos
            self._write_node(leaf)
            return
        
        # Insertar nueva clave y posición
        leaf.keys.insert(i, key)
        leaf.children.insert(i, record_pos)
        
        # Verificar si se necesita división
        if len(leaf.keys) < self.order:
            self._write_node(leaf)
            return
        
        self._split_leaf(leaf)
    
    def _split_leaf(self, leaf):
        """Divide un nodo hoja y actualiza la estructura del árbol"""
        new_leaf = Node(is_leaf=True)
        new_leaf.page_id = self._allocate_page()
        
        # Calcular punto de división
        split = len(leaf.keys) // 2
        
        # Mover mitad de claves e hijos al nuevo nodo
        new_leaf.keys = leaf.keys[split:]
        new_leaf.children = leaf.children[split:]
        
        # Actualizar el nodo original
        leaf.keys = leaf.keys[:split]
        leaf.children = leaf.children[:split]
        
        # Configurar cadena de hojas
        new_leaf.next_leaf = leaf.next_leaf
        leaf.next_leaf = new_leaf.page_id
        
        # Obtener primera clave del nuevo nodo para promoción
        promoted_key = new_leaf.keys[0]
        
        # Escribir ambas hojas al disco
        self._write_node(leaf)
        self._write_node(new_leaf)
        
        # Añadir clave promovida al padre
        self._insert_in_parent(leaf, promoted_key, new_leaf)
    
    def _insert_in_parent(self, left_node, key, right_node):
        """Inserta una clave y hijo derecho en el nodo padre"""
        # Caso especial: si el nodo izquierdo es la raíz
        if left_node.page_id == self.root_page_id:
            new_root = Node(is_leaf=False)
            new_root.page_id = self._allocate_page()
            new_root.keys.append(key)
            new_root.children.append(left_node.page_id)
            new_root.children.append(right_node.page_id)
            
            self.root_page_id = new_root.page_id
            self.height += 1
            
            self._write_node(new_root)
            return
        
        parent = self._find_parent(self.root_page_id, left_node.page_id)
        
        i = 0
        while i < len(parent.keys) and key > parent.keys[i]:
            i += 1
        
        parent.keys.insert(i, key)
        parent.children.insert(i + 1, right_node.page_id)
        
        # Verificar si el padre necesita división
        if len(parent.keys) < self.order:
            self._write_node(parent)
            return
        
        self._split_internal(parent)
    
    def _split_internal(self, node):
        """Divide un nodo interno y actualiza la estructura"""
        new_node = Node(is_leaf=False)
        new_node.page_id = self._allocate_page()
        
        split = len(node.keys) // 2
        
        # Obtener clave media para promoción
        promoted_key = node.keys[split]
        
        # Mover claves e hijos al nuevo nodo
        new_node.keys = node.keys[split+1:]
        new_node.children = node.children[split+1:]
        
        # Actualizar el nodo original
        node.keys = node.keys[:split]
        node.children = node.children[:split+1]
        
        # Escribir ambos nodos a disco
        self._write_node(node)
        self._write_node(new_node)
        
        # Añadir clave promovida al padre
        self._insert_in_parent(node, promoted_key, new_node)
    
    def _find_parent(self, node_id, child_id):
        """Encuentra el nodo padre de un nodo hijo dado"""
        node = self._read_node(node_id)
        
        if node.is_leaf:
            return None
        
        # Verificar si alguno de los hijos es el objetivo
        for i, child in enumerate(node.children):
            if child == child_id:
                return node
        
        # Buscar recursivamente en el hijo apropiado
        for i, key in enumerate(node.keys):
            i_child = self._read_node(node.children[i])
            if i_child.is_leaf:
                continue
                
            if i == len(node.keys) - 1:
                i_plus_child = self._read_node(node.children[i+1])
                if not i_plus_child.is_leaf:
                    right_result = self._find_parent(node.children[i+1], child_id)
                    if right_result:
                        return right_result
            
            result = self._find_parent(node.children[i], child_id)
            if result:
                return result
        
        return None
    
    def remove(self, key):
        """Elimina un registro con la clave dada"""
        if self.root_page_id is None:
            return False
            
        leaf = self._find_leaf(key)
        if leaf is None:
            return False
        
        found = False
        for i, k in enumerate(leaf.keys):
            if k == key:
                leaf.keys.pop(i)
                leaf.children.pop(i)
                found = True
                break
        
        if not found:
            return False
        
        self._write_node(leaf)
        
        # Verificar si necesitamos manejar underflow
        min_keys = (self.order - 1) // 2
        if len(leaf.keys) >= min_keys or leaf.page_id == self.root_page_id:
            return True
        
        # Versión simplificada - una versión completa necesitaría lógica más compleja
        return True
    
    def rebuild(self):
        """Reorganiza la estructura del índice"""
        old_index_file = self.index_file
        old_metadata_file = self.metadata_file
        
        self.index_file = f"{old_index_file}.rebuild"
        self.metadata_file = f"{old_metadata_file}.rebuild"
        
        self.root_page_id = None
        self.height = 0
        self.num_pages = 0
        
        self._init_index()
        
        all_records = self.get_all()
        
        for record in all_records:
            key = record[self.column_name]
            record_pos = 0  # Esto necesitaría ser la posición real
            self.add(key, record_pos)
        
        import os
        if os.path.exists(old_index_file):
            os.remove(old_index_file)
        if os.path.exists(old_metadata_file):
            os.remove(old_metadata_file)
        
        os.rename(self.index_file, old_index_file)
        os.rename(self.metadata_file, old_metadata_file)
        
        self.index_file = old_index_file
        self.metadata_file = old_metadata_file
    
    def get_all(self):
        """Obtiene todos los registros en el índice"""
        result = []
        
        if self.root_page_id is None:
            return result
        
        # Encontrar la hoja más a la izquierda
        node = self._read_node(self.root_page_id)
        while not node.is_leaf:
            node = self._read_node(node.children[0])
        
        # Recorrer todas las hojas usando la lista enlazada
        while node is not None:
            for i, key in enumerate(node.keys):
                record_pos = node.children[i]
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    result.append(self.table_ref._deserialize_record(record_data))
            
            # Moverse a la siguiente hoja
            if node.next_leaf is not None:
                node = self._read_node(node.next_leaf)
            else:
                node = None
        
        return result
    
    def count(self):
        """Cuenta el número de registros en el índice"""
        count = 0
        
        if self.root_page_id is None:
            return count
        
        # Encontrar la hoja más a la izquierda
        node = self._read_node(self.root_page_id)
        while not node.is_leaf:
            node = self._read_node(node.children[0])
        
        # Contar registros en todas las hojas
        while node is not None:
            count += len(node.keys)
            
            if node.next_leaf is not None:
                node = self._read_node(node.next_leaf)
            else:
                node = None
        
        return count
    
    def _get_record_size(self):
        try:
            return self.table_ref._get_record_size()
        except AttributeError:
            # Fallback - calcular tamaño basado en columnas
            size = 0
            for col_name, col_type in self.table_ref.columns.items():
                if col_type in self.table_ref.DATA_TYPES:
                    size += self.table_ref.DATA_TYPES[col_type]["size"]
                elif col_type.startswith("VARCHAR"):
                    size += int(col_type.split("(")[1].split(")")[0])
            return size