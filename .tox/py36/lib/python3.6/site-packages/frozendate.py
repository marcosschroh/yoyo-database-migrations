from collections import namedtuple
from contextlib import contextmanager
from datetime import date as real_date, datetime as real_datetime, timedelta
import re
import sys
import time

from mock import patch as mockpatch

__version__ = '0.1.3'

_patch_contexts = []

contextinfo = namedtuple('contextinfo', 'relnow modules patches')

#: Never patch these modules (unless explicitly demanded)
always_exclude = {__name__, 'datetime', 'six.moves.', 'dateutil'}


class FrozenDateMeta(type):
    """
    Allow a FrozenDate class to act as a virtual base class of
    ``datetime.date``.
    """

    virtual_base = real_date

    def __subclasscheck__(self, other):
        return issubclass(other, self.virtual_base)

    def __instancecheck__(self, other):
        return isinstance(other, self.virtual_base)


class FrozenDatetimeMeta(FrozenDateMeta):

    virtual_base = real_datetime


class RelativeNow(object):
    """
    Provide a callable that returns either:

    - A fixed datetime value of ``when`` (hard=True)
    - A datetime value starting at ``when``, updating in realtime (hard=False)
    """
    def __init__(self, when, hard):
        self.basetime = time.mktime(when.timetuple())
        self.hard = hard
        self.created_at = time.time()

    def now(self, tz=None):
        if self.hard:
            offset = 0
        else:
            offset = time.time() - self.created_at
        return real_datetime.fromtimestamp(self.basetime + offset, tz)

    def utcnow(self):
        if self.hard:
            offset = 0
        else:
            offset = time.time() - self.created_at
        return real_datetime.utcfromtimestamp(self.basetime + offset)


class FrozenDate(real_date):

    relnow = None

    @classmethod
    def today(cls):
        return cls.relnow.now().date()


class FrozenDatetime(real_datetime):

    relnow = None

    @classmethod
    def today(cls):
        return cls.relnow.now()

    @classmethod
    def now(cls, tz=None):
        return cls.relnow.now(tz)

    @classmethod
    def utcnow(cls):
        return cls.relnow.utcnow()


def _get_to_patch(kwargs):
    modules = kwargs.pop('modules', None)
    dontpatch = kwargs.pop('dontpatch', None)
    previous = kwargs.pop('previous', True)
    if modules is None:
        modules = find_modules(previous=previous)
    if dontpatch:
        modules = exclude_modules(modules, dontpatch)
    return modules


def _get_timedelta(args, kwargs):
    if not kwargs and len(args) == 1:
        assert isinstance(args[0], timedelta)
        return args[0]
    return timedelta(*args, **kwargs)


def _get_datetime(args, kwargs):
    if not kwargs and len(args) == 1:
        assert isinstance(args[0], real_datetime)
        return args[0]
    return real_datetime(*args, **kwargs)


def push_patch_context(info):
    _patch_contexts.append(info)


def pop_patch_context():
    return _patch_contexts.pop()


def current_patch_context():
    return _patch_contexts[-1]


def make_frozendate(relnow):
    assert isinstance(relnow, RelativeNow)
    return FrozenDateMeta('FrozenDate', (FrozenDate,), {'relnow': relnow})


def make_frozendatetime(relnow):
    assert isinstance(relnow, RelativeNow)
    return FrozenDatetimeMeta('FrozenDatetime', (FrozenDatetime,),
                              {'relnow': relnow})


def _patch_module(name, relnow):
    """
    patch a single module
    """

    module = sys.modules[name]
    patches = []
    try:
        date_is_patchable = issubclass(getattr(module, 'date', None),
                                       real_date)
    except TypeError:
        date_is_patchable = False

    try:
        datetime_is_patchable = issubclass(getattr(module, 'datetime', None),
                                           real_datetime)
    except TypeError:
        datetime_is_patchable = False

    if date_is_patchable:
        p = mockpatch('{0}.date'.format(module.__name__),
                      make_frozendate(relnow))
        p.start()
        patches.append(p)

    if datetime_is_patchable:
        p = mockpatch('{0}.datetime'.format(module.__name__),
                      make_frozendatetime(relnow))
        p.start()
        patches.append(p)

    return patches


