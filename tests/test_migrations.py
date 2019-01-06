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

from datetime import datetime
from datetime import timedelta
import pytest
from mock import Mock, patch

from yoyo.connections import get_backend
from yoyo import read_migrations
from yoyo import exceptions
from yoyo import ancestors, descendants

from tests import with_migrations, migrations_dir, dburi
from yoyo.migrations import topological_sort, MigrationList
from yoyo.scripts import newmigration


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT)")
    """,
    """
step("INSERT INTO yoyo_test VALUES (1)")
step("INSERT INTO yoyo_test VALUES ('x', 'y')")
    """,
)
def test_transaction_is_not_committed_on_error(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    with pytest.raises(backend.DatabaseError):
        backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT count(1) FROM yoyo_test")
    assert cursor.fetchone() == (0,)


@with_migrations(
    'step("CREATE TABLE yoyo_test (id INT)")',
    """
step("INSERT INTO yoyo_test VALUES (1)", "DELETE FROM yoyo_test WHERE id=1")
step("UPDATE yoyo_test SET id=2 WHERE id=1", "UPDATE yoyo_test SET id=1 WHERE id=2")
    """,
)
def test_rollbacks_happen_in_reverse(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == [(2,)]
    backend.rollback_migrations(migrations)
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == []


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT)")
    step("INSERT INTO yoyo_test VALUES (1)")
    step("INSERT INTO yoyo_test VALUES ('a', 'b')", ignore_errors='all')
    step("INSERT INTO yoyo_test VALUES (2)")
    """
)
def test_execution_continues_with_ignore_errors(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == [(1,), (2,)]


@with_migrations(
    """
    from yoyo import step, group
    step("CREATE TABLE yoyo_test (id INT)")
    group(
        step("INSERT INTO yoyo_test VALUES (1)"),
        step("INSERT INTO yoyo_test VALUES ('a', 'b')"),
        ignore_errors='all'
    )
    step("INSERT INTO yoyo_test VALUES (2)")
    """
)
def test_execution_continues_with_ignore_errors_in_transaction(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == [(2,)]


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT)")
    step("INSERT INTO yoyo_test VALUES (1)",
         "DELETE FROM yoyo_test WHERE id=2")
    step("UPDATE yoyo_test SET id=2 WHERE id=1",
         "SELECT nonexistent FROM imaginary", ignore_errors='rollback')
    """
)
def test_rollbackignores_errors(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == [(2,)]

    backend.rollback_migrations(migrations)
    cursor.execute("SELECT * FROM yoyo_test")
    assert cursor.fetchall() == []


def test_migration_is_committed(backend):
    with migrations_dir('step("CREATE TABLE yoyo_test (id INT)")') as tmpdir:
        migrations = read_migrations(tmpdir)
        backend.apply_migrations(migrations)

    backend.rollback()
    rows = backend.execute("SELECT * FROM yoyo_test").fetchall()
    assert list(rows) == []


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT)", "DROP TABLE yoyo_test")
    """
)
def test_show_migrations(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)

    backend.apply_migrations(migrations)
    migrations = backend.get_migrations_with_applied_status(migrations)
    assert migrations[0].applied

    backend.rollback_migrations(migrations)
    migrations = backend.get_migrations_with_applied_status(migrations)
    assert not migrations[0].applied


