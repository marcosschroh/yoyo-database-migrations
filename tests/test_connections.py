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

import sys

from mock import patch, call, MagicMock
import pytest

from yoyo.connections import parse_uri, BadConnectionURI


class MockDatabaseError(Exception):
    pass


class TestParseURI:
    @pytest.mark.skipif(
        sys.version_info < (2, 7, 4),
        reason="Requires python>=2.7.4 " "(http://bugs.python.org/issue7904)",
    )
    def test_it_parses_all_fields(self):
        parsed = parse_uri("protocol://scott:tiger@server:666/db?k=1")
        assert tuple(parsed) == (
            "protocol",
            "scott",
            "tiger",
            "server",
            666,
            "db",
            {"k": "1"},
        )

    def test_it_parses_escaped_username(self):
        parsed = parse_uri("protocol://scott%40example.org:tiger@localhost/db")
        assert parsed.username == "scott@example.org"

    def test_it_requires_scheme(self):
        with pytest.raises(BadConnectionURI):
            parse_uri("//scott:tiger@localhost/db")

    def test_it_roundtrips(self):
        cases = [
            "proto://scott%40example.org:tiger@localhost/db",
            "proto://localhost/db?a=1+2",
            "proto://localhost/db?a=a%3D1",
        ]
        for case in cases:
            parsed = parse_uri(case)
            assert parsed.uri == case

    def test_it_returns_relative_paths_for_sqlite(self):
        assert parse_uri("sqlite:///foo/bar.db").database == "foo/bar.db"

    def test_it_returns_absolute_paths_for_sqlite(self):
        assert parse_uri("sqlite:////foo/bar.db").database == "/foo/bar.db"


@pytest.mark.skipif(
    sys.version_info < (2, 7, 4),
    reason="Requires python>=2.7.4 " "(http://bugs.python.org/issue7904)",
)
@patch(
    "yoyo.backends.get_dbapi_module",
    return_value=MagicMock(DatabaseError=MockDatabaseError, paramstyle="qmark"),
)
def test_connections(get_dbapi_module):

    from yoyo import backends

    u = parse_uri("odbc://scott:tiger@db.example.org:42/northwind?foo=bar")
    cases = [
        (
            backends.ODBCBackend,
            "pyodbc",
            call(
                "UID=scott;PWD=tiger;ServerName=db.example.org;"
                "Port=42;Database=northwind;foo=bar"
            ),
        ),
        (
            backends.MySQLBackend,
            "pymysql",
            call(
                user="scott",
                passwd="tiger",
                host="db.example.org",
                port=42,
                db="northwind",
                foo="bar",
            ),
        ),
        (
            backends.SQLiteBackend,
            "sqlite3",
            call("northwind", detect_types=get_dbapi_module("sqlite3").PARSE_DECLTYPES),
        ),
        (
            backends.PostgresqlBackend,
            "psycopg2",
            call(
                user="scott",
                password="tiger",
                port=42,
                host="db.example.org",
                dbname="northwind",
                foo="bar",
            ),
        ),
    ]
    for cls, driver_module, connect_args in cases:
        cls(u, "_yoyo_migration")
        assert get_dbapi_module.call_args == call(driver_module)
        assert get_dbapi_module().connect.call_args == connect_args
