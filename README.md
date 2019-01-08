Yoyo database migrations
========================

[![Build Status](https://travis-ci.org/marcosschroh/yoyo-database-migrations.svg?branch=master)](https://travis-ci.org/marcosschroh/yoyo-database-migrations)
![License](https://img.shields.io/github/license/marcosschroh/yoyo-database-migrations.svg)
[![codecov](https://codecov.io/gh/marcosschroh/yoyo-database-migrations/branch/master/graph/badge.svg)](https://codecov.io/gh/marcosschroh/yoyo-database-migrations)

This project has been clone from [ollyc/yoyo](https://bitbucket.org/ollyc/yoyo). Thanks Ollyc!!


Why this repository?

* To improve project documentation
* To fix bugs related to different python versions
* I had different issues on Mac but not on Linux, so fix them
* To add full support for Python 3.6/3.7 (annotations, async/io databases drivers)
* To add new Features
* To add full code coverage

Yoyo is a database schema migration tool. You write database migrations
as Python scripts containing raw SQL statements or Python functions.

Installation:
------------
```
pip install yoyo-database-migrations
```


Documentation:
--------------
https://marcosschroh.github.io/yoyo-database-migrations/



What does yoyo-migrations do?
-----------------------------

As your database application evolves, changes to the database schema may be
required. Yoyo lets you write migration scripts in Python containing
SQL statements to migrate your database schema to a new version.

A simple migration script looks like this:

```python
# file: migrations/0001.create-foo.py
from yoyo import step
step(
    "CREATE TABLE foo (id INT, bar VARCHAR(20), PRIMARY KEY (id))",
    "DROP TABLE foo",
)
```

Yoyo manages these database migration scripts,
gives you command line tools to apply and rollback migrations,
and manages dependencies between migrations.

Database support
----------------

PostgreSQL, MySQL and SQLite databases are supported.
ODBC and Oracle database backends are available (but unsupported).
 

Improvements
------------

* Command `yoyo showmigrations` added
