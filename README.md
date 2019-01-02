Yoyo database migrations
========================

Yoyo is a database schema migration tool. You write database migrations
as Python scripts containing raw SQL statements or Python functions.

What does yoyo-migrations do?
-----------------------------

As your database application evolves, changes to the database schema may be
required. Yoyo lets you write migration scripts in Python containing
SQL statements to migrate your database schema to a new version.

A simple migration script looks like this:

.. code::python

    # file: migrations/0001.create-foo.py
    from yoyo import step
    step(
        "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
        "DROP TABLE foo",
    )

Yoyo manages these database migration scripts,
gives you command line tools to apply and rollback migrations,
and manages dependencies between migrations.

Database support
----------------

PostgreSQL, MySQL and SQLite databases are supported.
ODBC and Oracle database backends are available (but unsupported).

Documentation and code
----------------------

`Yoyo migrations documentation <https://ollycope.com/software/yoyo/>`_
\| `Repository <https://bitbucket.org/ollyc/yoyo/>`_
