# Command line usage

Start a new migration::

```bash
yoyo new ./migrations -m "Add column to foo"
```

Apply migrations from directory ``migrations`` to a PostgreSQL database:

```bash
yoyo apply --database postgresql://scott:tiger@localhost/db ./migrations
```

Rollback migrations previously applied to a MySQL database:

```bash
yoyo rollback --database mysql://scott:tiger@localhost/database ./migrations
```

Reapply (ie rollback then apply again) migrations to a SQLite database at
location ``/home/sheila/important.db``:

```bash
yoyo reapply --database sqlite:////home/sheila/important.db ./migrations
```

By default, yoyo-migrations starts in an interactive mode, prompting you for
each migration file before applying it, making it easy to preview which
migrations to apply and rollback.