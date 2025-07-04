import os
import struct
import json
import math
from HeiderDB.database.index_base import IndexBase

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
            self.free_pages = []
            
            self._write_node(root)
            self._save_metadata()
    
    def _load_metadata(self):
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.root_page_id = metadata.get('root_page_id')
        self.order = metadata.get('order')
        self.height = metadata.get('height', 1)
        self.num_pages = metadata.get('num_pages', 0)
        self.free_pages = metadata.get('free_pages', [])
    
    def _save_metadata(self):
        """Guarda metadatos del índice, incluyendo la lista de páginas libres"""
        metadata = {
            'table_name': self.table_name,
            'column_name': self.column_name,
            'root_page_id': self.root_page_id,
            'order': self.order,
            'height': self.height,
            'num_pages': self.num_pages,
            'free_pages': self.free_pages
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)
    
    def _allocate_page(self):
        """
        Asigna una página para un nuevo nodo.
        Primero intenta usar una página libre; si no hay, crea una nueva.
        
        Returns:
            int: ID de la página asignada
        """
        if hasattr(self, 'free_pages') and self.free_pages:
            return self.free_pages.pop()
        else:
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
        
        new_key, new_node = self._insert_recursive(self.root_page_id, key, record_pos)
        
        if new_key is not None:
            new_root = Node(is_leaf=False)
            new_root.page_id = self._allocate_page()
            new_root.keys.append(new_key)
            new_root.children.append(self.root_page_id)
            new_root.children.append(new_node.page_id)
            
            self._write_node(new_root)
            self.root_page_id = new_root.page_id
            self.height += 1
    
    def _insert_recursive(self, node_id, key, record_pos):
        """
        Inserta recursivamente una clave en el árbol.
        
        Args:
            node_id: ID del nodo actual
            key: Clave a insertar
            record_pos: Posición del registro
            
        Returns:
            tuple: (clave_promovida, nuevo_nodo) o (None, None) si no hay promoción
        """
        node = self._read_node(node_id)
        
        # Si es un nodo hoja
        if node.is_leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            
            if i < len(node.keys) and key == node.keys[i]:
                node.children[i] = record_pos
                self._write_node(node)
                return None, None
            
            node.keys.insert(i, key)
            node.children.insert(i, record_pos)
            
            # División
            if len(node.keys) < self.order:
                self._write_node(node)
                return None, None
            
            return self._split_leaf_recursive(node)
        
        # Si es un nodo interno
        else:
            # Encontrar el hijo
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            
            child_id = node.children[i]
            new_key, new_node = self._insert_recursive(child_id, key, record_pos)
            
            if new_key is None:
                return None, None
            
            i = 0
            while i < len(node.keys) and new_key > node.keys[i]:
                i += 1
            
            node.keys.insert(i, new_key)
            node.children.insert(i + 1, new_node.page_id)
            
            # Si necesitamos split:
            if len(node.keys) < self.order:
                self._write_node(node)
                return None, None
            
            return self._split_internal_recursive(node)
    
    def _split_leaf_recursive(self, leaf):
        """
        Divide un nodo hoja y devuelve la información para actualización del padre.
        
        Returns:
            tuple: (clave_promovida, nuevo_nodo)
        """
        new_leaf = Node(is_leaf=True)
        new_leaf.page_id = self._allocate_page()
        
        split = len(leaf.keys) // 2
        

        new_leaf.keys = leaf.keys[split:]
        new_leaf.children = leaf.children[split:]
        

        leaf.keys = leaf.keys[:split]
        leaf.children = leaf.children[:split]
        
        new_leaf.next_leaf = leaf.next_leaf
        leaf.next_leaf = new_leaf.page_id
        
        self._write_node(leaf)
        self._write_node(new_leaf)
        
        return new_leaf.keys[0], new_leaf
    
    def _split_internal_recursive(self, node):
        """
        Divide un nodo interno y devuelve la información para actualización del padre.
        
        Returns:
            tuple: (clave_promovida, nuevo_nodo)
        """
        new_node = Node(is_leaf=False)
        new_node.page_id = self._allocate_page()
        

        split = len(node.keys) // 2
        
        promoted_key = node.keys[split]
        
        new_node.keys = node.keys[split+1:]
        new_node.children = node.children[split+1:]
        
        node.keys = node.keys[:split]
        node.children = node.children[:split+1]
        
        self._write_node(node)
        self._write_node(new_node)
        
        return promoted_key, new_node
    
    def remove(self, key):
        """
        Elimina un registro con la clave dada de forma recursiva.
        
        Args:
            key: Clave a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False si no se encontró
        """
        if self.root_page_id is None:
            return False
        
        result, underflow = self._remove_recursive(self.root_page_id, key)
        # Si raiz vaciá
        if underflow:
            root = self._read_node(self.root_page_id)
            if not root.is_leaf and len(root.keys) == 0:
                new_root_id = root.children[0]
                self.root_page_id = new_root_id
                self.height -= 1
                # Liberar la página de la antigua raíz (opcional)
        
        self._save_metadata()
        return result
        
    def _remove_recursive(self, node_id, key):
        """
        Elimina recursivamente una clave del árbol B+.
        
        Args:
            node_id: ID del nodo actual
            key: Clave a eliminar
            
        Returns:
            tuple: (éxito, underflow) donde éxito indica si se eliminó la clave
                  y underflow indica si el nodo quedó con menos claves de las permitidas
        """
        node = self._read_node(node_id)
        min_keys = (self.order - 1) // 2
        
        # Si es un nodo hoja
        if node.is_leaf:
            # Buscar la clave
            i = 0
            while i < len(node.keys) and key != node.keys[i]:
                i += 1
                
            if i == len(node.keys):
                return False, False
            
            record_pos_to_delete = node.children[i]
            
            # last pos
            file_size = os.path.getsize(self.data_path)
            record_size = self.table_ref._get_record_size()
            last_record_pos = file_size - record_size
            
            # Reemplazar el registro a eliminar
            if record_pos_to_delete != last_record_pos:
                with open(self.data_path, 'rb') as f:
                    f.seek(last_record_pos)
                    last_record_data = f.read(record_size)
                    last_record = self.table_ref._deserialize_record(last_record_data)
                    last_key = last_record[self.column_name]
                
                with open(self.data_path, 'r+b') as f:
                    f.seek(record_pos_to_delete)
                    f.write(last_record_data)
                
                # Encontrar el nodo hoja
                last_leaf = self._find_leaf(last_key)
                if last_leaf is not None and last_leaf.page_id != node.page_id:
                    j = 0
                    while j < len(last_leaf.keys):
                        if last_leaf.keys[j] == last_key and last_leaf.children[j] == last_record_pos:
                            last_leaf.children[j] = record_pos_to_delete
                            self._write_node(last_leaf)
                            break
                        j += 1
                    # truncar 
                    with open(self.data_path, 'ab') as f:
                        f.truncate(last_record_pos)
            
            node.keys.pop(i)
            node.children.pop(i)
            
            self._write_node(node)
            
            # underflow??
            underflow = len(node.keys) < min_keys and node.page_id != self.root_page_id
            return True, underflow
            
        # Si es un nodo interno
        else:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            child_id = node.children[i]
            success, child_underflow = self._remove_recursive(child_id, key)
            
            if not success:
                return False, False
                
            if not child_underflow:
                return True, False
            child = self._read_node(child_id)
            return self._handle_underflow(node, child, i)
    
    def _handle_underflow(self, parent, child, child_index):
        """
        Maneja el underflow de un nodo hijo.
        
        Args:
            parent: Nodo padre
            child: Nodo hijo con underflow
            child_index: Índice del hijo en el padre
            
        Returns:
            tuple: (éxito, underflow_propagado) 
        """
        min_keys = (self.order - 1) // 2
        
        # Intentar pedir prestado del hermano izquierdo
        if child_index > 0:
            left_sibling_id = parent.children[child_index - 1]
            left_sibling = self._read_node(left_sibling_id)
            
            if len(left_sibling.keys) > min_keys:
                return self._redistribute_right(parent, left_sibling, child, child_index - 1)
        
        # Intentar pedir prestado del hermano derecho
        if child_index < len(parent.children) - 1:
            right_sibling_id = parent.children[child_index + 1]
            right_sibling = self._read_node(right_sibling_id)
            
            if len(right_sibling.keys) > min_keys:
                return self._redistribute_left(parent, child, right_sibling, child_index)
        
        # Fusionar
        if child_index > 0:
            left_sibling_id = parent.children[child_index - 1]
            left_sibling = self._read_node(left_sibling_id)
            return self._merge_nodes(parent, left_sibling, child, child_index - 1)
        else:
            right_sibling_id = parent.children[child_index + 1]
            right_sibling = self._read_node(right_sibling_id)
            return self._merge_nodes(parent, child, right_sibling, child_index)
    
    def _redistribute_right(self, parent, left, right, key_index):
        """
        Redistribuye claves: mueve una clave del hermano izquierdo al derecho.
        
        Args:
            parent: Nodo padre
            left: Hermano izquierdo
            right: Hermano derecho (con underflow)
            key_index: Índice de la clave del padre entre ambos nodos
            
        Returns:
            tuple: (True, False) - Éxito y no hay underflow propagado
        """
        # Para nodos hoja
        if left.is_leaf:
            key = left.keys.pop()
            ptr = left.children.pop()
            
            right.keys.insert(0, key)
            right.children.insert(0, ptr)
            
            parent.keys[key_index] = right.keys[0]
        else:
            # Para nodos internos
            right.keys.insert(0, parent.keys[key_index])
            parent.keys[key_index] = left.keys.pop()

            ptr = left.children.pop()
            right.children.insert(0, ptr)
        
        self._write_node(parent)
        self._write_node(left)
        self._write_node(right)
        
        return True, False
        
    def _redistribute_left(self, parent, left, right, key_index):
        """
        Redistribuye claves: mueve una clave del hermano derecho al izquierdo.
        
        Args:
            parent: Nodo padre
            left: Hermano izquierdo (con underflow)
            right: Hermano derecho
            key_index: Índice de la clave del padre entre ambos nodos
            
        Returns:
            tuple: (True, False) - Éxito y no hay underflow propagado
        """
        # Para nodos hoja
        if left.is_leaf:
            key = right.keys.pop(0)
            ptr = right.children.pop(0)
            
            left.keys.append(key)
            left.children.append(ptr)
            
            parent.keys[key_index] = right.keys[0]
        else:
            # Para nodos internos
            left.keys.append(parent.keys[key_index])
            parent.keys[key_index] = right.keys.pop(0)
            
            ptr = right.children.pop(0)
            left.children.append(ptr)
        

        self._write_node(parent)
        self._write_node(left)
        self._write_node(right)
        
        return True, False
        
    def _merge_nodes(self, parent, left, right, key_index):
        """
        Fusiona dos nodos hermanos, bajando la clave separadora del padre al nodo izquierdo.
        
        Args:
            parent: Nodo padre
            left: Hermano izquierdo
            right: Hermano derecho
            key_index: Índice de la clave del padre entre ambos nodos
            
        Returns:
            tuple: (True, underflow_propagado) - Éxito y posible underflow en el padre
        """
        if not left.is_leaf:
            left.keys.append(parent.keys[key_index])
        
        left.keys.extend(right.keys)
        left.children.extend(right.children)
        
        if left.is_leaf:
            left.next_leaf = right.next_leaf
        
        parent.keys.pop(key_index)
        parent.children.pop(key_index + 1)
        
        # liberar memoria
        self.free_pages.append(right.page_id)
        
        self._write_node(left)
        self._write_node(parent)
    
        min_keys = (self.order - 1) // 2
        parent_underflow = len(parent.keys) < min_keys and parent.page_id != self.root_page_id
        
        return True, parent_underflow
    
    def rebuild(self):
        pass
    
    def get_all(self):
        """Obtiene todos los registros en el índice"""
        result = []
        
        if self.root_page_id is None:
            return result
        
        # Encontrar la hoja más a la izquierda
        node = self._read_node(self.root_page_id)
        while not node.is_leaf:
            node = self._read_node(node.children[0])
        
        while node is not None:
            for i, key in enumerate(node.keys):
                record_pos = node.children[i]
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    result.append(self.table_ref._deserialize_record(record_data))
            
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
        
        node = self._read_node(self.root_page_id)
        while not node.is_leaf:
            node = self._read_node(node.children[0])
        
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
    
    def free_page(self, page_id):
        """
        Marca una página como libre para su posterior reutilización.
        
        Args:
            page_id (int): ID de la página a liberar
        """
        if page_id is not None and page_id < self.num_pages:
            self.free_pages.append(page_id)
            self._save_metadata()