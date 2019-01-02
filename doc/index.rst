Yoyo database migrations
########################

Yoyo is a Python database schema migration tool. You write migrations as Python
scripts containing raw SQL statements or Python functions.
They can be as simple as this:

.. code:: python

   # file: migrations/0001.create-foo.py
   from yoyo import step
   steps = [
      step("CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
           "DROP TABLE foo"),
   ]

Command line usage
==================

Start a new migration::

  yoyo new ./migrations -m "Add column to foo"

Apply migrations from directory ``migrations`` to a PostgreSQL database::

   yoyo apply --database postgresql://scott:tiger@localhost/db ./migrations

Rollback migrations previously applied to a MySQL database::

   yoyo rollback --database mysql://scott:tiger@localhost/database ./migrations

Reapply (ie rollback then apply again) migrations to a SQLite database at
location ``/home/sheila/important.db``::

    yoyo reapply --database sqlite:////home/sheila/important.db ./migrations

By default, yoyo-migrations starts in an interactive mode, prompting you for
each migration file before applying it, making it easy to preview which
migrations to apply and rollback.

Connections
-----------

Database connections are specified using a URL. Examples::

  # SQLite: use 4 slashes for an absolute database path on unix like platforms
  database = sqlite:////home/user/mydb.sqlite

  # SQLite: use 3 slashes for a relative path
  database = sqlite:///mydb.sqlite

  # SQLite: absolute path on Windows.
  database = sqlite:///c:\home\user\mydb.sqlite

  # MySQL: Network database connection
  database = mysql://scott:tiger@localhost/mydatabase

  # MySQL: unix socket connection
  database = mysql://scott:tiger@/mydatabase?unix_socket=/tmp/mysql.sock

  # MySQL with the MySQLdb driver (instead of pymysql)
  database = mysql+mysqldb://scott:tiger@localhost/mydatabase

  # PostgreSQL: database connection
  database = postgresql://scott:tiger@localhost/mydatabase

  # PostgreSQL: unix socket connection
  database = postgresql://scott:tiger@/mydatabase

  # PostgreSQL: changing the schema (via set search_path)
  database = postgresql://scott:tiger@/mydatabase?schema=some_schema

Password security
-----------------

You can specify your database username and password either as part of the
database connection string on the command line (exposing your database
password in the process list)
or in a configuration file where other users may be able to read it.

The ``-p`` or ``--prompt-password`` flag causes yoyo to prompt
for a password, helping prevent your credentials from being leaked.

Migration files
===============

The migrations directory contains a series of migration scripts. Each
migration script is a python file (``.py``) containing a series of steps. Each
step should comprise a migration query and (optionally) a rollback query:

.. code:: python

    #
    # file: migrations/0001.create-foo.py
    #
    from yoyo import step
    step(
        "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
        "DROP TABLE foo",
    )

Migrations may also declare dependencies on earlier migrations via the
``__depends__`` attribute:

.. code:: python

    #
    # file: migrations/0002.modify-foo.py
    #
    __depends__ = {'0001.create-foo'}

    step(
        "ALTER TABLE foo ADD baz INT",
        "ALTER TABLE foo DROP baz",
    )


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

.. code:: python

    #
    # file: migrations/0001.create-foo.py
    #
    from yoyo import step
    step(
        "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
        "DROP TABLE foo",
        ignore_errors='apply',
    )

Steps can also be python functions taking a database connection as
their only argument:

.. code:: python

    #
    # file: migrations/0002.update-keys.py
    #
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

Post-apply hook
---------------

It can be useful to have a script that is run after every successful migration.
For example you could use this to update database permissions or re-create
views.
To do this, create a special migration file called ``post-apply.py``.
This file should have the same format as any other migration file.


Configuration file
==================

Yoyo looks for a configuration file named ``yoyo.ini`` in the current working
directory or any ancestor directory.

If no configuration file is found ``yoyo`` will prompt you to
create one, popuplated with the current command line args.

