__version__ = '0.1.2'

from functools import partial

try:
    filetype = file
except NameError:
    import io
    filetype = io.IOBase


class DoesntMatch(AssertionError):
    pass


class Matcher(object):

    def __init__(self, condition):
        self.condition = condition

    def __eq__(self, other):
        return self.condition(other)

    def __ne__(self, other):
        try:
            return not self.condition(other)
        except DoesntMatch:
            return True

    def __and__(self, other):
        if not isinstance(other, Matcher):
            other = Matcher(other)
        return self.__class__(lambda ob: self.condition(ob) and
                              other.condition(ob))

    def __or__(self, other):
        if not isinstance(other, Matcher):
            other = Matcher(other)

        def orcondition(ob):
            try:
                if other.condition(ob):
                    return True
            except DoesntMatch:
                return self.condition(ob)

        return self.__class__(orcondition)


def HasKeysAndAttrs(**attrs):

    attrs = attrs.copy()

    has_attrs = attrs.pop('has_attrs', [])
    has_keys = attrs.pop('has_keys', [])
    has_items = dict(attrs.pop('has_items', []))

    has_keys.extend(has_items.keys())
    has_attrs.extend(attrs.keys())

    def match_func(other):
        marker = []

        for item in has_keys:
            if item not in other:
                raise DoesntMatch('%r does not contain the key %r' %
                                  (other, item))

        for item in has_attrs:
            if getattr(other, item, marker) is marker:
                raise DoesntMatch('%r does not have an attribute '
                                  'named %r. ' % (other, item))

        for item, expected in attrs.items():
            value = getattr(other, item)
            if expected != value:
                raise DoesntMatch('%r.%s: Expected %r. Got %r.' %
                                  (other, item, expected, value))

        for key, expected in has_items.items():
            value = other[key]
            if expected != value:
                raise DoesntMatch('%r[%r]: Expected %r. Got %r.' %
                                  (other, key, expected, value))

        return True
    return Matcher(match_func)


def InstanceOf(cls, *tests, **attrs):
    def match_func(other):
        if not isinstance(other, cls):
            raise DoesntMatch('Expected: %s instance. '
                              'Got: %r' % (cls, other))
        return True
    return Matcher(match_func) & HasKeysAndAttrs(**attrs) & Passes(*tests)

Bool = partial(InstanceOf, bool)
ByteArray = partial(InstanceOf, bytearray)
Bytes = partial(InstanceOf, bytes)
Complex = partial(InstanceOf, complex)
Dict = partial(InstanceOf, dict)
Exception = partial(InstanceOf, Exception)
File = partial(InstanceOf, filetype)
Float = partial(InstanceOf, float)
FrozenSet = partial(InstanceOf, frozenset)
Int = partial(InstanceOf, int)
List = partial(InstanceOf, list)
Object = partial(InstanceOf, object)
Set = partial(InstanceOf, set)
Str = partial(InstanceOf, str)
Tuple = partial(InstanceOf, tuple)
Type = partial(InstanceOf, type)
Unicode = partial(InstanceOf, type(u''))


def Contains(*things):
    """
    Return a matcher that matches only if all ``things`` are present in the
    object
    """
    return Matcher(lambda container: all(n in container for n in things))


def DoesntContain(*things):
    """
    Return a matcher that matches only if none of ``things`` is present in the
    object
    """
    return Matcher(lambda container: all(n not in container for n in things))


def Anything(**attrs):
    return Matcher(lambda other: True) & HasKeysAndAttrs(**attrs)


def Passes(*tests):
    def match_func(ob):
        for t in tests:
            if not t(ob):
                raise DoesntMatch('%r failed to pass test %r' % (ob, t))
        return True
    return Matcher(match_func)


def DictLike(*args, **kwargs):
    return HasKeysAndAttrs(has_items=dict(*args, **kwargs))
