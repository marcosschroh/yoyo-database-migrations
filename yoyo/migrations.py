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

from collections import (
    defaultdict,
    OrderedDict,
    Counter,
    MutableSequence,
    Iterable,
    deque,
)
from copy import copy
from itertools import chain, count
from logging import getLogger
import hashlib
import os
import sys
import inspect

from yoyo.compat import reraise, exec_, ustr, stdout
from yoyo import exceptions
from yoyo.utils import plural

logger = getLogger("yoyo.migrations")
default_migration_table = "_yoyo_migration"

hash_function = hashlib.sha256


def get_migration_hash(migration_id):
    """
    Return a unique hash given a migration_id, that can be used as a database
    key.

    :param migration_id: a migration id (ie filename without extension), or
                         ``None`` if this is a new migration
    """
    if migration_id is None:
        return None
    return hash_function(migration_id.encode("utf-8")).hexdigest()


class Migration(object):

    __all_migrations = {}

    def __init__(self, id, path):
        self.id = id
        self.hash = get_migration_hash(id)
        self.path = path
        self.steps = None
        self.source = None
        self.use_transactions = True
        self._depends = None
        self.__all_migrations[id] = self
        self.applied = None

    def __repr__(self):
        return "<{} {!r} from {}>".format(self.__class__.__name__, self.id, self.path)

    @property
    def loaded(self):
        return self.steps is not None

    @property
    def depends(self):
        self.load()
        return self._depends

    def load(self):
        if self.loaded:
            return
        with open(self.path, "r") as f:
            self.source = source = f.read()
            migration_code = compile(source, f.name, "exec")

        collector = StepCollector(migration=self)
        ns = {
            "step": collector.add_step,
            "group": collector.add_step_group,
            "transaction": collector.add_step_group,
            "collector": collector,
        }
        try:
            exec_(migration_code, ns)
        except Exception as e:
            logger.exception("Could not import migration from %r: %r", self.path, e)
            raise exceptions.BadMigration(self.path, e)
        depends = ns.get("__depends__", [])
        if isinstance(depends, (ustr, bytes)):
            depends = [depends]
        self._depends = {self.__all_migrations.get(id, None) for id in depends}
        self.use_transactions = ns.get("__transactional__", True)
        if None in self._depends:
            raise exceptions.BadMigration(
                "Could not resolve dependencies in {}".format(self.path)
            )
        self.ns = ns
        self.source = source
        self.steps = collector.create_steps(self.use_transactions)

    def process_steps(self, backend, direction, force=False):

        self.load()
        reverse = {"rollback": "apply", "apply": "rollback"}[direction]

        steps = self.steps
        if direction == "rollback":
            steps = reversed(steps)

        executed_steps = []
        if self.use_transactions:
            transaction = backend.transaction
        else:
            transaction = backend.disable_transactions

        with transaction():
            for step in steps:
                try:
                    getattr(step, direction)(backend, force)
                    executed_steps.append(step)
                except backend.DatabaseError:
                    exc_info = sys.exc_info()

                    if not backend.has_transactional_ddl or not self.use_transactions:
                        # Any DDL statements that have been executed have been
                        # committed. Go through the rollback steps to undo
                        # these inasmuch is possible.
                        try:
                            for step in reversed(executed_steps):
                                getattr(step, reverse)(backend)
                        except backend.DatabaseError:
                            logger.exception("Could not %s step %s", direction, step.id)
                    reraise(exc_info[0], exc_info[1], exc_info[2])


class PostApplyHookMigration(Migration):
    """
    A special migration that is run after successfully applying a set of
    migrations. Unlike a normal migration this will be run every time
    migrations are applied script is called.
    """


class StepBase(object):

    id = None

    def __repr__(self):
        return "<{} #{}>".format(self.__class__.__name__, self.id)

    def apply(self, backend, force=False):
        raise NotImplementedError()

    def rollback(self, backend, force=False):
        raise NotImplementedError()


