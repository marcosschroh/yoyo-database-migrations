# Migration files

The migrations directory contains a series of migration scripts. Each
migration script is a python file (``.py``) containing a series of steps. Each
step should comprise a migration query and (optionally) a rollback query:

```python
# file: migrations/0001.create-foo.py

from yoyo import step

step(
    "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
    "DROP TABLE foo"
)
```

Migrations may also declare dependencies on earlier migrations via the
``__depends__`` attribute:

```python
# file: migrations/0002.modify-foo.py

__depends__ = {'0001.create-foo'}

step(
    "ALTER TABLE foo ADD baz INT",
    "ALTER TABLE foo DROP baz"
)
```

The filename of each file (without the .py extension) is used as migration's
identifier. In the absence of a ``__depends__`` attribute, migrations
are applied in filename order, so it's useful to name your files using a date
(eg '20090115-xyz.py') or some other incrementing number.

yoyo creates a table in your target database, ``_yoyo_migration``, to
track which migrations have been applied.

Steps may also take an optional argument ``ignore_errors``, which must be one
of ``apply``, ``rollback``, or ``all``. If in the previous example the table
foo might have already been created by another means, we could add
``ignore_errors='apply'`` to the step to allow the migrations to continue
regardless:

```python
# file: migrations/0001.create-foo.py

from yoyo import step

step(
    "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
    "DROP TABLE foo",
    ignore_errors='apply'
)
```

Steps can also be python functions taking a database connection as
their only argument:

```python
# file: migrations/0002.update-keys.py

from yoyo import step

def do_step(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sysinfo "
        " (osname, hostname, release, version, arch)"
        " VALUES (%s, %s, %s, %s, %s %s)",
        os.uname()
    )

step(do_step)
```