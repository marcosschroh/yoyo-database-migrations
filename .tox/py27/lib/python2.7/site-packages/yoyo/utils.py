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

from __future__ import print_function
from itertools import count
import os
import random
import re
import string
import sys

from yoyo.compat import configparser
from yoyo.config import CONFIG_EDITOR_KEY

try:
    import termios

    def getch():
        """
        Read a single character without echoing to the console and without
        having to wait for a newline.
        """
        fd = sys.stdin.fileno()
        saved_attributes = termios.tcgetattr(fd)
        try:
            attributes = termios.tcgetattr(fd)  # get a fresh copy!
            attributes[3] = attributes[3] & ~(termios.ICANON | termios.ECHO)
            attributes[6][termios.VMIN] = 1
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, attributes)

            a = sys.stdin.read(1)
        finally:
            # be sure to reset the attributes no matter what!
            termios.tcsetattr(fd, termios.TCSANOW, saved_attributes)
        return a


except ImportError:
    try:
        from msvcrt import getwch as getch
    except ImportError:
        # some non Windows environments don't have termios (google cloud)
        # running yoyo through the python sdk should not require `getch`
        pass


def prompt(prompt, options):
    """
    Display the given prompt and list of options and return the user selection.
    """

    while True:
        sys.stdout.write("%s [%s]: " % (prompt, options))
        sys.stdout.flush()
        ch = getch()
        if ch == os.linesep:
            ch = (
                [o.lower() for o in options if "A" <= o <= "Z"] + list(options.lower())
            )[0]
        print(ch)
        if ch.lower() not in options.lower():
            print("Invalid response, please try again!")
        else:
            break

    return ch.lower()


def confirm(s, default=None):
    options = "yn"
    if default:
        default = default.lower()
        if default == "y":
            options = "Yn"
        elif default == "n":
            options = "yN"
    return prompt(s, options) == "y"


def plural(quantity, one, plural):
    """
    >>> plural(1, '%d dead frog', '%d dead frogs')
    '1 dead frog'
    >>> plural(2, '%d dead frog', '%d dead frogs')
    '2 dead frogs'
    """
    if quantity == 1:
        return one.replace("%d", "%d" % quantity)
    return plural.replace("%d", "%d" % quantity)


def get_editor(config):
    """
    Return the user's preferred visual editor
    """
    try:
        return config.get("DEFAULT", CONFIG_EDITOR_KEY)
    except configparser.NoOptionError:
        pass
    for key in ["VISUAL", "EDITOR"]:
        editor = os.environ.get(key, None)
        if editor:
            return editor
    return "vi"


def get_random_string(length, chars=(string.ascii_letters + string.digits)):
    """
    Return a random string of ``length`` characters
    """
    rng = random.SystemRandom()
    return "".join(rng.choice(chars) for i in range(length))


def change_param_style(target_style, sql, bind_parameters):
    """
    :param target_style: A DBAPI paramstyle value (eg 'qmark', 'format', etc)
    :param sql: An SQL str
    :bind_parameters: A dict of bind parameters for the query

    :return: tuple of `(sql, bind_parameters)`. ``sql`` will be rewritten with
             the target paramstyle; ``bind_parameters`` will be a tuple or
             dict as required.
    """
    if target_style == "named":
        return sql, bind_parameters
    positional = target_style in {"qmark", "numeric", "format"}
    if not bind_parameters:
        return (sql, (tuple() if positional else {}))

    param_gen = {
        "qmark": lambda name: "?",
        "numeric": lambda name, c=count(1): ":{}".format(next(c)),
        "format": lambda name: "%s",
        "pyformat": lambda name: "%({})s".format(name),
    }[target_style]

    pattern = re.compile(
        # Don't match if preceded by backslash (an escape)
        # or ':' (an SQL cast, eg '::INT')
        r"(?<![:\\])"
        # one of the given bind_parameters
        r":("
        + "|".join(re.escape(k) for k in bind_parameters)
        + r")"
        # followed by a non-word char, or end of string
        r"(?=\W|$)"
    )

    transformed_sql = pattern.sub(lambda match: param_gen(match.group(1)), sql)
    if positional:
        positional_params = []
        for match in pattern.finditer(sql):
            param_name = match.group(1)
            positional_params.append(bind_parameters[param_name])
        return transformed_sql, tuple(positional_params)
    return transformed_sql, bind_parameters
