# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2013/08/20
# copy: (C) Copyright 2013 Cadit Health Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import unittest
import io
import textwrap

import six

from iniherit.parser import Loader, ConfigParser, SafeConfigParser

#------------------------------------------------------------------------------
class ByteLoader(Loader):
  def __init__(self, *args, **kw):
    self.items = dict()
    self.items.update(*args, **kw)
  def load(self, name, encoding=None):
    if name not in self.items:
      raise IOError(2, 'No such file or directory', name)
    ret = six.StringIO(self.items[name])
    ret.name = name
    return ret

#------------------------------------------------------------------------------
class TestIniherit(unittest.TestCase):

  maxDiff = None

  #----------------------------------------------------------------------------
  def test_iniherit(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '''
        [DEFAULT]
        kw1 = base-kw1
        kw2 = base-kw2
        [section]
        test1 = only in base, the value "%(kw1)s" should be "base-kw1"
        test2 = the value "%(kw2)s" should be "base-kw2"
      ''',
      'extend.ini' : '''
        [DEFAULT]
        %inherit = base.ini
        kw1 = extend-kw1
      ''',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    self.assertEqual(parser.get('DEFAULT', 'kw1'), 'extend-kw1')
    self.assertEqual(parser.get('DEFAULT', 'kw2'), 'base-kw2')
    self.assertEqual(parser.get('section', 'test1'),
                     'only in base, the value "extend-kw1" should be "base-kw1"')
    self.assertEqual(parser.get('section', 'test2'),
                     'the value "base-kw2" should be "base-kw2"')
    self.assertFalse(parser.has_option('DEFAULT', '%inherit'))

  #----------------------------------------------------------------------------
  def test_iniherit_multiple(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '''
        [DEFAULT]
        kw1 = base-kw1
        kw2 = base-kw2
        kw3 = base-kw3
        kw4 = base-kw4
      ''',
      'override.ini' : '''
        [DEFAULT]
        kw2 = override-kw2
        kw3 = override-kw3
        kw5 = override-kw5
      ''',
      'extend.ini' : '''
        [DEFAULT]
        %inherit = base.ini ?no-such-ini.ini override.ini
        kw1 = extend-kw1
        kw3 = extend-kw3
        kw6 = extend-kw6
      ''',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    self.assertEqual(parser.get('DEFAULT', 'kw1'), 'extend-kw1')
    self.assertEqual(parser.get('DEFAULT', 'kw2'), 'override-kw2')
    self.assertEqual(parser.get('DEFAULT', 'kw3'), 'extend-kw3')
    self.assertEqual(parser.get('DEFAULT', 'kw4'), 'base-kw4')
    self.assertEqual(parser.get('DEFAULT', 'kw5'), 'override-kw5')
    self.assertEqual(parser.get('DEFAULT', 'kw6'), 'extend-kw6')

  #----------------------------------------------------------------------------
  def test_iniherit_noSuchFile(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini'   : '[DEFAULT]\nkw1 = base-kw1\n',
      'extend.ini' : '[DEFAULT]\n%inherit = base.ini no-such-ini.ini\nkw2 = extend-kw2\n',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    self.assertRaises(IOError, parser.read, 'extend.ini')

  #----------------------------------------------------------------------------
  def test_iniherit_relativePath(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'dir/base.ini' : '[section]\nkw1 = base-kw1\n',
      'dir/mid.ini'  : '[DEFAULT]\n%inherit = base.ini\n[section]\nkw2 = mid-kw2\n',
      'extend.ini'   : '[DEFAULT]\n%inherit = dir/mid.ini\n[section]\nkw3 = extend-kw3\n',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    self.assertEqual(parser.get('section', 'kw1'), 'base-kw1')
    self.assertEqual(parser.get('section', 'kw2'), 'mid-kw2')
    self.assertEqual(parser.get('section', 'kw3'), 'extend-kw3')

  #----------------------------------------------------------------------------
  def test_iniherit_inheritTargetInterpolation(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base-without-interpolation.ini' : '''
        [DEFAULT]
        %inherit = dir/foo.ini
        code = foo
        [section]
        %inherit = dir/bar.ini
        code = %(ENV:THECODE:-noexist)s
      ''',
      'base-with-interpolation.ini' : '''
        [DEFAULT]
        %inherit = dir/%(code)s.ini
        code = foo
        [section]
        %inherit = dir/%(ENV:THECODE:-noexist)s.ini
        code = %(ENV:THECODE:-noexist)s
      ''',
      'base-with-cascading-interpolation.ini' : '''
        [DEFAULT]
        %inherit = dir/%(code)s.ini
        code = foo
        [section]
        %inherit = dir/%(code)s.ini
        code = %(ENV:THECODE:-noexist)s
      ''',
      'dir/foo.ini' : '''
        [DEFAULT]
        value = it-is-foo
      ''',
      'dir/bar.ini' : '''
        [section]
        value = it-is-bar
      ''',
    }.items()}
    import os
    os.environ['THECODE'] = 'bar'
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('base-without-interpolation.ini')
    self.assertEqual(parser.get('DEFAULT', 'value'), 'it-is-foo')
    self.assertEqual(parser.get('DEFAULT', 'code'), 'foo')
    self.assertEqual(parser.get('section', 'value'), 'it-is-bar')
    self.assertEqual(parser.get('section', 'code'), 'bar')
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('base-with-interpolation.ini')
    self.assertEqual(parser.get('DEFAULT', 'value'), 'it-is-foo')
    self.assertEqual(parser.get('DEFAULT', 'code'), 'foo')
    self.assertEqual(parser.get('section', 'value'), 'it-is-bar')
    self.assertEqual(parser.get('section', 'code'), 'bar')
    # TODO: enable this when "%inherit" interpolation uses iniherit
    #       interpolation for recursive interpolation...
    # parser = ConfigParser(loader=ByteLoader(files))
    # parser.read('base-with-cascading-interpolation.ini')
    # self.assertEqual(parser.get('DEFAULT', 'value'), 'it-is-foo')
    # self.assertEqual(parser.get('DEFAULT', 'code'), 'foo')
    # self.assertEqual(parser.get('section', 'value'), 'it-is-bar')
    # self.assertEqual(parser.get('section', 'code'), 'bar')

  #----------------------------------------------------------------------------
  def test_iniherit_nameWithSpace(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base + space.ini' : '[DEFAULT]\nkw=word\n',
      'config.ini'       : '[DEFAULT]\n%inherit = base%20%2b%20space.ini\n',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('config.ini')
    self.assertEqual(parser.get('DEFAULT', 'kw'), 'word')

  #----------------------------------------------------------------------------
  def test_iniherit_sectionInherit(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini'   : '[DEFAULT]\nkw1=word\n[s]\nfoo=bar\nx=y\n',
      'other.ini'  : '[DEFAULT]\nkw2=word\n[so]\nzig=zag\n',
      'config.ini' : '[s]\n%inherit = base.ini other.ini[so]\nx=z\n',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('config.ini')
    self.assertEqual(parser.items('DEFAULT'), [])
    self.assertEqual(sorted(parser.items('s')),
                     sorted(dict(foo='bar', zig='zag', x='z').items()))

  #----------------------------------------------------------------------------
  def test_iniherit_interpolation(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'config.ini' : '[app]\noutput = %(tmpdir)s/var/result.log\n',
    }.items()}
    parser = SafeConfigParser(
      defaults={'tmpdir': '/tmp'}, loader=ByteLoader(dict(files)))
    parser.read('config.ini')
    self.assertEqual(parser.get('app', 'output'), '/tmp/var/result.log')
    self.assertEqual(parser.get('app', 'output', raw=True), '%(tmpdir)s/var/result.log')

  #----------------------------------------------------------------------------
  def test_iniherit_invalidInterpolationValues(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'config.ini' : '[logger]\ntimefmt=%H:%M:%S\n',
    }.items()}
    parser = SafeConfigParser(loader=ByteLoader(dict(files)))
    parser.read('config.ini')
    self.assertEqual(parser.items('DEFAULT'), [])
    self.assertEqual(parser.get('logger', 'timefmt', raw=True), '%H:%M:%S')

  #----------------------------------------------------------------------------
  def test_install_globally(self):
    from iniherit.parser import CP
    from iniherit.mixin import install_globally, uninstall_globally

    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini'   : '[DEFAULT]\nkw = base-kw\n',
      'config.ini' : '[DEFAULT]\n%inherit = base.ini\n',
    }.items()}
    loader = ByteLoader(dict(files))

    def do_the_test():
      # first test that inheritance doesn't work
      parser = CP.ConfigParser()
      parser.loader = loader
      parser.readfp(loader.load('config.ini'))
      with self.assertRaises(CP.NoOptionError):
        parser.get('DEFAULT', 'kw')
      # then monkey-patch and test that inheritance does work
      install_globally()
      parser = CP.ConfigParser()
      parser.loader = loader
      parser.readfp(loader.load('config.ini'))
      self.assertEqual(parser.get('DEFAULT', 'kw'), 'base-kw')
      uninstall_globally()

    do_first_test = do_second_test = do_the_test
    do_first_test()
    do_second_test()

  #----------------------------------------------------------------------------
  def test_output_order_ascending(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '[s1]\ns1v = b1\n[s2]\ns2v = b2\n[s3]\ns3v = b3\n',
      'extend.ini' : '[DEFAULT]\n%inherit = base.ini\n[s2]\ns2v = o2',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    output = six.StringIO()
    parser.write(output)
    self.assertMultiLineEqual(
      output.getvalue(),
      '[s1]\ns1v = b1\n\n[s2]\ns2v = o2\n\n[s3]\ns3v = b3\n\n')

  #----------------------------------------------------------------------------
  def test_output_order_descending(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '[s3]\ns3v = b3\n[s2]\ns2v = b2\n[s1]\ns1v = b1\n',
      'extend.ini' : '[DEFAULT]\n%inherit = base.ini\n[s2]\ns2v = o2',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    output = six.StringIO()
    parser.write(output)
    self.assertMultiLineEqual(
      output.getvalue(),
      '[s3]\ns3v = b3\n\n[s2]\ns2v = o2\n\n[s1]\ns1v = b1\n\n')

  #----------------------------------------------------------------------------
  def test_interpolation_super_depth(self):
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '''\
        [DEFAULT]
        keys2 = base-vals
        # [loggers]
        # keys = root, authz
        # okeys = okeys-bVal
      ''',
      'mid.ini' : '''\
        [DEFAULT]
        %inherit = base.ini ?no-such-ini.ini
        # key1 = val1
      ''',
      'extend.ini' : '''\
        [DEFAULT]
        %inherit = mid.ini
        # nkeys = %(SUPER:-nval0)s, eVal1
        keys2 = %(SUPER:-nval0)s, eVal1
        # [loggers]
        # keys = %(SUPER)s, authn
        # okeys = %(SUPER:-okeys-eDef)s, okeys-eVal
        # dkeys = %(SUPER:-dkeys-eDef)s, dkeys-eVal
      ''',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')

    # self.assertEqual(parser.get('loggers', 'keys'), 'root, authz, authn')
    # self.assertEqual(parser.get('loggers', 'okeys'), 'okeys-bVal, okeys-eVal')
    # self.assertEqual(parser.get('loggers', 'dkeys'), 'dkeys-eDef, dkeys-eVal')

    self.assertEqual(parser.get('DEFAULT', 'keys2'), 'base-vals, eVal1')

    # self.assertEqual(parser.get('DEFAULT', 'nkeys'), 'nval0, eVal1')
    # self.assertEqual(parser.get('DEFAULT', 'key1'), 'val1')

  #----------------------------------------------------------------------------
  def test_interpolation_super_breadth(self):
    from iniherit import InterpolationMissingSuperError
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '''\
        [loggers]
        keys = root, authz
      ''',
      'adjust.ini' : '''\
        [loggers]
        keys = %(SUPER)s, authn
        nkey = %(SUPER)s and boom!
        dkey = %(SUPER:-more)s or less
      ''',
      'extend.ini' : '''\
        [DEFAULT]
        %inherit = base.ini adjust.ini
      ''',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    self.assertEqual(parser.get('loggers', 'keys'), 'root, authz, authn')
    self.assertEqual(parser.get('loggers', 'dkey'), 'more or less')
    with self.assertRaises(InterpolationMissingSuperError) as cm:
      parser.get('loggers', 'nkey')
    if six.PY2:
      err = textwrap.dedent('''\
        Bad value substitution:
        \tsection: [loggers]
        \toption : nkey
        \tkey    : SUPER
        \trawval : %(SUPER)s and boom!
      ''')
    else:
      err = (
        "Bad value substitution:"
        " option 'nkey' in section 'loggers'"
        " contains an interpolation key 'SUPER' which is not a valid option name."
        " Raw value: '%(SUPER)s and boom!'"
      )
    self.assertMultiLineEqual(str(cm.exception), err)

  #----------------------------------------------------------------------------
  def test_interpolation_super_invalid(self):
    from iniherit import InterpolationMissingSuperError
    files = {k: textwrap.dedent(v) for k, v in {
      'base.ini' : '''\
        [DEFAULT]
        key1 = val1
      ''',
      'extend.ini' : '''\
        [DEFAULT]
        %inherit = base.ini
        key2 = %(SUPER)s and boom!
      ''',
    }.items()}
    files = {k: textwrap.dedent(v) for k, v in files.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('extend.ini')
    with self.assertRaises(InterpolationMissingSuperError) as cm:
      parser.get('DEFAULT', 'key2')
    if six.PY2:
      err = textwrap.dedent('''\
        Bad value substitution:
        \tsection: [DEFAULT]
        \toption : key2
        \tkey    : SUPER
        \trawval : %(SUPER)s and boom!
      ''')
    else:
      err = (
        "Bad value substitution:"
        " option 'key2' in section 'DEFAULT'"
        " contains an interpolation key 'SUPER' which is not a valid option name."
        " Raw value: '%(SUPER)s and boom!'"
      )
    self.assertMultiLineEqual(str(cm.exception), err)

  #----------------------------------------------------------------------------
  def test_interpolation_env(self):
    import os
    from six.moves.configparser import InterpolationDepthError
    from iniherit import InterpolationMissingEnvError
    files = {k: textwrap.dedent(v) for k, v in {
      'config.ini' : '''\
        [section]
        key1 = %(ENV:INIHERIT_TEST_EXIST)s
        key2 = %(ENV:INIHERIT_TEST_EXIST:-default-value)s
        key3 = %(ENV:INIHERIT_TEST_NOEXIST)s
        key4 = %(ENV:INIHERIT_TEST_NOEXIST:-default-value)s
        key5 = %(ENV:INIHERIT_TEST_INFLOOP)s
      ''',
    }.items()}
    files = {k: textwrap.dedent(v) for k, v in files.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('config.ini')
    # note: setting envvar's *after* reading to ensure that interpolation
    #       occurs on-demand, i.e. lazy-eval
    os.environ.pop('INIHERIT_TEST_NOEXIST', None)
    os.environ['INIHERIT_TEST_EXIST']   = 'this-value'
    os.environ['INIHERIT_TEST_INFLOOP'] = '%(ENV:INIHERIT_TEST_INFLOOP)s'
    self.assertEqual(parser.get('section', 'key1'), 'this-value')
    self.assertEqual(parser.get('section', 'key2'), 'this-value')
    self.assertEqual(parser.get('section', 'key4'), 'default-value')
    with self.assertRaises(InterpolationMissingEnvError) as cm:
      parser.get('section', 'key3')
    if six.PY2:
      err = textwrap.dedent('''\
        Bad value substitution:
        \tsection: [section]
        \toption : key3
        \tkey    : INIHERIT_TEST_NOEXIST
        \trawval : %(ENV:INIHERIT_TEST_NOEXIST)s
      ''')
    else:
      err = (
        "Bad value substitution:"
        " option 'key3' in section 'section'"
        " contains an interpolation key 'INIHERIT_TEST_NOEXIST'"
        " which is not a valid option name."
        " Raw value: '%(ENV:INIHERIT_TEST_NOEXIST)s'"
      )
    self.assertMultiLineEqual(str(cm.exception), err)
    with self.assertRaises(InterpolationDepthError) as cm:
      parser.get('section', 'key5')
    if six.PY2:
      err = textwrap.dedent('''\
        Value interpolation too deeply recursive:
        \tsection: [section]
        \toption : key5
        \trawval : %(ENV:INIHERIT_TEST_INFLOOP)s
      ''')
    else:
      err = (
        "Recursion limit exceeded in value substitution:"
        " option 'key5' in section 'section'"
        " contains an interpolation key which cannot be substituted in 10 steps."
        " Raw value: '%(ENV:INIHERIT_TEST_INFLOOP)s'"
      )
    self.assertMultiLineEqual(str(cm.exception), err)

  #----------------------------------------------------------------------------
  def test_cascading_env_interpolate(self):
    # test that if a key contains an interpolation of another key
    # can in turn interpolate an "%(ENV:...)s" style expansion.
    files = {k: textwrap.dedent(v) for k, v in {
      'config.ini' : '''
        [DEFAULT]
        kw1 = %(kw2)s
        kw2 = %(ENV:UNDEFINED:-defval)s
      ''',
    }.items()}
    parser = ConfigParser(loader=ByteLoader(files))
    parser.read('config.ini')
    self.assertEqual(parser.get('DEFAULT', 'kw2'), 'defval')
    self.assertEqual(parser.get('DEFAULT', 'kw1'), 'defval')

  #----------------------------------------------------------------------------
  def test_subclass_override(self):
    # test that subclasses that override `ConfigParser._interpolate`,
    # but that still directly call it, works...
    class SomeOtherConfigParser(ConfigParser):
      def _interpolate(self, section, option, rawval, vars):
        return ConfigParser._interpolate(self, section, option, rawval, vars)
    files = {k: textwrap.dedent(v) for k, v in {
      'config.ini' : '''
        [DEFAULT]
        kw1 = %(kw2)s
        kw2 = %(ENV:SOMEVAL:-defval)s
      ''',
    }.items()}
    parser = SomeOtherConfigParser(loader=ByteLoader(files))
    parser.read('config.ini')
    self.assertEqual(parser.get('DEFAULT', 'kw2'), 'defval')
    self.assertEqual(parser.get('DEFAULT', 'kw1'), 'defval')


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
