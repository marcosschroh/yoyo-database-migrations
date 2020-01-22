# Connections

Database connections are specified using a URL. 

Examples:

### SQLite: use 4 slashes for an absolute database path on unix like platforms

```
database = sqlite:////home/user/mydb.sqlite
```

### SQLite: use 3 slashes for a relative path

```
database = sqlite:///mydb.sqlite
```

### SQLite: absolute path on Windows.

```
database = sqlite:///c:\home\user\mydb.sqlite
```

### MySQL: Network database connection

```
database = mysql://scott:tiger@localhost/mydatabase
```

### MySQL: unix socket connection

```
database = mysql://scott:tiger@/mydatabase?unix_socket=/tmp/mysql.sock
```

### MySQL with the MySQLdb driver (instead of pymysql)

```python
database = mysql+mysqldb://scott:tiger@localhost/mydatabase
```

### MySQL with the MySQLdb driver (Using SSL/TLS to Encrypt a Connection)

```python
database = mysql+mysqldb://scott:tiger@localhost/mydatabase?ssl=yes&sslca=/path/to/cert
```


### PostgreSQL: database connection

```
database = postgresql://scott:tiger@localhost/mydatabase
```

### PostgreSQL: unix socket connection

```
database = postgresql://scott:tiger@/mydatabase
```

### PostgreSQL: changing the schema (via set search_path)

```
database = postgresql://scott:tiger@/mydatabase?schema=some_schema
```