class TransactionWrapper(StepBase):
    """
    A :class:~`yoyo.migrations.TransactionWrapper` object causes a step to be
    run within a single database transaction. Nested transactions are
    implemented via savepoints.
    """

    def __init__(self, step, ignore_errors=None):
        assert ignore_errors in (None, "all", "apply", "rollback")
        self.step = step
        self.ignore_errors = ignore_errors

    def __repr__(self):
        return "<TransactionWrapper {!r}>".format(self.step)

    def apply(self, backend, force=False, direction="apply"):
        with backend.transaction() as transaction:
            try:
                getattr(self.step, direction)(backend, force)
            except backend.DatabaseError:
                if force or self.ignore_errors in (direction, "all"):
                    logger.exception("Ignored error in %r", self.step)
                    transaction.rollback()
                    return
                else:
                    raise

    def rollback(self, backend, force=False):
        self.apply(backend, force, "rollback")


class Transactionless(StepBase):
    """
    A :class:~`yoyo.migrations.TransactionWrapper` object causes a step to be
    run outside of a database transaction.
    """

    def __init__(self, step, ignore_errors=None):
        assert ignore_errors in (None, "all", "apply", "rollback")
        self.step = step
        self.ignore_errors = ignore_errors

    def __repr__(self):
        return "<TransactionWrapper {!r}>".format(self.step)

    def apply(self, backend, force=False, direction="apply"):
        try:
            getattr(self.step, direction)(backend, force)
        except backend.DatabaseError:
            if force or self.ignore_errors in (direction, "all"):
                logger.exception("Ignored error in %r", self.step)
                return
            else:
                raise

    def rollback(self, backend, force=False):
        self.apply(backend, force, "rollback")


class MigrationStep(StepBase):
    """
    Model a single migration.

    Each migration step comprises apply and rollback steps of up and down SQL
    statements.
    """

    def __init__(self, id, apply, rollback):

        self.id = id
        self._rollback = rollback
        self._apply = apply

    def _execute(self, cursor, stmt, out=None):
        """
        Execute the given statement. If rows are returned, output these in a
        tabulated format.
        """
        if out is None:
            out = stdout
        if isinstance(stmt, ustr):
            logger.debug(" - executing %r", stmt.encode("ascii", "replace"))
        else:
            logger.debug(" - executing %r", stmt)
        cursor.execute(stmt)
        if cursor.description:
            result = [[ustr(value) for value in row] for row in cursor.fetchall()]
            column_names = [desc[0] for desc in cursor.description]
            column_sizes = [len(c) for c in column_names]

            for row in result:
                for ix, value in enumerate(row):
                    if len(value) > column_sizes[ix]:
                        column_sizes[ix] = len(value)
            format = "|".join(" %%- %ds " % size for size in column_sizes)
            format += "\n"
            out.write(format % tuple(column_names))
            out.write("+".join("-" * (size + 2) for size in column_sizes) + "\n")
            for row in result:
                out.write(format % tuple(row))
            out.write(plural(len(result), "(%d row)", "(%d rows)") + "\n")

    def apply(self, backend, force=False):
        """
        Apply the step.

        :param force: If true, errors will be logged but not be re-raised
        """
        logger.info(" - applying step %d", self.id)
        if not self._apply:
            return
        if isinstance(self._apply, (ustr, str)):
            cursor = backend.cursor()
            try:
                self._execute(cursor, self._apply)
            finally:
                cursor.close()
        else:
            self._apply(backend.connection)

    def rollback(self, backend, force=False):
        """
        Rollback the step.
        """
        logger.info(" - rolling back step %d", self.id)
        if self._rollback is None:
            return
        if isinstance(self._rollback, (ustr, str)):
            cursor = backend.cursor()
            try:
                self._execute(cursor, self._rollback)
            finally:
                cursor.close()
        else:
            self._rollback(backend.connection)


