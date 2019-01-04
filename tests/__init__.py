# Copyright 2015 Oliver Cope
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from itertools import chain
from tempfile import mkdtemp
from textwrap import dedent
from shutil import rmtree
import os.path

from yoyo.config import get_configparser
from yoyo.connections import get_backend

dburi = "sqlite:///:memory:"

config_file = os.path.join(
    os.path.dirname(__file__), *("../../test_databases.ini".split("/"))
)
config = get_configparser()
config.read([config_file])


def get_test_dburis(only=frozenset(), exclude=frozenset()):
    return [
        dburi
        for name, dburi in config.items("DEFAULT")
        if (only and name in only) or (not only and name not in exclude)
    ]


def get_test_backends(only=frozenset(), exclude=frozenset()):
    return [get_backend(dburi) for dburi in get_test_dburis(only, exclude)]


def clear_database(backend):
    for table in backend.list_tables():
        with backend.transaction():
            backend.execute("DROP TABLE {}".format(table))


class MigrationsContextManager(object):
    """
    Decorator/contextmanager taking a list of migrations.
    Creates a temporary directory writes
    each migration to a file (named '0.py', '1.py', '2.py' etc), calls the
    decorated function with the directory name as the first argument, and
    cleans up the temporary directory on exit.
    """

    def __init__(self, *migrations, **kwmigrations):
        self.migrations = migrations
        self.kwmigrations = kwmigrations

    def add_migration(self, id, code):
        filename = os.path.join(self.tmpdir, "{!s}.py".format(id))
        with open(filename, "w") as f:
            f.write(dedent(code).strip())

    def __enter__(self):
        tmpdir = self.tmpdir = mkdtemp()
        for id, code in chain(enumerate(self.migrations), self.kwmigrations.items()):
            self.add_migration(id, code)
        return tmpdir

    def __exit__(self, *exc_info):
        rmtree(self.tmpdir)

    def __call__(self, func):
        def decorator(*args, **kwargs):
            with self:
                return func(*(args + (self.tmpdir,)), **kwargs)

        return decorator


with_migrations = MigrationsContextManager
migrations_dir = MigrationsContextManager