def test_rollback_happens_on_step_failure(backend):
    with migrations_dir(
        """
                        step("",
                             "CREATE TABLE yoyo_is_rolledback (i INT)"),
                        step("CREATE TABLE yoyo_test (s VARCHAR(100))",
                             "DROP TABLE yoyo_test")
                        step("invalid sql!")"""
    ) as tmpdir:
        migrations = read_migrations(tmpdir)
        with pytest.raises(backend.DatabaseError):
            backend.apply_migrations(migrations)

    # The yoyo_test table should have either been deleted (transactional ddl)
    # or dropped (non-transactional-ddl)
    with pytest.raises(backend.DatabaseError):
        backend.execute("SELECT * FROM yoyo_test")

    # Transactional DDL: rollback steps not executed
    if backend.has_transactional_ddl:
        with pytest.raises(backend.DatabaseError):
            backend.execute("SELECT * FROM yoyo_is_rolledback")

    # Non-transactional DDL: ensure the rollback steps were executed
    else:
        cursor = backend.execute("SELECT * FROM yoyo_is_rolledback")
        assert list(cursor.fetchall()) == []


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT)")
    step("DROP TABLE yoyo_test")
    """
)
def test_specify_migration_table(tmpdir):
    backend = get_backend(dburi, migration_table="another_migration_table")
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT migration_id FROM another_migration_table")
    assert cursor.fetchall() == [("0",)]


@with_migrations(
    """
    def foo(conn):
        conn.cursor().execute("CREATE TABLE foo_test (id INT)")
        conn.cursor().execute("INSERT INTO foo_test VALUES (1)")
    def bar(conn):
        foo(conn)
    step(bar)
    """
)
def test_migration_functions_have_namespace_access(tmpdir):
    """
    Test that functions called via step have access to the script namespace
    """
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT id FROM foo_test")
    assert cursor.fetchall() == [(1,)]


@with_migrations(
    """
    from yoyo import group, step
    step("CREATE TABLE yoyo_test (id INT)")
    group(step("INSERT INTO yoyo_test VALUES (1)")),
    """
)
def test_migrations_can_import_step_and_group(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    backend.apply_migrations(migrations)
    cursor = backend.cursor()
    cursor.execute("SELECT id FROM yoyo_test")
    assert cursor.fetchall() == [(1,)]


@with_migrations(
    """
    step("CREATE TABLE yoyo_test (id INT, c VARCHAR(1))")
    step("INSERT INTO yoyo_test VALUES (1, 'a')")
    step("INSERT INTO yoyo_test VALUES (2, 'b')")
    step("SELECT * FROM yoyo_test")
    """
)
def test_migrations_display_selected_data(tmpdir):
    backend = get_backend(dburi)
    migrations = read_migrations(tmpdir)
    with patch("yoyo.migrations.stdout") as stdout:
        backend.apply_migrations(migrations)
        written = "".join(a[0] for a, kw in stdout.write.call_args_list)
        assert written == (
            " id | c \n" "----+---\n" " 1  | a \n" " 2  | b \n" "(2 rows)\n"
        )


class TestTopologicalSort(object):
    def get_mock_migrations(self):
        class MockMigration(Mock):
            def __repr__(self):
                return "<MockMigration {}>".format(self.id)

        return [
            MockMigration(id="m1", depends=set()),
            MockMigration(id="m2", depends=set()),
            MockMigration(id="m3", depends=set()),
            MockMigration(id="m4", depends=set()),
        ]

    def test_it_keeps_stable_order(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        assert list(topological_sort([m1, m2, m3, m4])) == [m1, m2, m3, m4]
        assert list(topological_sort([m4, m3, m2, m1])) == [m4, m3, m2, m1]

    def test_it_sorts_topologically(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        m3.depends.add(m4)
        assert list(topological_sort([m1, m2, m3, m4])) == [m4, m3, m1, m2]

    def test_it_brings_depended_upon_migrations_to_the_front(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        m1.depends.add(m4)
        assert list(topological_sort([m1, m2, m3, m4])) == [m4, m1, m2, m3]

    def test_it_discards_missing_dependencies(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        m3.depends.add(Mock())
        assert list(topological_sort([m1, m2, m3, m4])) == [m1, m2, m3, m4]

    def test_it_catches_cycles(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        m3.depends.add(m3)
        with pytest.raises(exceptions.BadMigration):
            list(topological_sort([m1, m2, m3, m4]))

    def test_it_handles_multiple_edges_to_the_same_node(self):
        m1, m2, m3, m4 = self.get_mock_migrations()
        m2.depends.add(m1)
        m3.depends.add(m1)
        m4.depends.add(m1)
        assert list(topological_sort([m1, m2, m3, m4])) == [m1, m2, m3, m4]


class TestMigrationList(object):
    def test_can_create_empty(self):
        m = MigrationList()
        assert list(m) == []

    def test_cannot_create_with_duplicate_ids(self):
        with pytest.raises(exceptions.MigrationConflict):
            MigrationList([Mock(id=1), Mock(id=1)])

    def test_can_append_new_id(self):
        m = MigrationList([Mock(id=n) for n in range(10)])
        m.append(Mock(id=10))

    def test_cannot_append_duplicate_id(self):
        m = MigrationList([Mock(id=n) for n in range(10)])
        with pytest.raises(exceptions.MigrationConflict):
            m.append(Mock(id=1))

    def test_deletion_allows_reinsertion(self):
        m = MigrationList([Mock(id=n) for n in range(10)])
        del m[0]
        m.append(Mock(id=0))

    def test_can_overwrite_slice_with_same_ids(self):
        m = MigrationList([Mock(id=n) for n in range(10)])
        m[1:3] = [Mock(id=2), Mock(id=1)]

    def test_cannot_overwrite_slice_with_conflicting_ids(self):
        m = MigrationList([Mock(id=n) for n in range(10)])
        with pytest.raises(exceptions.MigrationConflict):
            m[1:3] = [Mock(id=4)]


class TestAncestorsDescendants(object):
    def setup(self):
        self.m1 = Mock(id="m1", depends=["m2", "m3"])
        self.m2 = Mock(id="m2", depends=["m3"])
        self.m3 = Mock(id="m3", depends=["m5"])
        self.m4 = Mock(id="m4", depends=["m5"])
        self.m5 = Mock(id="m5", depends=[])
        self.m1.depends = {self.m2, self.m3}
        self.m2.depends = {self.m3}
        self.m3.depends = {self.m5}
        self.m4.depends = {self.m5}
        self.migrations = {self.m1, self.m2, self.m3, self.m4, self.m5}

    def test_ancestors(self):

        assert ancestors(self.m1, self.migrations) == {self.m2, self.m3, self.m5}
        assert ancestors(self.m2, self.migrations) == {self.m3, self.m5}
        assert ancestors(self.m3, self.migrations) == {self.m5}
        assert ancestors(self.m4, self.migrations) == {self.m5}
        assert ancestors(self.m5, self.migrations) == set()

    def test_descendants(self):

        assert descendants(self.m1, self.migrations) == set()
        assert descendants(self.m2, self.migrations) == {self.m1}
        assert descendants(self.m3, self.migrations) == {self.m2, self.m1}
        assert descendants(self.m4, self.migrations) == set()
        assert descendants(self.m5, self.migrations) == {
            self.m4,
            self.m3,
            self.m2,
            self.m1,
        }


class TestReadMigrations(object):
    @with_migrations(**{newmigration.tempfile_prefix + "test": ""})
    def test_it_ignores_yoyo_new_tmp_files(self, tmpdir):
        """
        The yoyo new command creates temporary files in the migrations directory.
        These shouldn't be picked up by yoyo apply etc
        """
        assert len(read_migrations(tmpdir)) == 0

    @with_migrations(**{"post-apply": """step('SELECT 1')"""})
    def test_it_loads_post_apply_scripts(self, tmpdir):
        migrations = read_migrations(tmpdir)
        assert len(migrations) == 0
        assert len(migrations.post_apply) == 1

    @with_migrations(**{"a": """step('SELECT 1')"""})
    def test_it_does_not_add_duplicate_steps(self, tmpdir):
        m = read_migrations(tmpdir)[0]
        m.load()
        assert len(m.steps) == 1

        m = read_migrations(tmpdir)[0]
        m.load()
        assert len(m.steps) == 1

    @with_migrations(**{"a": """from yoyo import step; step('SELECT 1')"""})
    def test_it_does_not_add_duplicate_steps_with_imported_symbols(self, tmpdir):
        m = read_migrations(tmpdir)[0]
        m.load()
        assert len(m.steps) == 1

        m = read_migrations(tmpdir)[0]
        m.load()
        assert len(m.steps) == 1


class TestPostApplyHooks(object):
    def test_post_apply_hooks_are_run_every_time(self):

        backend = get_backend(dburi)
        migrations = migrations_dir(
            **{
                "a": "step('create table postapply (i int)')",
                "post-apply": "step('insert into postapply values (1)')",
            }
        )

        with migrations as tmp:

            def count_postapply_calls():
                cursor = backend.cursor()
                cursor.execute("SELECT count(1) FROM postapply")
                return cursor.fetchone()[0]

            def _apply_migrations():
                backend.apply_migrations(backend.to_apply(read_migrations(tmp)))

            # Should apply migration 'a' and call the post-apply hook
            _apply_migrations()
            assert count_postapply_calls() == 1

            # No outstanding migrations: post-apply hook should not be called
            _apply_migrations()
            assert count_postapply_calls() == 1

            # New migration added: post-apply should be called a second time
            migrations.add_migration("b", "")
            _apply_migrations()
            assert count_postapply_calls() == 2

    @with_migrations(
        **{
            "a": "step('create table postapply (i int)')",
            "post-apply": "step('insert into postapply values (1)')",
            "post-apply2": "step('insert into postapply values (2)')",
        }
    )
    def test_it_runs_multiple_post_apply_hooks(self, tmpdir):
        backend = get_backend(dburi)
        backend.apply_migrations(backend.to_apply(read_migrations(tmpdir)))
        cursor = backend.cursor()
        cursor.execute("SELECT * FROM postapply")
        assert cursor.fetchall() == [(1,), (2,)]

    @with_migrations(
        **{
            "a": "step('create table postapply (i int)')",
            "post-apply": "step('insert into postapply values (1)')",
        }
    )
    def test_apply_migrations_only_does_not_run_hooks(self, tmpdir):
        backend = get_backend(dburi)
        backend.apply_migrations_only(backend.to_apply(read_migrations(tmpdir)))
        cursor = backend.cursor()
        cursor.execute("SELECT * FROM postapply")
        assert cursor.fetchall() == []


class TestLogging(object):
    def get_last_log_entry(self, backend):
        cursor = backend.execute(
            "SELECT migration_id, operation, "
            "created_at_utc, username, hostname "
            "from _yoyo_log "
            "ORDER BY id DESC LIMIT 1"
        )
        return {d[0]: value for d, value in zip(cursor.description, cursor.fetchone())}

    def get_log_count(self, backend):
        return backend.execute("SELECT count(1) FROM _yoyo_log").fetchone()[0]

    def test_it_logs_apply_and_rollback(self, backend):
        with with_migrations(a='step("CREATE TABLE yoyo_test (id INT)")') as tmpdir:
            migrations = read_migrations(tmpdir)
            backend.apply_migrations(migrations)
            assert self.get_log_count(backend) == 1
            logged = self.get_last_log_entry(backend)
            assert logged["migration_id"] == "a"
            assert logged["operation"] == "apply"
            assert logged["created_at_utc"] >= datetime.utcnow() - timedelta(seconds=2)
            apply_time = logged["created_at_utc"]

            backend.rollback_migrations(migrations)
            assert self.get_log_count(backend) == 2
            logged = self.get_last_log_entry(backend)
            assert logged["migration_id"] == "a"
            assert logged["operation"] == "rollback"
            assert logged["created_at_utc"] >= apply_time

    def test_it_logs_mark_and_unmark(self, backend):
        with with_migrations(a='step("CREATE TABLE yoyo_test (id INT)")') as tmpdir:
            migrations = read_migrations(tmpdir)
            backend.mark_migrations(migrations)
            assert self.get_log_count(backend) == 1
            logged = self.get_last_log_entry(backend)
            assert logged["migration_id"] == "a"
            assert logged["operation"] == "mark"
            assert logged["created_at_utc"] >= datetime.utcnow() - timedelta(seconds=2)
            marked_time = logged["created_at_utc"]

            backend.unmark_migrations(migrations)
            assert self.get_log_count(backend) == 2
            logged = self.get_last_log_entry(backend)
            assert logged["migration_id"] == "a"
            assert logged["operation"] == "unmark"
            assert logged["created_at_utc"] >= marked_time
