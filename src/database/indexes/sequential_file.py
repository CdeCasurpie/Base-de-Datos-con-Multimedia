import os
import struct
import json
import math
from database.index_base import IndexBase

class SequentialFile(IndexBase):
    
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.table_name = table_name
        self.column_name = column_name
        self.data_path = data_path
        self.table_ref = table_ref
        self.page_size = page_size
        
        self.index_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_seq_index.dat")
        self.overflow_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_seq_overflow.dat")
        self.metadata_file = os.path.join(os.path.dirname(data_path), f"{table_name}_{column_name}_seq_metadata.json")
        
        self.key_size = table_ref.get_column_size(column_name)
        self.ptr_size = 8  
        self.next_size = 8 
        self.col_type = table_ref.columns.get(column_name)
        
        self.entry_size = self.key_size + self.ptr_size + self.next_size
        
        self.entries_per_page = math.floor(page_size / self.entry_size)
        
        self.record_count = 0
        self.overflow_count = 0
        self.active_entries = 0  
        self._init_index()
    
    def _init_index(self):
        if os.path.exists(self.metadata_file):
            self._load_metadata()
        else:
            if not os.path.exists(os.path.dirname(self.index_file)):
                os.makedirs(os.path.dirname(self.index_file))
            
            with open(self.index_file, 'wb') as f:
                pass
            
            with open(self.overflow_file, 'wb') as f:
                pass
            self._save_metadata()
    
    def _load_metadata(self):
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.record_count = metadata.get('record_count', 0)
        self.overflow_count = metadata.get('overflow_count', 0)
        self.active_entries = metadata.get('active_entries', self.record_count)
    
    def _save_metadata(self):
        metadata = {
            'table_name': self.table_name,
            'column_name': self.column_name,
            'record_count': self.record_count,
            'overflow_count': self.overflow_count,
            'active_entries': self.active_entries,
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)
    
    def _serialize_key(self, key):
        return self.table_ref.serialize_column(self.col_type, key)
    
    def _deserialize_key(self, key_bytes):
        return self.table_ref.deserialize_column(self.col_type, key_bytes)
    
    def _write_index_entry(self, file_obj, key, pointer, next_pointer):
        key_bytes = self._serialize_key(key)
        file_obj.write(key_bytes)
        file_obj.write(struct.pack('!q', pointer))
        file_obj.write(struct.pack('!q', next_pointer))
    
    def _read_index_entry(self, file_obj):
        try:
            start_pos = file_obj.tell()

            key_bytes = file_obj.read(self.key_size)
            if not key_bytes or len(key_bytes) < self.key_size:
                return None, None, None

            if key_bytes == b'\x00' * self.key_size:
                file_obj.read(self.ptr_size + self.next_size)
                return None, None, None

            pointer_bytes = file_obj.read(self.ptr_size)
            next_pointer_bytes = file_obj.read(self.next_size)

            if len(pointer_bytes) < self.ptr_size or len(next_pointer_bytes) < self.next_size:
                return None, None, None

            key = self._deserialize_key(key_bytes)
            if key is None:
                return None, None, None

            pointer = struct.unpack('!q', pointer_bytes)[0]
            next_pointer = struct.unpack('!q', next_pointer_bytes)[0]

            if pointer < 0 and pointer != -1:
                return None, None, None
            if next_pointer < -1:
                return None, None, None

            return key, pointer, next_pointer

        except (struct.error, ValueError, TypeError) as e:
            return None, None, None

    def search(self, key):
        if self.active_entries == 0:
            return None
        
        with open(self.index_file, 'rb') as f:
            position = self._binary_search(f, key)
            
            if position >= 0:
                f.seek(position)
                found_key, record_pos, _ = self._read_index_entry(f)
                
                if found_key == key:
                    return self._get_record_at_position(record_pos)
            else:
                insert_pos = -position - 1
                
                if insert_pos > 0:
                    f.seek((insert_pos - 1) * self.entry_size)
                    _, _, overflow_ptr = self._read_index_entry(f)
                    
                    while overflow_ptr != -1:
                        with open(self.overflow_file, 'rb') as of:
                            of.seek(overflow_ptr)
                            entry = self._read_index_entry(of)

                            if entry is None:
                                break

                            of_key, of_pos, next_overflow = entry

                            if of_key == key:
                                return self._get_record_at_position(of_pos)

                            overflow_ptr = next_overflow
        
        return None
    
    def _binary_search(self, file_obj, key):
        left = 0
        right = self._get_max_valid_entries() - 1
        
        while left <= right:
            mid = (left + right) // 2
            file_obj.seek(mid * self.entry_size)
            
            mid_key, _, _ = self._read_index_entry(file_obj)
            
            if mid_key is None:
                valid_pos = self._find_next_valid_entry(file_obj, mid)
                if valid_pos == -1:
                    right = mid - 1
                    continue
                else:
                    file_obj.seek(valid_pos * self.entry_size)
                    mid_key, _, _ = self._read_index_entry(file_obj)
                    mid = valid_pos
            
            if mid_key == key:
                return mid * self.entry_size  
            elif mid_key < key:
                left = mid + 1
            else:
                right = mid - 1
        
        return -(left + 1) 
    
    def _get_max_valid_entries(self):
        try:
            file_size = os.path.getsize(self.index_file)
            return file_size // self.entry_size
        except OSError:
            return 0
    
    def _find_next_valid_entry(self, file_obj, start_pos):
        max_entries = self._get_max_valid_entries()
        
        for i in range(start_pos + 1, max_entries):
            file_obj.seek(i * self.entry_size)
            key, _, _ = self._read_index_entry(file_obj)
            if key is not None:
                return i
        
        return -1  
    
    def _get_record_at_position(self, position):
        if position is None or position < 0:
            return None
            
        try:
            with open(self.data_path, 'rb') as f:
                file_size = os.path.getsize(self.data_path)
                if position >= file_size:
                    return None
                    
                f.seek(position)
                record_size = self.table_ref._get_record_size()

                if position + record_size > file_size:
                    return None
                    
                record_data = f.read(record_size)
                if len(record_data) < record_size:
                    return None
                    
                return self.table_ref._deserialize_record(record_data)
                
        except (OSError, IOError, struct.error, ValueError):
            return None

    def range_search(self, begin_key, end_key=None):
        result = []
        
        if self.active_entries == 0:
            return result
        
        if end_key is None:
            end_key = begin_key
        
        with open(self.index_file, 'rb') as f:
            position = self._binary_search(f, begin_key)
            
            if position < 0:
                position = -position - 1
                position = position * self.entry_size
            
            max_file_size = os.path.getsize(self.index_file)
            if position >= max_file_size or position < 0:
                position = 0
            
            f.seek(position)
            while True:
                entry_pos = f.tell()
                if entry_pos >= max_file_size:
                    break
                
                key, record_pos, next_ptr = self._read_index_entry(f)
                
                if key is None:
                    continue 
                
                if key > end_key:
                    break
                
                if key >= begin_key:
                    record = self._get_record_at_position(record_pos)
                    if record is not None:
                        result.append(record)
                
                while next_ptr != -1:
                    with open(self.overflow_file, 'rb') as of:
                        of.seek(next_ptr)
                        of_key, of_pos, next_ptr = self._read_index_entry(of)
                        
                        if of_key is not None and begin_key <= of_key <= end_key:
                            overflow_record = self._get_record_at_position(of_pos)
                            if overflow_record is not None:
                                result.append(overflow_record)
        
        return result
    
    def add(self, record, key):
        record_data = self.table_ref._serialize_record(record)
        record_pos = self._append_record_to_data_file(record_data)
        
        if self.active_entries == 0:
            with open(self.index_file, 'wb') as f:
                self._write_index_entry(f, key, record_pos, -1)
            self.record_count += 1
            self.active_entries += 1
            self._save_metadata()
            return
        
        with open(self.index_file, 'rb') as f:
            position = self._binary_search(f, key)
            
            if position >= 0:
                with open(self.index_file, 'r+b') as f:
                    f.seek(position)
                    _, _, next_ptr = self._read_index_entry(f)
                    f.seek(position)
                    self._write_index_entry(f, key, record_pos, next_ptr)
                return
        
        insert_pos = -position - 1
        null_pos = self._find_null_position()
        
        if null_pos != -1:
            with open(self.index_file, 'r+b') as f:
                f.seek(null_pos * self.entry_size)
                self._write_index_entry(f, key, record_pos, -1)
            self.active_entries += 1
        else:
            max_entries = self._get_max_valid_entries()
            
            if insert_pos < max_entries:
                with open(self.index_file, 'r+b') as f:
                    f.seek(insert_pos * self.entry_size)
                    prev_key, prev_pos, prev_next_ptr = self._read_index_entry(f)
                    
                    if prev_key is not None: 
                        with open(self.overflow_file, 'a+b') as of:
                            overflow_pos = of.tell()
                            self._write_index_entry(of, key, record_pos, prev_next_ptr)
                        
                        f.seek(insert_pos * self.entry_size)
                        self._write_index_entry(f, prev_key, prev_pos, overflow_pos)
                        self.overflow_count += 1
                    else:
                        f.seek(insert_pos * self.entry_size)
                        self._write_index_entry(f, key, record_pos, -1)
            else:
               
                with open(self.index_file, 'a+b') as f:
                    self._write_index_entry(f, key, record_pos, -1)
            
            self.active_entries += 1
        
        self.record_count += 1
        self._save_metadata()
        
        
        if (self.overflow_count > self.active_entries // 2 or 
            (self.record_count - self.active_entries) > self.active_entries // 3):
            self.rebuild()
    
    def _find_null_position(self):
        try:
            max_entries = self._get_max_valid_entries()
            
            with open(self.index_file, 'rb') as f:
                for i in range(max_entries):
                    f.seek(i * self.entry_size)
                    key, _, _ = self._read_index_entry(f)
                    if key is None:
                        return i
            
            return -1 
        except OSError:
            return -1
    
    def _append_record_to_data_file(self, record_data):
        with open(self.data_path, 'ab') as f:
            record_pos = f.tell()
            f.write(record_data)
            return record_pos
    
    def remove(self, key):
        if self.active_entries == 0:
            return False
        
        try:
            with open(self.index_file, 'r+b') as f:
                position = self._binary_search(f, key)
                
                if position >= 0:
                    f.seek(position)
                    found_key, record_pos, next_ptr = self._read_index_entry(f)
                    
                    if found_key != key:
                        return False
                    
                    if next_ptr != -1:
                        try:
                            with open(self.overflow_file, 'rb') as of:
                                of.seek(next_ptr)
                                of_key, of_pos, of_next = self._read_index_entry(of)
                                
                                if of_key is not None and of_pos is not None:
                                    f.seek(position)
                                    self._write_index_entry(f, of_key, of_pos, of_next)
                                    self.overflow_count -= 1
                                else:
                                    f.seek(position)
                                    f.write(b'\x00' * self.entry_size)
                        except (OSError, IOError):
                            f.seek(position)
                            f.write(b'\x00' * self.entry_size)
                    else:
                        # Marcar entrada como vacía
                        f.seek(position)
                        f.write(b'\x00' * self.entry_size)
                    
                    self.record_count -= 1
                    self.active_entries -= 1
                    self._save_metadata()
                    
                    # Reconstruir si hay muchas entradas vacías
                    if ((self.record_count - self.active_entries) > self.active_entries // 2 or
                        self.overflow_count > self.active_entries // 2):
                        self.rebuild()
                    
                    return True
                else:
                    
                    insert_pos = -position - 1
                    
                    if insert_pos > 0:
                        try:
                            f.seek((insert_pos - 1) * self.entry_size)
                            prev_key, prev_pos, overflow_ptr = self._read_index_entry(f)
                            
                            prev_of_ptr = None
                            curr_of_ptr = overflow_ptr
                            
                            while curr_of_ptr != -1 and curr_of_ptr >= 0:
                                with open(self.overflow_file, 'r+b') as of:
                                    of.seek(curr_of_ptr)
                                    of_key, of_pos, next_overflow = self._read_index_entry(of)
                                    
                                    if of_key == key:
                                        
                                        if prev_of_ptr is None:
                                            f.seek((insert_pos - 1) * self.entry_size)
                                            self._write_index_entry(f, prev_key, prev_pos, next_overflow)
                                        else:
                                            of.seek(prev_of_ptr)
                                            prev_of_key, prev_of_pos, _ = self._read_index_entry(of)
                                            if prev_of_key is not None:
                                                of.seek(prev_of_ptr)
                                                self._write_index_entry(of, prev_of_key, prev_of_pos, next_overflow)
                                        
                                        self.record_count -= 1
                                        self.overflow_count -= 1
                                        self.active_entries -= 1
                                        self._save_metadata()
                                        return True
                                    
                                    prev_of_ptr = curr_of_ptr
                                    curr_of_ptr = next_overflow
                                    
                        except (OSError, IOError):
                            pass
        
        except (OSError, IOError):
            pass
        
        return False

    def rebuild(self):
        """Reconstruye el índice eliminando entradas nulas y reorganizando"""
        entries = []
        
        
        try:
            with open(self.index_file, 'rb') as f:
                max_entries = self._get_max_valid_entries()
                
                for i in range(max_entries):
                    f.seek(i * self.entry_size)
                    key, record_pos, next_ptr = self._read_index_entry(f)
                    
                    if key is None:
                        continue  
                        
                    entries.append((key, record_pos))
                    
                   
                    current_overflow_ptr = next_ptr
                    while current_overflow_ptr != -1:
                        try:
                            with open(self.overflow_file, 'rb') as of:
                                of.seek(current_overflow_ptr)
                                of_key, of_pos, next_overflow_ptr = self._read_index_entry(of)
                                if of_key is not None:
                                    entries.append((of_key, of_pos))
                                current_overflow_ptr = next_overflow_ptr
                        except (OSError, IOError):
                            break
        except (OSError, IOError):
            pass
        
        # Ordenar todas las entradas por clave
        entries.sort(key=lambda x: x[0])
        
        # Reescribir el archivo principal con todas las entradas ordenadas
        try:
            with open(self.index_file, 'wb') as f:
                for key, record_pos in entries:
                    self._write_index_entry(f, key, record_pos, -1)
            
            # Limpiar el archivo de overflow
            with open(self.overflow_file, 'wb') as f:
                pass
            
            # Actualizar contadores
            self.record_count = len(entries)
            self.active_entries = len(entries)
            self.overflow_count = 0
            self._save_metadata()
            
        except (OSError, IOError):
            pass
    
    def count(self):
        return self.active_entries
    
    def get_all(self):
        result = []
        
        if self.active_entries == 0:
            return result
            
        try:
            with open(self.index_file, 'rb') as f:
                max_entries = self._get_max_valid_entries()
                
                for i in range(max_entries):
                    f.seek(i * self.entry_size)
                    key, record_pos, next_ptr = self._read_index_entry(f)
                    
                    if key is None or record_pos is None:
                        continue 
                    
                   
                    if record_pos >= 0:
                        try:
                            record = self._get_record_at_position(record_pos)
                            if record is not None:
                                result.append(record)
                        except (OSError, IOError, struct.error):
                            continue
                    
                    current_overflow_ptr = next_ptr
                    while current_overflow_ptr != -1 and current_overflow_ptr >= 0:
                        try:
                            with open(self.overflow_file, 'rb') as of:
                                of.seek(current_overflow_ptr)
                                of_key, of_pos, next_overflow = self._read_index_entry(of)
                                
                                if of_key is not None and of_pos is not None and of_pos >= 0:
                                    try:
                                        overflow_record = self._get_record_at_position(of_pos)
                                        if overflow_record is not None:
                                            result.append(overflow_record)
                                    except (OSError, IOError, struct.error):
                                        pass
                                
                                current_overflow_ptr = next_overflow
                                
                        except (OSError, IOError):
                            break
                            
        except (OSError, IOError):
            return result
                
        return result