class StepGroup(MigrationStep):
    """
    Multiple steps aggregated together
    """

    def __init__(self, steps):
        self.steps = steps

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.steps)

    def apply(self, backend, force=False):
        for item in self.steps:
            item.apply(backend, force)

    def rollback(self, backend, force=False):
        for item in self.steps:
            item.apply(backend, force)


def read_migrations(*directories):
    """
    Return a ``MigrationList`` containing all migrations from ``directory``.
    """
    from yoyo.scripts import newmigration

    migrations = MigrationList()
    for directory in directories:
        paths = [
            os.path.join(directory, path)
            for path in os.listdir(directory)
            if path.endswith(".py")
            and not path.startswith(newmigration.tempfile_prefix)
        ]

        for path in sorted(paths):

            filename = os.path.splitext(os.path.basename(path))[0]

            if filename.startswith("post-apply"):
                migration_class = PostApplyHookMigration
            else:
                migration_class = Migration

            migration = migration_class(
                os.path.splitext(os.path.basename(path))[0], path
            )
            if migration_class is PostApplyHookMigration:
                migrations.post_apply.append(migration)
            else:
                migrations.append(migration)
    return migrations


class MigrationList(MutableSequence):
    """
    A list of database migrations.
    """

    def __init__(self, items=None, post_apply=None):
        self.items = list(items) if items else []
        self.post_apply = post_apply if post_apply else []
        self.keys = set(item.id for item in self.items)
        self.check_conflicts()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.items))

    def check_conflicts(self):
        c = Counter()
        for item in self:
            c[item.id] += 1
            if c[item.id] > 1:
                raise exceptions.MigrationConflict(item.id)

    def __getitem__(self, n):
        if isinstance(n, slice):
            return self.__class__(self.items.__getitem__(n))
        return self.items.__getitem__(n)

    def __setitem__(self, n, ob):
        removing = self.items[n]
        if not isinstance(removing, list):
            remove_ids = set([item.id for item in removing])
            new_ids = [ob.id]
        else:
            remove_ids = set(item.id for item in removing)
            new_ids = {item.id for item in ob}

        for id in new_ids:
            if id in self.keys and id not in remove_ids:
                raise exceptions.MigrationConflict(id)

        self.keys.difference_update(removing)
        self.keys.update(new_ids)
        return self.items.__setitem__(n, ob)

    def __len__(self):
        return len(self.items)

    def __delitem__(self, i):
        self.keys.remove(self.items[i].id)
        self.items.__delitem__(i)

    def insert(self, i, x):
        if x.id in self.keys:
            raise exceptions.MigrationConflict(x.id)
        self.keys.add(x.id)
        return self.items.insert(i, x)

    def __add__(self, other):
        ob = copy(self)
        ob.extend(other)
        return ob

    def filter(self, predicate):
        return self.__class__([m for m in self if predicate(m)], self.post_apply)

    def replace(self, newmigrations):
        return self.__class__(newmigrations, self.post_apply)


class StepCollector(object):
    """
    Provide the ``step`` and ``transaction`` functions used in migration
    scripts.

    Each call to step/transaction updates the StepCollector's ``steps`` list.
    """

    def __init__(self, migration):
        self.migration = migration
        self.steps = OrderedDict()
        self.step_id = count(0)

    def add_step(self, apply, rollback=None, ignore_errors=None):
        """
        Wrap the given apply and rollback code in a transaction, and add it
        to the list of steps.
        Return the transaction-wrapped step.
        """

        def do_add(use_transactions):
            wrapper = TransactionWrapper if use_transactions else Transactionless
            t = MigrationStep(next(self.step_id), apply, rollback)
            t = wrapper(t, ignore_errors)
            return t

        self.steps[do_add] = 1
        return do_add

    def add_step_group(self, *args, **kwargs):
        """
        Create a ``StepGroup`` group of steps.
        """
        if "steps" in kwargs:
            if args:
                raise ValueError(
                    "steps cannot be called with both keyword "
                    "and positional 'steps' argument"
                )

            steps = kwargs["steps"]
        else:
            steps = list(chain(*(s if isinstance(s, Iterable) else [s] for s in args)))
        for s in steps:
            del self.steps[s]

        def do_add(use_transactions):
            ignore_errors = kwargs.pop("ignore_errors", None)
            wrapper = TransactionWrapper if use_transactions else Transactionless

            group = StepGroup([create_step(use_transactions) for create_step in steps])
            return wrapper(group, ignore_errors)

        self.steps[do_add] = 1
        return do_add

    def create_steps(self, use_transactions):
        return [create_step(use_transactions) for create_step in self.steps]


