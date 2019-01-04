# Disabling transactions

You can disable transaction handling within a migration by setting
`__transactional__ = False`, eg:

```python
__transactional__ = False

step("CREATE DATABASE mydb", "DROP DATABASE mydb")
```

This feature is only tested against the PostgreSQL and SQLite backends. 

### PostgreSQL

In PostgreSQL it is an error to run certain statements inside a transaction
block. These include:

```sql
CREATE DATABASE ...
CREATE TABLE <foo>
ALTER TYPE <enum> ...
```

Using `__transactional__ = False` allows you to run these within a migration

### SQLite

In SQLite, the default transactional behavior may prevent other tools from
accessing the database for the duration of the migration. Using
`__transactional__ = False` allows you to work around this limitation.