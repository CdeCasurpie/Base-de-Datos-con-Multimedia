import os
import tempfile
import unittest
from database.indexes.multimedia_storage import MultimediaStorage


class TestMultimediaStorage(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ms = MultimediaStorage(self.dir)
        self.sample = b"abc123"
        self.file = os.path.join(
            os.path.dirname(__file__), "..", "database", "indexes", "test_image.jpeg"
        )

    def tearDown(self):
        for f in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, f))
        os.rmdir(self.dir)

    def test_store_and_load_bytes(self):
        path = self.ms.store(self.sample)
        data = self.ms.load(path)
        self.assertEqual(data, self.sample)

    def test_store_and_load_file(self):
        path = self.ms.store(self.file)
        data = self.ms.load(path)
        self.assertTrue(len(data) > 0)

    def test_delete(self):
        path = self.ms.store(self.sample)
        self.assertTrue(self.ms.delete(path))
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
