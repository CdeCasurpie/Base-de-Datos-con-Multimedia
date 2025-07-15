import os
import sys
import shutil


from HeiderDB.database.table import Table
from HeiderDB.database.indexes.multimedia_index import MultimediaIndex


def clean_data():
    if os.path.exists("test_multimedia_data"):
        shutil.rmtree("test_multimedia_data")


def create_table():
    os.makedirs("test_multimedia_data/tables", exist_ok=True)
    columns = {"id": "INT", "image": "IMAGE"}
    table = Table(
        name="gallery",
        columns=columns,
        primary_key="id",
        page_size=4096,
        index_type="bplus_tree",
        data_dir="test_multimedia_data",
    )
    return table


def test_multimedia_index():
    clean_data()
    table = create_table()
    index = MultimediaIndex(
        table_name=table.name,
        column_name="image",
        data_path=table.data_path,
        table_ref=table,
        page_size=table.page_size,
    )
    index.initialize(media_type="image")
    test_image_path = os.path.join(
        os.path.dirname(__file__), "../database/indexes/test_image.jpeg"
    )
    record = {"id": 1, "image": test_image_path}
    table.add(record)
    index.add(record, key=1)
    assert index.count() == 1
    assert index.search(1) is not None
    results = index.knn_search(test_image_path, k=1)
    assert len(results) == 1
    index.remove(1)
    assert index.count() == 0
    print("MultimediaIndex pasó todas las pruebas básicas")


if __name__ == "__main__":
    test_multimedia_index()
