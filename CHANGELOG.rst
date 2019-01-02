6.0.0 (released 2018-08-21)
---------------------------

**This version introduces backwards incompatible changes**. Please read this
file carefully before upgrading.

* Bugfix: now works on MySQL+utf8mb4 databases. This requires a new 
  internal schema for recording applied migrations, and your database will be
  automatically updated when you first run this version. After upgrading, your
  database will no longer be compatible with older versions of yoyo migrations.
  (thanks to James Socol and others for the report and discussion of the
  implementation)

* Bugfix: The `yoyo break-lock` command is no longer broken

* All migration operations (``apply``, ``rollback``, ``mark``, ``unmark``) are
  now logged in a table ``_yoyo_log`` (thanks to Matt Williams for the
  suggestion).

* The CLI script now displays the list of selected migrations before
  asking for final confirmation when in interactive mode.

* Added support for ``__transactional__`` flag in sqlite migrations


5.1.7 (released 2018-07-30)
---------------------------

* Bugfix: fix uppercase letters being excluded from generated filenames 
  (thanks to Romain Godefroy)

5.1.6 (released 2018-06-28)
---------------------------

* Bugfix: fix problems running on Python 3 on Windows

5.1.5 (released 2018-06-13)
---------------------------

* Bugfix: adding a ``schema`` parameter to PostgreSQL connection strings
  no longer raises an exception (thanks to Mohamed Habib for the report)

5.1.0 (released 2018-07-11)
---------------------------

* ``yoyo rollback`` now only rolls back a single migration in batch mode (
  unless a --revision or --all is specified) (thanks to
  `A A <https://bitbucket.org/linuxnotes/>`_ for the idea and initial
  implementation)
* Added support for Oracle via cx_Oracle backend (thanks to Donald Sarratt)
* Added support for locking migration tables during operations to prevent
  conflicts if multiple yoyo processes run at the same time (thanks to Artimi
  NA for proposal and initial implementation)
* Removed dependency on python-slugify to avoid pulling in GPL'd code
  (thanks to Olivier Chédru)
* Added support for a ``schema`` parameter for PostgreSQL databases (thanks to
  Tobiáš Štancel)
* Added support for arbitrary keyword parameters in PostgreSQL URLs, allowing
  eg ``sslmode=require`` to be specified.
* Bugfix: relative paths are correctly resolved in the config file.
* Bugfix: fixed the ordering when applying migrations with the reapply command
  (thanks to Goohu)


5.0.5 (released 2017-01-12)
---------------------------

* Added support for a ``__transactional__ = False`` flag in migration files,
  allowing migrations to run commands in PostgreSQL that raise errors
  if run inside a transaction block (eg "CREATE DATABASE")

* Bugfix: fix the unix_socket option for mysql connections

5.0.4 (released 2016-09-04)
---------------------------

* Bugfix: fixed crash when mutliple migrations have the same dependency
  (thanks to smotko for the report)

5.0.3 (released 2016-07-03)
---------------------------

* Bugfix: fixed exception when creating a new migration interactively
  with `yoyo new`

5.0.2 (released 2016-06-21)
---------------------------

* Added ``DatabaseBackend.apply_migrations_only`` and ``run_post_hooks``
  methods. This allows python code that interfaces with yoyo to run migrations
  and post_hooks separately if required (thanks to Robi Wan for reporting this
  and discussing possible fixes)
* Bugfix: fix duplicate key error when using post-apply hooks (thanks to Robi
  Wan for the report)
* Bugfix: migration steps are no longer loaded multiple times if
  read_migrations is called more than once (thanks to Kyle McChesney for the
  report)
* Bugfix: make sure that the migration_table option is read from the config
  file (thanks to Frederik Holljen for the report and Manolo Micozzi for the
  fix)

5.0.1 (released 2015-11-13)
---------------------------

* Bugfix: migration files are now sequentially named when using the prefix
  option (thanks to Igor Tsarev)

5.0.0 (released 2015-11-13)
---------------------------

**This version introduces backwards incompatible changes**. Please read this
file carefully before upgrading.

