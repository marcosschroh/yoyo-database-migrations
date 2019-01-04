from datetime import datetime
import getpass
import socket

from yoyo import internalmigrations
from tests import clear_database


def assert_table_is_created(backend, table):
    assert table in backend.list_tables()


def assert_table_is_missing(backend, table):
    assert table not in backend.list_tables()


def test_it_installs_migrations_table(backend):
    clear_database(backend)
    internalmigrations.upgrade(backend)


def test_it_installs_v1(backend):
    clear_database(backend)
    internalmigrations.upgrade(backend, version=1)
    assert internalmigrations.get_current_version(backend) == 1
    assert_table_is_created(backend, "_yoyo_migration")
    assert_table_is_missing(backend, "_yoyo_version")
    assert_table_is_missing(backend, "_yoyo_log")


def test_it_installs_v2(backend):
    clear_database(backend)
    internalmigrations.upgrade(backend, version=2)
    assert internalmigrations.get_current_version(backend) == 2
    assert_table_is_created(backend, "_yoyo_migration")
    assert_table_is_created(backend, "_yoyo_version")
    assert_table_is_created(backend, "_yoyo_log")


def test_v3_preserves_history_when_upgrading(backend):
    clear_database(backend)
    internalmigrations.upgrade(backend, version=1)
    v2insert = (
        "INSERT INTO {0.migration_table_quoted} (id, ctime) "
        "VALUES (:id, :when)".format(backend)
    )

    with backend.transaction():
        backend.execute(
            v2insert, {"id": "migration-a", "when": datetime(2000, 1, 1, 12)}
        )
        backend.execute(
            v2insert, {"id": "migration-b", "when": datetime(2000, 2, 1, 12)}
        )

    internalmigrations.upgrade(backend, version=2)

    cursor = backend.execute(
        "SELECT migration_hash, migration_id, applied_at_utc "
        "FROM {0.migration_table_quoted} order by applied_at_utc".format(backend)
    )
    applied = list(cursor.fetchall())
    assert applied == [
        (
            "da335f4748bac940534a07dcd997122ff9fc7c7ebe90b78f5c11aeda2a2d0104",
            "migration-a",
            datetime(2000, 1, 1, 12),
        ),
        (
            "82f4683f1cc4f376e7c5a996392927d9a5ed6d102681cd8609b65b621e72ed78",
            "migration-b",
            datetime(2000, 2, 1, 12),
        ),
    ]

    cursor = backend.execute(
        "SELECT migration_hash, migration_id, "
        "operation, created_at_utc, username, hostname, comment "
        "FROM {0.log_table_quoted} order by created_at_utc".format(backend)
    )
    log = list(cursor.fetchall())
    current_user = getpass.getuser()
    current_host = socket.getfqdn()
    assert log == [
        (
            "da335f4748bac940534a07dcd997122ff9fc7c7ebe90b78f5c11aeda2a2d0104",
            "migration-a",
            "apply",
            datetime(2000, 1, 1, 12),
            current_user,
            current_host,
            "this log entry created automatically by an internal schema upgrade",
        ),
        (
            "82f4683f1cc4f376e7c5a996392927d9a5ed6d102681cd8609b65b621e72ed78",
            "migration-b",
            "apply",
            datetime(2000, 2, 1, 12),
            current_user,
            current_host,
            "this log entry created automatically by an internal schema upgrade",
        ),
    ]
