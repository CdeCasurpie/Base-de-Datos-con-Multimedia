import os
import json
import struct
from database.index_base import IndexBase

class ISAMSparseIndex(IndexBase):
    """
    ISAM Sparse dinámico, con dos niveles de índices dispersos:
      - root: punteros dispersos a páginas de nivel 1
      - levels: punteros dispersos a páginas de datos físicas

    Cada página de datos (y sus overflows) está en self.pages, con:
      - entries: lista de {"key","pos"}
      - next_overflow: índice de su overflow o -1
      - next_data: índice de la siguiente página de datos o -1

    Las páginas de datos se mantienen ordenadas internamente,
    pero las páginas de overflow NO se reordenan tras insertar.
    """
    def __init__(self, table_name, column_name, data_path, table_ref, page_size):
        super().__init__(table_name, column_name, data_path, table_ref, page_size)
        self.index_file     = os.path.join(os.path.dirname(data_path),
                                           f"{table_name}_{column_name}_isam_index.json")
        self.data_path      = data_path
        self.table_ref      = table_ref
        self.page_size      = page_size
        self.block_factor   = page_size // table_ref._get_record_size()
        self.deleted_marker = -1

        # Metadatos dinámicos
        self.pages = []                  # todas las data pages + overflows
        self.index = {"root": [],        # nivel 0 disperso
                      "levels": []}      # nivel 1 disperso

        self._init_index()

    def _init_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, "r") as f:
                data = json.load(f)
            self.pages = data["pages"]
            self.index = {"root": data["root"], "levels": data["levels"]}
        else:
            self.rebuild()

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump({
                "pages":  self.pages,
                "root":   self.index["root"],
                "levels": self.index["levels"]
            }, f, indent=4)

    def rebuild(self):
        """
        1) Leer todo el .dat y filtrar eliminados
        2) Ordenar si hiciera falta
        3) Reescribir .dat
        4) Partir en páginas físicas (self.pages) sin overflows
        5) Construir índices dispersos root y levels
        """
        rs = self.table_ref._get_record_size()
        registros = []

        # 1) Leer y filtrar
        with open(self.data_path, 'rb') as f:
            while True:
                buf = f.read(rs)
                if not buf:
                    break
                rec = self.table_ref._deserialize_record(buf)
                if rec[self.column_name] != self.deleted_marker:
                    registros.append(rec)

        # 2) Ordenar si hace falta
        if any(registros[i][self.column_name] > registros[i+1][self.column_name]
               for i in range(len(registros)-1)):
            registros.sort(key=lambda r: r[self.column_name])

        # 3) Reescribir .dat
        with open(self.data_path, 'wb') as f:
            for rec in registros:
                f.write(self.table_ref._serialize_record(rec))

        # 4) Partir en páginas físicas
        pages = [
            registros[i:i+self.block_factor]
            for i in range(0, len(registros), self.block_factor)
        ]
        self.pages = []
        for i, page in enumerate(pages):
            entries = [
                {"key": rec[self.column_name], "pos": i*self.block_factor + j}
                for j, rec in enumerate(page)
            ]
            next_data = i+1 if i+1 < len(pages) else -1
            self.pages.append({
                "entries": entries,
                "next_overflow": -1,
                "next_data": next_data
            })

        # 5) Construir nivel 1 disperso: un puntero por data page
        pointers = [
            {"key": p["entries"][0]["key"], "page": idx}
            for idx, p in enumerate(self.pages) if p["entries"]
        ]
        self.index["levels"] = [
            pointers[k:k+self.block_factor]
            for k in range(0, len(pointers), self.block_factor)
        ]

        # Construir root disperso: un puntero por bloque de nivel 1
        self.index["root"] = [
            {"key": blk[0]["key"], "level1_block": idx}
            for idx, blk in enumerate(self.index["levels"]) if blk
        ]

        self._save_index()

    def _read_record(self, pos):
        rs = self.table_ref._get_record_size()
        with open(self.data_path, 'rb') as f:
            f.seek(pos * rs)
            buf = f.read(rs)
        return self.table_ref._deserialize_record(buf)

    def _find_level1_block(self, key):
        arr = self.index["root"]
        lo, hi = 0, len(arr) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if key < arr[mid]["key"]:
                hi = mid - 1
            else:
                lo = mid + 1
        idx = hi if hi >= 0 else 0
        return arr[idx]["level1_block"]

    def _find_data_page(self, level1_block, key):
        arr = self.index["levels"][level1_block]
        lo, hi = 0, len(arr) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if key < arr[mid]["key"]:
                hi = mid - 1
            else:
                lo = mid + 1
        idx = hi if hi >= 0 else 0
        return arr[idx]["page"]

    def search(self, key):
        # Si no hay páginas todavía, devolver None
        if not self.pages:
            return None

        lvl1 = self._find_level1_block(key)
        dp   = self._find_data_page(lvl1, key)

        # revisar data page principal
        page = self.pages[dp]
        for e in page["entries"]:
            if e["key"] == key:
                return self._read_record(e["pos"])

        # revisar overflows encadenados
        ov = page["next_overflow"]
        while ov != -1:
            for e in self.pages[ov]["entries"]:
                if e["key"] == key:
                    return self._read_record(e["pos"])
            ov = self.pages[ov]["next_overflow"]

        return None

    def range_search(self, lo_key, hi_key=None):
        if hi_key is None:
            hi_key = lo_key
        # Si no hay páginas, no hay nada
        if not self.pages:
            return []

        results = []
        lvl1 = self._find_level1_block(lo_key)
        dp   = self._find_data_page(lvl1, lo_key)

        # recorrer páginas físicas en orden
        while dp != -1:
            page = self.pages[dp]
            queue = [dp]
            while queue:
                idx = queue.pop(0)
                blk = self.pages[idx]
                for e in blk["entries"]:
                    k = e["key"]
                    if k == self.deleted_marker:
                        continue
                    if k > hi_key:
                        return results
                    if k >= lo_key:
                        results.append(self._read_record(e["pos"]))
                if blk["next_overflow"] != -1:
                    queue.append(blk["next_overflow"])
            dp = page["next_data"]

        return results

    def add(self, record, key):
        rs = self.table_ref._get_record_size()
        # 1) Append al datafile
        with open(self.data_path, 'ab') as f:
            f.write(self.table_ref._serialize_record(record))
            pos = (f.tell() // rs) - 1

        # 2) Si no hay páginas, reconstruir índice completo
        if not self.pages:
            self.rebuild()
            return

        # 3) Ubicar data page destino
        lvl1 = self._find_level1_block(key)
        dp   = self._find_data_page(lvl1, key)

        # 4) Si hay espacio en la página, insertar y reordenar
        if len(self.pages[dp]["entries"]) < self.block_factor:
            entries = self.pages[dp]["entries"]
            entries.append({"key": key, "pos": pos})
            entries.sort(key=lambda e: e["key"])
            self._save_index()
            return

        # 5) Buscar overflow con espacio
        prev, ov = dp, self.pages[dp]["next_overflow"]
        while ov != -1:
            if len(self.pages[ov]["entries"]) < self.block_factor:
                self.pages[ov]["entries"].append({"key": key, "pos": pos})
                self._save_index()
                return
            prev, ov = ov, self.pages[ov]["next_overflow"]

        # 6) Crear nuevo overflow si todos llenos
        new_idx = len(self.pages)
        self.pages.append({
            "entries": [{"key": key, "pos": pos}],
            "next_overflow": -1,
            "next_data": self.pages[dp]["next_data"]
        })
        self.pages[prev]["next_overflow"] = new_idx
        self._save_index()

    def remove(self, key):
        rs = self.table_ref._get_record_size()
        # Si no hay páginas, no hay nada que borrar
        if not self.pages:
            return False

        lvl1 = self._find_level1_block(key)
        dp   = self._find_data_page(lvl1, key)

        with open(self.data_path, 'r+b') as f:
            queue = [dp]
            while queue:
                idx = queue.pop(0)
                blk = self.pages[idx]
                for i, e in enumerate(blk["entries"]):
                    if e["key"] == key:
                        pos = e["pos"]
                        f.seek(pos * rs)
                        rec = self.table_ref._deserialize_record(f.read(rs))
                        rec[self.column_name] = self.deleted_marker
                        f.seek(pos * rs)
                        f.write(self.table_ref._serialize_record(rec))
                        blk["entries"].pop(i)
                        self._save_index()
                        return True
                if blk["next_overflow"] != -1:
                    queue.append(blk["next_overflow"])
        return False

    def count(self):
        rs = self.table_ref._get_record_size()
        return os.path.getsize(self.data_path) // rs

    def get_all(self):
        total = self.count()
        results = []
        for pos in range(total):
            rec = self._read_record(pos)
            if rec[self.column_name] != self.deleted_marker:
                results.append(rec)
        return results
