from HeiderDB.client import HeiderClient

client = HeiderClient()

res = client.send_query("""
CREATE TABLE articulos (
  id INT,
  titulo VARCHAR(200),
  contenido VARCHAR(5000),
  categoria VARCHAR(50),
  tags VARCHAR(500)
) USING INDEX bplus_tree(id);
""")
print(res)

res = client.send_query("""CREATE INVERTED INDEX idx_contenido ON articulos(contenido);""")
print(res)

res = client.send_query("""INSERT INTO articulos VALUES (1, 'Introducción a Python', 'Python es un lenguaje de programación interpretado de alto nivel con una filosofía que enfatiza la legibilidad del código. Python se destaca por su sintaxis clara y su amplia biblioteca estándar.', 'Programación', 'python, programación, tutorial');""")
print(res)

res = client.send_query("SELECT * FROM articulos WHERE contenido CONTAINS 'python base de datos';")
print(res)