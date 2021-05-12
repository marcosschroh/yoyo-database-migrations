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

from __future__ import absolute_import

from collections import namedtuple

from .migrations import default_migration_table
from .backends import (
    PostgresqlBackend,
    SQLiteBackend,
    ODBCBackend,
    OracleBackend,
    MySQLBackend,
    MySQLdbBackend,
    ExasolBackend,
)
from .compat import urlsplit, urlunsplit, parse_qsl, urlencode, quote, unquote

BACKENDS = {
    "odbc": ODBCBackend,
    "oracle": OracleBackend,
    "postgresql": PostgresqlBackend,
    "postgres": PostgresqlBackend,
    "psql": PostgresqlBackend,
    "mysql": MySQLBackend,
    "mysql+mysqldb": MySQLdbBackend,
    "sqlite": SQLiteBackend,
    "exasol": ExasolBackend,
    "exasoldb": ExasolBackend,
}


_DatabaseURI = namedtuple(
    "_DatabaseURI", "scheme username password hostname port database " "args"
)


class DatabaseURI(_DatabaseURI):
    @property
    def netloc(self):
        hostname = self.hostname or ""
        if self.port:
            hostpart = "{}:{}".format(hostname, self.port)
        else:
            hostpart = hostname

        if self.username:
            return "{}:{}@{}".format(
                quote(self.username), quote(self.password or ""), hostpart
            )
        else:
            return hostpart

    def __str__(self):
        return urlunsplit(
            (self.scheme, self.netloc, self.database, urlencode(self.args), "")
        )

    @property
    def uri(self):
        return str(self)


class BadConnectionURI(Exception):
    """
    An invalid connection URI
    """


def get_backend(uri, migration_table=default_migration_table):
    """
    Connect to the given DB uri in the format
    ``driver://user:pass@host:port/database_name?param=value``,
    returning a :class:`DatabaseBackend` object
    """
    parsed = parse_uri(uri)
    try:
        backend_class = BACKENDS[parsed.scheme.lower()]
    except KeyError:
        raise BadConnectionURI(
            "Unrecognised database connection scheme %r" % parsed.scheme
        )
    return backend_class(parsed, migration_table)


def parse_uri(s):
    """
    Examples::

        >>> parse_uri('postgres://fred:bassett@server:5432/fredsdatabase')
        ('postgres', 'fred', 'bassett', 'server', 5432, 'fredsdatabase', None)
        >>> parse_uri('mysql:///jimsdatabase')
        ('mysql', None, None, None, None, 'jimsdatabase', None, None)
        >>> parse_uri('odbc://user:password@server/database?DSN=dsn')
        ('odbc', 'user', 'password', 'server', None, 'database', {'DSN':'dsn'})
    """
    result = urlsplit(s)

    if not result.scheme:
        raise BadConnectionURI("No scheme specified in connection URI %r" % s)

    return DatabaseURI(
        scheme=result.scheme,
        username=(unquote(result.username) if result.username is not None else None),
        password=(unquote(result.password) if result.password is not None else None),
        hostname=result.hostname,
        port=result.port,
        database=result.path[1:] if result.path else None,
        args=dict(parse_qsl(result.query)),
    )