def patch(*args, **kwargs):
    """
    Patch a list of modules, defaulting to all modules found in sys.modules

    :param modules: A list of module to be patched. If not supplied, all
                    modules will be patched.
    :param dontpatch: A list of module names that will not be patched. Items
                      match by prefix (so ``dontpatch=['mypackage.']`` would
                      skip all modules in ``mypackage``)
    :param hard: If true, the datetime will be frozen hard (all calls to
                 datetime.now return exactly the same value). If false, calls
                 to datetime.now will start from the given date, and update in
                 real time.
    """
    hard = kwargs.pop('hard', False)
    modules = _get_to_patch(kwargs)
    relnow = RelativeNow(_get_datetime(args, kwargs), hard=hard)
    return _patch(modules, relnow)


def _patch(modules, relnow):
    patches = sum((_patch_module(m, relnow) for m in modules), [])
    push_patch_context(contextinfo(relnow, modules, patches))


def find_modules(previous=True):
    if previous:
        try:
            modules = current_patch_context().modules
        except IndexError:
            modules = sys.modules.keys()
    else:
        modules = sys.modules.keys()
    return exclude_modules(modules, always_exclude)


def exclude_modules(modules, dontpatch):
    if not dontpatch:
        return modules
    dontpatch = re.compile('|'.join(re.escape(s) for s in dontpatch)).match
    return [m for m in modules if not dontpatch(m)]


def unpatch():
    """
    Unpatch all previously patched modules.

    If there are nested calls to freeze/patch
    this only unpatches the patches applied by the innermost call
    """
    relnow, modules, patches = pop_patch_context()
    for patch in patches:
        patch.stop()


@contextmanager
def freeze(*args, **kwargs):
    """
    Freeze time. Acts as a context manager, eg::

        with freeze(2000, 12, 31):
            assert we_all_met_up()

    :param modules: A list of module to be patched. If not supplied, all
                    modules will be patched.
    :param dontpatch: A list of module names that will not be patched. Items
                      match by prefix (so ``dontpatch=['mypackage.']`` would
                      skip all modules in ``mypackage``)
    :param hard: If true, the datetime will be frozen hard (all calls to
                 datetime.now return exactly the same value). If false, calls
                 to datetime.now will start from the given date, and update in
                 real time.
    """
    hard = kwargs.pop('hard', False)
    modules = _get_to_patch(kwargs)
    when = RelativeNow(_get_datetime(args, kwargs), hard)
    _patch(modules, when)
    yield now()
    unpatch()


@contextmanager
def freeze_relative(*args, **kwargs):
    """
    Freeze time relative to the previous freezing. Acts as a context manager,
    eg::

        with freeze_relative(days=-1):
            assert all_my_troubles_seemed_so_far_away()


    :param modules: A list of module to be patched. If not supplied, all
                    modules will be patched.
    :param dontpatch: A list of module names that will not be patched. Items
                      match by prefix (so ``dontpatch=['mypackage.']`` would
                      skip all modules in ``mypackage``)
    :param hard: If true, the datetime will be frozen hard (all calls to
                 datetime.now return exactly the same value). If false, calls
                 to datetime.now will start from the given date, and update in
                 real time.
    """
    hard = kwargs.pop('hard', False)
    modules = _get_to_patch(kwargs)
    delta = _get_timedelta(args, kwargs)
    _patch(modules, RelativeNow(now() + delta, hard=hard))
    yield now()
    unpatch()


def now():
    """
    Return the currently frozen datetime
    """
    try:
        ci = current_patch_context()
        return ci.relnow.now()
    except IndexError:
        return real_datetime.now()


def today():
    """
    Return the currently frozen date
    """
    return now().date()