def _get_collector(depth=2):
    return inspect.stack()[depth][0].f_locals["collector"]


def step(*args, **kwargs):
    return _get_collector().add_step(*args, **kwargs)


def group(*args, **kwargs):
    return _get_collector().add_step_group(*args, **kwargs)


#: Alias for compatibility purposes.
#: This no longer affects transaction handling.
transaction = group


def ancestors(migration, population):
    """
    Return the dependencies for ``migration`` from ``population``.

    :param migration: a :class:`~yoyo.migrations.Migration` object
    :param population: a collection of migrations
    """
    to_process = set()
    for m in migration.depends:
        to_process.add(m)

    deps = set()
    while to_process:
        m = to_process.pop()
        deps.add(m)
        for d in m.depends:
            if d in deps:
                continue
            deps.add(d)
            to_process.add(d)
    return deps


def descendants(migration, population):
    """
    Return all descendants of ``migration`` from ``population``.

    :param migration: a :class:`~yoyo.migrations.Migration` object
    :param population: a collection of migrations
    """
    population = set(population)
    descendants = {migration}
    while True:
        found = False
        for m in population - descendants:
            if set(m.depends) & descendants:
                descendants.add(m)
                found = True
        if not found:
            break
    descendants.remove(migration)
    return descendants


def heads(migration_list):
    """
    Return the set of migrations that have no child dependencies
    """
    heads = set(migration_list)
    for m in migration_list:
        heads -= m.depends
    return heads


def topological_sort(migration_list):

    # The sorted list, initially empty
    L = list()

    # Make a copy of migration_list. It's probably an iterator.
    migration_list = list(migration_list)
    valid_migrations = set(migration_list)

    # Track graph edges in two parallel data structures.
    # Use OrderedDict so that we can traverse edges in order
    # and keep the sort stable
    forward_edges = defaultdict(OrderedDict)
    backward_edges = defaultdict(OrderedDict)

    for m in migration_list:
        for n in m.depends:
            if n not in valid_migrations:
                continue
            forward_edges[n][m] = 1
            backward_edges[m][n] = 1

    # Only toposort the migrations forming part of the dependency graph
    to_toposort = set(chain(forward_edges, backward_edges))

    # Starting migrations: those with no dependencies
    # To make this a stable sort we always need to pop from the left end
    # of this list, hence use a deque.
    S = deque(
        m for m in to_toposort if not any(n in valid_migrations for n in m.depends)
    )

    while S:
        n = S.popleft()
        L.append(n)

        # for each node M with an edge E from N to M
        for m in list(forward_edges[n]):

            # remove edge E from the graph
            del forward_edges[n][m]
            del backward_edges[m][n]

            # If M has no other incoming edges, it qualifies as a starting node
            if not backward_edges[m]:
                S.append(m)

    if any(forward_edges.values()):
        raise exceptions.BadMigration(
            "Circular dependencies among these migrations {}".format(
                ", ".join(
                    m.id for m in forward_edges for n in {m} | set(forward_edges[m])
                )
            )
        )

    # Return the toposorted migrations followed by the remainder of migrations
    # in their original order
    return L + [m for m in migration_list if m not in to_toposort]
