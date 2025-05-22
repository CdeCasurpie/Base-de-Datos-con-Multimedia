import os
import struct
import json
import math
from database.index_base import IndexBase

class Bucket:
    """
    Clase que representa un bucket en el hash extensible.
    Almacena claves y punteros a registros.
    """
    def __init__(self, bucket_id=None, local_depth=1):
        self.bucket_id = bucket_id
        self.local_depth = local_depth
        self.keys = []       
        self.pointers = []    
        self.next = -1        
    
    def is_full(self, block_factor):
        """Verifica si el bucket está lleno"""
        return len(self.keys) >= block_factor
    
    def add_entry(self, key, pointer):
        """Añade una clave y su puntero asociado"""
        self.keys.append(key)
        self.pointers.append(pointer)
    
    def remove_entry(self, key):
        """Elimina una clave y su puntero asociado"""
        if key in self.keys:
            idx = self.keys.index(key)
            self.keys.pop(idx)
            self.pointers.pop(idx)
            return True
        return False

class ExtendibleHash(IndexBase):
    """
    Implementación de índice Hash Extensible para una tabla.
    """
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size
        
        self.dir_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_hash_dir.json")
        self.bucket_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_hash_buckets.dat")
        
        self.global_depth = 2  
        self.next_bucket_id = 0 
        
        self.key_size = table_ref.get_column_size(column_name)
        self.ptr_size = 8  
        self.col_type = table_ref.columns.get(column_name)
        
        # Cálculo del factor de bloque (cuántas entradas caben en un bucket)
        # Cada bucket tiene: local_depth(4) + num_entries(4) + entries(key_size+ size cada una) + next_pointer(4)
        self.block_factor = math.floor((page_size - 12) / (self.key_size + self.ptr_size))
        
        self.directory = {}
        self._init_index()
    
    def _init_index(self):
        """Inicializa o carga el índice desde archivos existentes"""
        if os.path.exists(self.dir_file):
            self._load_directory()
        else:
            if not os.path.exists(os.path.dirname(self.dir_file)):
                os.makedirs(os.path.dirname(self.dir_file))
            
            for i in range(2**self.global_depth):
                binary = format(i, f'0{self.global_depth}b')
                self.directory[binary] = i % 2  
            
            # Crear los buckets iniciales
            bucket0 = Bucket(bucket_id=0, local_depth=1)
            bucket1 = Bucket(bucket_id=1, local_depth=1)
            
            self.next_bucket_id = 2
            
            # Guardar directorio y buckets
            self._save_directory()
            
            with open(self.bucket_file, "wb") as f:
                self._write_bucket(f, bucket0)
                self._write_bucket(f, bucket1)
    
    def _load_directory(self):
        with open(self.dir_file, "r") as f:
            data = json.load(f)
            self.global_depth = data["global_depth"]
            self.directory = {k: v for k, v in data["directory"].items()}
            self.next_bucket_id = data["next_bucket_id"]
    
    def _save_directory(self):
        with open(self.dir_file, "w") as f:
            json.dump({
                "global_depth": self.global_depth,
                "directory": self.directory,
                "next_bucket_id": self.next_bucket_id
            }, f, indent=4)
    
    def _read_bucket(self, bucket_id):
        with open(self.bucket_file, "rb") as f:
            entry_size = self.key_size + self.ptr_size
            bucket_size = 8 + (self.block_factor * entry_size) + 4  # local_depth + num_entries + entradas + next
            f.seek(bucket_id * bucket_size)
            
            local_depth = struct.unpack('i', f.read(4))[0]
            num_entries = struct.unpack('i', f.read(4))[0]
            
            bucket = Bucket(bucket_id=bucket_id, local_depth=local_depth)
            
            for _ in range(num_entries):
                key = self._deserialize_key(f.read(self.key_size))
                pointer = struct.unpack('q', f.read(self.ptr_size))[0]
                bucket.add_entry(key, pointer)
            
            f.seek((self.block_factor - num_entries) * entry_size, 1)
            
            bucket.next = struct.unpack('i', f.read(4))[0]
            
            return bucket
    
    def _write_bucket(self, file_obj, bucket):
        entry_size = self.key_size + self.ptr_size
        bucket_size = 8 + (self.block_factor * entry_size) + 4
        file_obj.seek(bucket.bucket_id * bucket_size)
        
        file_obj.write(struct.pack('i', bucket.local_depth))
        file_obj.write(struct.pack('i', len(bucket.keys)))
        
        for i in range(len(bucket.keys)):
            key_bytes = self._serialize_key(bucket.keys[i])
            file_obj.write(key_bytes)
            file_obj.write(struct.pack('q', bucket.pointers[i]))
        
        for _ in range(self.block_factor - len(bucket.keys)):
            file_obj.write(b'\x00' * self.key_size)
            file_obj.write(struct.pack('q', 0))
        
        file_obj.write(struct.pack('i', bucket.next))
    
    def _serialize_key(self, key):
        return self.table_ref.serialize_column(self.col_type, key)
    
    def _deserialize_key(self, key_bytes):
        return self.table_ref.deserialize_column(self.col_type, key_bytes)
    
    def hashindex(self, key):
        if isinstance(key, str):
            hash_value = sum(ord(c) for c in key)
        elif isinstance(key, float):
            hash_value = int(key * 1000)
        else:
            hash_value = int(key)
        
        hashid = hash_value % (2 ** self.global_depth)
        return format(hashid, f'0{self.global_depth}b')
    
    def search(self, key):
        bin_index = self.hashindex(key)
        bucket_id = self.directory[bin_index]
        bucket = self._read_bucket(bucket_id)
        
        if key in bucket.keys:
            idx = bucket.keys.index(key)
            record_pos = bucket.pointers[idx]
            
            with open(self.data_path, 'rb') as f:
                f.seek(record_pos)
                record_data = f.read(self.table_ref._get_record_size())
                return self.table_ref._deserialize_record(record_data)
        
        current = bucket
        while current.next != -1:
            current = self._read_bucket(current.next)
            if key in current.keys:
                idx = current.keys.index(key)
                record_pos = current.pointers[idx]
                
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    return self.table_ref._deserialize_record(record_data)
        
        return None
    
    def add(self, record, key):
        record_data = self.table_ref._serialize_record(record)
        record_pos = self._append_record_to_data_file(record_data)
        
        self._add_key_with_position(key, record_pos)
    
    def _append_record_to_data_file(self, record_data):
        with open(self.data_path, 'ab') as f:
            record_pos = f.tell()
            f.write(record_data)
            return record_pos
    
    def _add_key_with_position(self, key, record_pos):
        bin_index = self.hashindex(key)
        bucket_id = self.directory[bin_index]
        bucket = self._read_bucket(bucket_id)
        
        if key in bucket.keys:
            idx = bucket.keys.index(key)
            bucket.pointers[idx] = record_pos
            with open(self.bucket_file, "r+b") as f:
                self._write_bucket(f, bucket)
            return
        
        current = bucket
        while current.next != -1:
            current = self._read_bucket(current.next)
            if key in current.keys:
                idx = current.keys.index(key)
                current.pointers[idx] = record_pos
                with open(self.bucket_file, "r+b") as f:
                    self._write_bucket(f, current)
                return
        
        if not bucket.is_full(self.block_factor):
            bucket.add_entry(key, record_pos)
            with open(self.bucket_file, "r+b") as f:
                self._write_bucket(f, bucket)
            return
        
        if bucket.next == -1:
            # Si la profundidad local es igual a la global, duplicar el directorio
            if bucket.local_depth == self.global_depth:
                self._double_directory()
                self._add_key_with_position(key, record_pos)
            else:
                # Dividir el bucket
                self._split_bucket(bucket_id)
                self._add_key_with_position(key, record_pos)
        else:
            current = bucket
            while current.next != -1:
                current = self._read_bucket(current.next)
                if not current.is_full(self.block_factor):
                    current.add_entry(key, record_pos)
                    with open(self.bucket_file, "r+b") as f:
                        self._write_bucket(f, current)
                    return
            
            overflow = Bucket(bucket_id=self.next_bucket_id, local_depth=current.local_depth)
            self.next_bucket_id += 1
            
            overflow.add_entry(key, record_pos)
            current.next = overflow.bucket_id
            
            with open(self.bucket_file, "r+b") as f:
                self._write_bucket(f, current)
                self._write_bucket(f, overflow)
            
            self._save_directory()
    
    def _double_directory(self):
        self.global_depth += 1
        new_directory = {}
        
        # Por cada entrada en el directorio actual, crear dos nuevas entradas
        for bin_index, bucket_id in self.directory.items():
            new_directory['0' + bin_index] = bucket_id
            new_directory['1' + bin_index] = bucket_id
        
        self.directory = new_directory
        self._save_directory()
    
    def _split_bucket(self, bucket_id):
        bucket = self._read_bucket(bucket_id)
        local_depth = bucket.local_depth
        
        new_bucket = Bucket(bucket_id=self.next_bucket_id, local_depth=local_depth + 1)
        self.next_bucket_id += 1
        
        bucket.local_depth = local_depth + 1
        
        old_keys = bucket.keys
        old_pointers = bucket.pointers
        
        bucket.keys = []
        bucket.pointers = []
        
        for bin_index, bid in self.directory.items():
            if bid == bucket_id:
                # Usar el bit correspondiente para decidir si redirigir
                bit_pos = len(bin_index) - local_depth - 1
                if bit_pos >= 0 and bin_index[bit_pos] == '1':
                    self.directory[bin_index] = new_bucket.bucket_id
        
        self._save_directory()
        
        with open(self.bucket_file, "r+b") as f:
            self._write_bucket(f, bucket)
            self._write_bucket(f, new_bucket)
        
        for i in range(len(old_keys)):
            self._add_key_with_position(old_keys[i], old_pointers[i])
    
    def remove(self, key):
        bin_index = self.hashindex(key)
        bucket_id = self.directory[bin_index]
        bucket = self._read_bucket(bucket_id)
        
        if key in bucket.keys:
            bucket.remove_entry(key)
            with open(self.bucket_file, "r+b") as f:
                self._write_bucket(f, bucket)
            
            if len(bucket.keys) == 0 and bucket.local_depth > 1:
                self._merge_buckets()
            
            return True
        
        current = bucket
        prev = None
        while current.next != -1:
            prev = current
            current = self._read_bucket(current.next)
            
            if key in current.keys:
                current.remove_entry(key)
                
                if len(current.keys) == 0:
                    prev.next = current.next
                    with open(self.bucket_file, "r+b") as f:
                        self._write_bucket(f, prev)
                else:
                    with open(self.bucket_file, "r+b") as f:
                        self._write_bucket(f, current)
                
                return True
        
        return False
    
    def _merge_buckets(self):
        buckets_by_prefix = {}
        
        for bin_index, bucket_id in self.directory.items():
            bucket = self._read_bucket(bucket_id)
            if bucket.local_depth > 1:
                prefix = bin_index[:-1]
                if prefix not in buckets_by_prefix:
                    buckets_by_prefix[prefix] = []
                if bucket_id not in [b[0] for b in buckets_by_prefix[prefix]]:
                    buckets_by_prefix[prefix].append((bucket_id, len(bucket.keys)))
        
        for prefix, bucket_list in buckets_by_prefix.items():
            if len(bucket_list) == 2:
                bucket1_id, bucket1_size = bucket_list[0]
                bucket2_id, bucket2_size = bucket_list[1]
                
                bucket1 = self._read_bucket(bucket1_id)
                bucket2 = self._read_bucket(bucket2_id)
                
                if (bucket1.local_depth == bucket2.local_depth and 
                    bucket1_size + bucket2_size <= self.block_factor):
                    
                    for i in range(len(bucket2.keys)):
                        bucket1.add_entry(bucket2.keys[i], bucket2.pointers[i])
                    
                    bucket1.local_depth -= 1
                    
                    for bin_idx, b_id in self.directory.items():
                        if bin_idx.startswith(prefix):
                            self.directory[bin_idx] = bucket1_id
                    
                    bucket2.keys = []
                    bucket2.pointers = []
                    bucket2.local_depth = 0
                    
                    with open(self.bucket_file, "r+b") as f:
                        self._write_bucket(f, bucket1)
                        self._write_bucket(f, bucket2)
                    
                    self._save_directory()
                    
                    self._reduce_global_depth_if_possible()
                    
                    return True
        
        return False
    
    def _reduce_global_depth_if_possible(self):
        max_local_depth = 0
        for bucket_id in set(self.directory.values()):
            bucket = self._read_bucket(bucket_id)
            max_local_depth = max(max_local_depth, bucket.local_depth)
        
        if max_local_depth < self.global_depth:
            self.global_depth -= 1
            
            new_directory = {}
            unique_entries = set()
            
            for i in range(2**self.global_depth):
                bin_index = format(i, f'0{self.global_depth}b')
                old_idx = '0' + bin_index  
                bucket_id = self.directory[old_idx]
                
                new_directory[bin_index] = bucket_id
                unique_entries.add(bucket_id)
            
            self.directory = new_directory
            self._save_directory()
            
            return True
        
        return False
    
    def count(self):
        count = 0
        
        unique_buckets = set(self.directory.values())
        
        for bucket_id in unique_buckets:
            bucket = self._read_bucket(bucket_id)
            count += len(bucket.keys)
            
            current = bucket
            while current.next != -1:
                current = self._read_bucket(current.next)
                count += len(current.keys)
        
        return count
    
    def get_all(self):
        result = []
        
        unique_buckets = set(self.directory.values())
        
        for bucket_id in unique_buckets:
            bucket = self._read_bucket(bucket_id)
            
            for i in range(len(bucket.keys)):
                record_pos = bucket.pointers[i]
                with open(self.data_path, 'rb') as f:
                    f.seek(record_pos)
                    record_data = f.read(self.table_ref._get_record_size())
                    result.append(self.table_ref._deserialize_record(record_data))
            
            current = bucket
            while current.next != -1:
                current = self._read_bucket(current.next)
                for i in range(len(current.keys)):
                    record_pos = current.pointers[i]
                    with open(self.data_path, 'rb') as f:
                        f.seek(record_pos)
                        record_data = f.read(self.table_ref._get_record_size())
                        result.append(self.table_ref._deserialize_record(record_data))
        
        return result
    
    def range_search(self, begin_key, end_key=None):
        """
        Nota: El hash no es óptimo para búsquedas por rango
        """
        if end_key is None:
            end_key = begin_key
        
        result = []
        
        # En un hash, no hay forma eficiente de hacer búsqueda por rango sin recorrer todo
        all_records = self.get_all()
        
        for record in all_records:
            key = record[self.column_name]
            if begin_key <= key <= end_key:
                result.append(record)
        
        return result
    
    def rebuild(self):
        all_records = self.get_all()
        
        if os.path.exists(self.dir_file):
            os.remove(self.dir_file)
        if os.path.exists(self.bucket_file):
            os.remove(self.bucket_file)
        
        self.global_depth = 2
        self.next_bucket_id = 0
        self._init_index()
        
        for record in all_records:
            key = record[self.column_name]
            self.add(record, key)
        
        return True
    
    def _get_record_size(self):
        return self.table_ref._get_record_size()
