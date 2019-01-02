"""
Version 2 schema.

Compatible with yoyo-migrations >=  6.0
"""
from yoyo.migrations import get_migration_hash


def upgrade(backend):
    create_log_table(backend)
    create_version_table(backend)
    cursor = backend.execute(
        "SELECT id, ctime FROM {}".format(backend.migration_table_quoted)
    )
    for migration_id, created_at in iter(cursor.fetchone, None):
        migration_hash = get_migration_hash(migration_id)
        log_data = dict(
            backend.get_log_data(),
            operation="apply",
            comment=(
                "this log entry created automatically by an " "internal schema upgrade"
            ),
            created_at_utc=created_at,
            migration_hash=migration_hash,
            migration_id=migration_id,
        )
        backend.execute(
            "INSERT INTO {0.log_table_quoted} "
            "(id, migration_hash, migration_id, operation, created_at_utc, "
            "username, hostname, comment) "
            "VALUES "
            "(:id, :migration_hash, :migration_id, 'apply', :created_at_utc, "
            ":username, :hostname, :comment)".format(backend),
            log_data,
        )

    backend.execute("DROP TABLE {0.migration_table_quoted}".format(backend))
    create_migration_table(backend)
    backend.execute(
        "INSERT INTO {0.migration_table_quoted} "
        "SELECT migration_hash, migration_id, created_at_utc "
        "FROM {0.log_table_quoted}".format(backend)
    )


def create_migration_table(backend):
    backend.execute(
        "CREATE TABLE {0.migration_table_quoted} ( "
        # sha256 hash of the migration id
        "migration_hash VARCHAR(64), "
        # The migration id (ie path basename without extension)
        "migration_id VARCHAR(255), "
        # When this id was applied
        "applied_at_utc TIMESTAMP, "
        "PRIMARY KEY (migration_hash))".format(backend)
    )


def create_log_table(backend):
    backend.execute(
        "CREATE TABLE {0.log_table_quoted} ( "
        "id VARCHAR(36), "
        "migration_hash VARCHAR(64), "
        "migration_id VARCHAR(255), "
        "operation VARCHAR(10), "
        "username VARCHAR(255), "
        "hostname VARCHAR(255), "
        "comment VARCHAR(255), "
        "created_at_utc TIMESTAMP, "
        "PRIMARY KEY (id))".format(backend)
    )


def create_version_table(backend):
    backend.execute(
        "CREATE TABLE {0.version_table_quoted} ("
        "version INT NOT NULL PRIMARY KEY, "
        "installed_at_utc TIMESTAMP)".format(backend)
    )
