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

import argparse
import re
import warnings
from tabulate import tabulate

from yoyo import read_migrations, default_migration_table, ancestors, descendants
from yoyo.scripts.main import InvalidArgument, get_backend
from yoyo import utils


def install_argparsers(global_parser, subparsers):
    migration_parser = argparse.ArgumentParser(add_help=False)
    migration_parser.add_argument(
        "sources", nargs="*", help="Source directory of migration scripts"
    )

    migration_parser.add_argument(
        "-d",
        "--database",
        default=None,
        help="Database, eg 'sqlite:///path/to/sqlite.db' "
        "or 'postgresql://user@host/db'",
    )

    migration_parser.add_argument(
        "-m",
        "--match",
        help="Select migrations matching PATTERN (regular expression)",
        metavar="PATTERN",
    )

    migration_parser.add_argument(
        "-a",
        "--all",
        dest="all",
        action="store_true",
        help="Select all migrations, regardless of whether "
        "they have been previously applied",
    )

    migration_parser.add_argument(
        "-f",
        "--force",
        dest="force",
        action="store_true",
        help="Force apply/rollback of steps even if " "previous steps have failed",
    )

    migration_parser.add_argument(
        "-p",
        "--prompt-password",
        dest="prompt_password",
        action="store_true",
        help="Prompt for the database password",
    )

    migration_parser.add_argument(
        "--migration-table",
        dest="migration_table",
        action="store",
        default=default_migration_table,
        help="Name of table to use for storing " "migration metadata",
    )

    migration_parser.add_argument(
        "-r",
        "--revision",
        help="Apply/rollback migration with id " "REVISION",
        metavar="REVISION",
    )

    parser_apply = subparsers.add_parser(
        "apply", help="Apply migrations", parents=[global_parser, migration_parser]
    )
    parser_apply.set_defaults(func=apply, command_name="apply")

    parser_apply = subparsers.add_parser(
        "showmigrations", help="Show migrations", parents=[global_parser, migration_parser]
    )
    parser_apply.set_defaults(func=show_migrations, command_name="showmigrations")

    parser_rollback = subparsers.add_parser(
        "rollback",
        parents=[global_parser, migration_parser],
        help="Rollback migrations",
    )
    parser_rollback.set_defaults(func=rollback, command_name="rollback")

    parser_reapply = subparsers.add_parser(
        "reapply", parents=[global_parser, migration_parser], help="Reapply migrations"
    )
    parser_reapply.set_defaults(func=reapply, command_name="reapply")

    parser_mark = subparsers.add_parser(
        "mark",
        parents=[global_parser, migration_parser],
        help="Mark migrations as applied, without running them",
    )
    parser_mark.set_defaults(func=mark, command_name="mark")

    parser_unmark = subparsers.add_parser(
        "unmark",
        parents=[global_parser, migration_parser],
        help="Unmark applied migrations, without rolling them back",
    )
    parser_unmark.set_defaults(func=unmark, command_name="unmark")

    parser_break_lock = subparsers.add_parser(
        "break-lock", parents=[global_parser], help="Break migration locks"
    )
    parser_break_lock.set_defaults(func=break_lock, command_name="break-lock")
    parser_break_lock.add_argument(
        "-d",
        "--database",
        default=None,
        help="Database, eg 'sqlite:///path/to/sqlite.db' "
        "or 'postgresql://user@host/db'",
    )


