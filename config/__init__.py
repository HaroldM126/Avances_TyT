import pymysql

# Compatibilidad de PyMySQL con la verificación de versión de Django 5.2
pymysql.version_info = (2, 2, 1, 'final', 0)
pymysql.install_as_MySQLdb()