* The configuration file is now stored per-project, not per-migrations source
  directory. This makes it possible to share a migrations source directory
  across multiple projects.
* The api for calling yoyo programmatically has changed. Refer to the
  README for an up to date example of calling yoyo from python code.
* Improved url parsing
* Allow database uris containing usernames with the symbol '@'
* The command line option ``--no-cache`` has been renamed to
  ``--no-config-file``. The old name is retained as an alias for backwards
  compatibility
* The database must now be supplied using the ``--database/-d`` command line
  flag. This makes it possible to change the database when calling yoyo without
  needing to respecify the migration directories.
* Added a --revision command line option. In the case of apply, this causes
  the specified migration to be applied, plus any dependencies. In the case
  of rollback, this removes the specified revision and any other migrations
  that depend upon it.
* Added 'mark' and 'unmark' commands to allow migrations to be marked in the
  database without actually running them
* Transaction handling has changed. Each migration now always runs in a
  single transaction, with individual steps running in nested transactions
  (using savepoints).
  The ``transaction()`` function is still available
  for backwards compatibility,
  but now creates a savepoint rather than a full transaction.
* The default MySQL driver has been changed to PyMySQL, for Python 3
  compatbility reasons. MySQLdb can be used by specifying the
  'mysql+mysqldb://' scheme.
* Errors encountered while creating the _yoyo_migrations table are now raised
  rather than being silently ignored (thanks to James Socol).

Version 4.2.5
-------------

* Fix for pyscopg2 driver versions >=2.6
* Faster loading of migration scripts
* Dependencies between migrations can be added via the
  ``__depends__`` attribute
* Dropped support for python 2.6

Version 4.2.4
-------------

* Fix for mismanaged 4.2.3 release

Version 4.2.3
-------------

* Migrations are now datestamped with a UTC date (thanks to robi wan)

* Fixes for installation and use under python 3

Version 4.2.2
-------------

* Migration scripts can start with ``from yoyo import step, transaction``.
  This prevents linters (eg flake8) throwing errors over undefined names.

* Bugfix: functions declared in a migration file can access the script's global
  namespace

Version 4.2.1
-------------

* Bugfix for previous release, which omitted critical files

Version 4.2.0
-------------

* Removed yoyo.migrate namespace package. Any code that uses the yoyo api
  directly needs have any imports modified, eg this::

    from yoyo.migrate import read_migrations
    from yoyo.migrate.connections import connect

  Should be changed to this::

    from yoyo import read_migrations
    from yoyo.connections import connect

* Migrated from darcs to mercurial. Code is now hosted at
  https://bitbucket.org/ollyc/yoyo

* Bugfix: the migration_table option was not being passed to read_migrations,
  causing the value to be ignored

Version 4.1.6
-------------

* Added windows support (thanks to Peter Shinners)

Version 4.1.5
-------------

* Configure logging handlers so that the -v switch causes output to go to the
  console (thanks to Andrew Nelis).

* ``-v`` command line switch no longer takes an argument but may be specified
  multiple times instead (ie use ``-vvv`` instead of ``-v3``). ``--verbosity``
  retains the old behaviour.

Version 4.1.4
-------------

* Bugfix for post apply hooks

Version 4.1.3
-------------

* Changed default migration table name back to '_yoyo_migration'

Version 4.1.2
-------------

* Bugfix for error when running in interactive mode

Version 4.1.1
-------------

* Introduced configuration option for migration table name

Version 4.1.0
-------------

* Introduced ability to run steps within a transaction (thanks to Ryan Williams
  for suggesting this functionality along with assorted bug fixes.)

* "post-apply" migrations can be run after every successful upward migration

* Other minor bugfixes and improvements

* Switched to <major>.<minor> version numbering convention

Version 4
-------------

* Fixed problem installing due to missing manifest entry

Version 3
-------------

* Use the console_scripts entry_point in preference to scripts=[] in
  setup.py, this provides better interoperability with buildout

Version 2
-------------

* Fixed error when reading dburi from config file

Version 1
-------------

* Initial release

