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

import codecs
import locale
import sys

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # noqa

try:
    from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl, quote, unquote
except ImportError:
    from urlparse import urlsplit, urlunsplit, parse_qsl  # noqa
    from urllib import urlencode, quote, unquote  # noqa


PY2 = sys.version_info[0] == 2

if PY2:
    ustr = unicode  # noqa
else:
    ustr = str

if PY2:
    exec("def reraise(tp, value, tb):\n raise tp, value, tb")
else:

    def reraise(tp, value, tb):
        raise value.with_traceback(tb)


if PY2:
    exec("def exec_(code, globals_):\n " "exec code in globals_")
else:

    def exec_(code, globals_):
        exec(code, globals_)


if PY2 and hasattr(sys.stdout, "isatty"):
    # In python2 sys.stdout is a byte stream.
    # Convert it to a unicode stream using the environment's preferred encoding
    if sys.stdout.isatty():
        encoding = sys.stdout.encoding
    else:
        encoding = locale.getpreferredencoding()
    stdout = codecs.getwriter(encoding)(sys.stdout)

else:
    stdout = sys.stdout