def get_migrations(args, backend):
    sources = args.sources
    dburi = args.database

    if not sources:
        raise InvalidArgument("Please specify the migration source directory")

    migrations = read_migrations(*sources)

    if args.match:
        migrations = migrations.filter(
            lambda m: re.search(args.match, m.id) is not None
        )

    if not args.all:
        if args.func in {apply, mark}:
            migrations = backend.to_apply(migrations)

        elif args.func in {rollback, reapply, unmark}:
            migrations = backend.to_rollback(migrations)

        elif args.func == show_migrations:
            return backend.get_migrations_with_applied_status(migrations)

    if args.revision:
        targets = [m for m in migrations if args.revision in m.id]
        if len(targets) == 0:
            raise InvalidArgument(
                "'{}' doesn't match any revisions.".format(args.revision)
            )
        if len(targets) > 1:
            raise InvalidArgument(
                "'{}' matches multiple revisions. "
                "Please specify one of {}.".format(
                    args.revision, ", ".join(m.id for m in targets)
                )
            )

        target = targets[0]

        # apply: apply target an all its dependencies
        if args.func in {mark, apply}:
            deps = ancestors(target, migrations)
            target_plus_deps = deps | {target}
            migrations = migrations.filter(lambda m: m in target_plus_deps)

        # rollback/reapply: rollback target and everything that depends on it
        else:
            deps = descendants(target, migrations)
            target_plus_deps = deps | {target}
            migrations = migrations.filter(lambda m: m in target_plus_deps)

    if not args.batch_mode and not args.revision:
        migrations = prompt_migrations(backend, migrations, args.command_name)

    if args.batch_mode and not args.revision and not args.all and args.func is rollback:
        if len(migrations) > 1:
            warnings.warn(
                "Only rolling back a single migration."
                "To roll back multiple migrations, "
                "either use interactive mode or use "
                "--revision or --all"
            )
            migrations = migrations[:1]

    if not args.batch_mode and migrations:
        print("")
        print(
            "Selected", utils.plural(len(migrations), "%d migration:", "%d migrations:")
        )
        for m in migrations:
            print("  [{m.id}]".format(m=m))
        prompt = "{} {} to {}".format(
            args.command_name.title(),
            utils.plural(len(migrations), "this migration", "these %d migrations"),
            dburi,
        )
        if not utils.confirm(prompt, default="y"):
            return migrations.replace([])
    return migrations


def apply(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)
        backend.apply_migrations(migrations, args.force)


def show_migrations(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)

        print(tabulate(
            [(m.id, '\033[92m Yes \033[0m' if m.applied else '\033[91m No \033[0m') for m in migrations],
            headers=['Migration', 'Applied'])
        )


def reapply(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)
        backend.rollback_migrations(migrations, args.force)
        migrations = backend.to_apply(migrations)
        backend.apply_migrations(migrations, args.force)


def rollback(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)
        backend.rollback_migrations(migrations, args.force)


def mark(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)
        backend.mark_migrations(migrations)


def unmark(args, config):
    backend = get_backend(args, config)
    with backend.lock():
        migrations = get_migrations(args, backend)
        backend.unmark_migrations(migrations)


def break_lock(args, config):
    backend = get_backend(args, config)
    backend.break_lock()


def prompt_migrations(backend, migrations, direction):
    """
    Iterate through the list of migrations and prompt the user to
    apply/rollback each. Return a list of user selected migrations.

    direction
        one of 'apply' or 'rollback'
    """

    class prompted_migration(object):
        def __init__(self, migration, default=None):
            super(prompted_migration, self).__init__()
            self.migration = migration
            self.choice = default

    to_prompt = [prompted_migration(m) for m in migrations]

    position = 0
    while position < len(to_prompt):
        mig = to_prompt[position]

        choice = mig.choice
        if choice is None:
            is_applied = backend.is_applied(mig.migration)
            if direction == "apply":
                choice = "n" if is_applied else "y"
            else:
                choice = "y" if is_applied else "n"
        options = "".join(o.upper() if o == choice else o.lower() for o in "ynvdaqjk?")

        print("")
        print("[%s]" % (mig.migration.id,))
        response = utils.prompt("Shall I %s this migration?" % (direction,), options)

        if response == "?":
            print("")
            print("y: %s this migration" % (direction,))
            print("n: don't %s it" % (direction,))
            print("")
            print("v: view this migration in full")
            print("")
            print(
                "d: %s the selected migrations, skipping any remaining" % (direction,)
            )
            print("a: %s all the remaining migrations" % (direction,))
            print("q: cancel without making any changes")
            print("")
            print("j: skip to next migration")
            print("k: back up to previous migration")
            print("")
            print("?: show this help")
            continue

        if response in "yn":
            mig.choice = response
            position += 1
            continue

        if response == "v":
            print(mig.migration.source)
            continue

        if response == "j":
            position = min(len(to_prompt), position + 1)
            continue

        if response == "k":
            position = max(0, position - 1)

        if response == "d":
            break

        if response == "a":
            for mig in to_prompt[position:]:
                mig.choice = "y"
            break

        if response == "q":
            for mig in to_prompt:
                mig.choice = "n"
            break

    return migrations.replace(m.migration for m in to_prompt if m.choice == "y")