Using a configuration file saves repeated typing,
avoids your database username and password showing in process listings
and lessens the risk of accidentally running migrations
against the wrong database (ie by re-running an earlier ``yoyo`` entry in
your command history when you have moved to a different directory).

If you do not want a config file to be loaded
add the ``--no-config`` parameter to the command line options.

The configuration file may contain the following options::

  [DEFAULT]

  # List of migration source directories. "%(here)s" is expanded to the
  # full path of the directory containing this ini file.
  sources = %(here)s/migrations %(here)s/lib/module/migrations

  # Target database
  database = postgresql://scott:tiger@localhost/mydb

  # Verbosity level. Goes from 0 (least verbose) to 3 (most verbose)
  verbosity = 3

  # Disable interactive features
  batch_mode = on

  # Editor to use when starting new migrations
  # "{}" is expanded to the filename of the new migration
  editor = /usr/local/bin/vim -f {}

  # An arbitrary command to run after a migration has been created
  # "{}" is expanded to the filename of the new migration
  post_create_command = hg add {}

  # A prefix to use for generated migration filenames
  prefix = myproject_


Config file inheritance may be used to customize configuration per site::

  #
  # file: yoyo-defaults.ini
  #
  [DEFAULT]
  sources = %(here)s/migrations

  #
  # file: yoyo.ini
  #
  [DEFAULT]

  ; Inherit settings from yoyo-defaults.ini
  %inherit = %(here)s/yoyo-defaults.ini

  ; Use '?' to avoid raising an error if the file does not exist
  %inherit = ?%(here)s/yoyo-defaults.ini

  database = sqlite:///%(here)s/mydb.sqlite

Transactions
============

Each migration runs in a separate transaction. Savepoints are used
to isolate steps within each migration.

If an error occurs during a step and the step has ``ignore_errors`` set,
then that individual step will be rolled back and
execution will pick up from the next step.
If ``ignore_errors`` is not set then the entire migration will be rolled back
and execution stopped.

Note that some databases (eg MySQL) do not support rollback on DDL statements
(eg ``CREATE ...`` and ``ALTER ...`` statements). For these databases
you may need to manually intervene to reset the database state
should errors occur in your migration.

Using ``group`` allows you to nest steps, giving you control of where
rollbacks happen. For example:

.. code:: python

    group([
      step("ALTER TABLE employees ADD tax_code TEXT"),
      step("CREATE INDEX tax_code_idx ON employees (tax_code)")
    ], ignore_errors='all')
    step("UPDATE employees SET tax_code='C' WHERE pay_grade < 4")
    step("UPDATE employees SET tax_code='B' WHERE pay_grade >= 6")
    step("UPDATE employees SET tax_code='A' WHERE pay_grade >= 8")

Disabling transactions
----------------------

You can disable transaction handling within a migration by setting
``__transactional__ = False``, eg:

.. code:: python

    __transactional__ = False

    step("CREATE DATABASE mydb", "DROP DATABASE mydb")

This feature is only tested against the PostgreSQL and SQLite backends. 

PostgreSQL
``````````
In PostgreSQL it is an error to run certain statements inside a transaction
block. These include:

.. code:: sql

    CREATE DATABASE ...
    CREATE TABLE <foo>
    ALTER TYPE <enum> ...

Using ``__transactional__ = False`` allows you to run these within a migration

SQLite
```````
In SQLite, the default transactional behavior may prevent other tools from
accessing the database for the duration of the migration. Using
``__transactional__ = False`` allows you to work around this limitation.


Using yoyo from python code
===========================

The following example shows how to apply migrations from inside python code:

.. code:: python

    from yoyo import read_migrations
    from yoyo import get_backend

    backend = get_backend('postgres://myuser@localhost/mydatabase')
    migrations = read_migrations('path/to/migrations')
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))

.. :vim:sw=4:et

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Changelog
=========

.. include:: ../CHANGELOG.rst
