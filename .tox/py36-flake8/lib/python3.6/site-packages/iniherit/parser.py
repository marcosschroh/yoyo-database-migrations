# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2013/08/20
# copy: (C) Copyright 2013 Cadit Health Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import io
import os.path
import warnings

import six
from six.moves import configparser as CP
from six.moves import urllib
try:
  from collections import OrderedDict
except ImportError:
  OrderedDict = dict

# TODO: PY3 added a `ConfigParser.read_dict` that should probably
#       be overridden as well...
# TODO: should `ConfigParser.set()` be checked for option==INHERITTAG?...

from . import interpolation

__all__ = (
  'Loader', 'IniheritMixin', 'RawConfigParser',
  'ConfigParser', 'SafeConfigParser',
  'DEFAULT_INHERITTAG',
)

#------------------------------------------------------------------------------

_real_RawConfigParser  = CP.RawConfigParser
_real_ConfigParser     = CP.ConfigParser
_real_SafeConfigParser = CP.SafeConfigParser

DEFAULT_INHERITTAG = '%inherit'

#------------------------------------------------------------------------------
class Loader(object):
  def load(self, name, encoding=None):
    # todo: these fp are leaked... need to use "contextlib.closing" somehow...
    if encoding is None:
      return open(name)
    return open(name, encoding=encoding)


#------------------------------------------------------------------------------
def _get_real_interpolate(parser):
  # todo: should this be sensitive to `parser`?...
  return \
    getattr(_real_ConfigParser, '_iniherit__interpolate', None) \
    or getattr(_real_ConfigParser, '_interpolate', None)

#------------------------------------------------------------------------------
# TODO: this would probably be *much* simpler with meta-classes...

#------------------------------------------------------------------------------
class IniheritMixin(object):

  IM_INHERITTAG  = DEFAULT_INHERITTAG
  IM_DEFAULTSECT = CP.DEFAULTSECT

  #----------------------------------------------------------------------------
  def __init__(self, *args, **kw):
    self.loader = kw.get('loader', None) or Loader()
    self.inherit = True
    self.IM_INHERITTAG  = DEFAULT_INHERITTAG
    self.IM_DEFAULTSECT = getattr(self, 'default_section', CP.DEFAULTSECT)

  #----------------------------------------------------------------------------
  def read(self, filenames, encoding=None):
    if isinstance(filenames, six.string_types):
      filenames = [filenames]
    read_ok = []
    for filename in filenames:
      try:
        fp = self._load(filename, encoding=encoding)
      except IOError:
        continue
      self._read(fp, filename, encoding=encoding)
      fp.close()
      read_ok.append(filename)
    return read_ok

  #----------------------------------------------------------------------------
  def _load(self, filename, encoding=None):
    if not getattr(self, 'loader', None):
      self.loader = Loader()
    return self.loader.load(filename, encoding=encoding)

  #----------------------------------------------------------------------------
  def _read(self, fp, fpname, encoding=None):
    if getattr(self, 'inherit', True) or not hasattr(self, '_iniherit__read'):
      raw = self._readRecursive(fp, fpname, encoding=encoding)
      self._apply(raw, self)
    else:
      self._iniherit__read(fp, fpname)

  #----------------------------------------------------------------------------
  def _makeParser(self, raw=True):
    ret = _real_RawConfigParser() if raw else _real_ConfigParser()
    ret.inherit = False
    ## TODO: any other configurations that need to be copied into `ret`??...
    ret.optionxform = self.optionxform
    return ret

  #----------------------------------------------------------------------------
  def _readRecursive(self, fp, fpname, encoding=None):
    ret = self._makeParser()
    src = self._makeParser()
    src.readfp(fp, fpname)
    dirname = os.path.dirname(fpname)
    if src.has_option(self.IM_DEFAULTSECT, self.IM_INHERITTAG):
      inilist = src.get(self.IM_DEFAULTSECT, self.IM_INHERITTAG)
      src.remove_option(self.IM_DEFAULTSECT, self.IM_INHERITTAG)
      inilist = self._interpolate_with_vars(
        src, self.IM_DEFAULTSECT, self.IM_INHERITTAG, inilist)
      for curname in inilist.split():
        optional = curname.startswith('?')
        if optional:
          curname = curname[1:]
        curname = os.path.join(dirname, urllib.parse.unquote(curname))
        try:
          curfp = self._load(curname, encoding=encoding)
        except IOError:
          if optional:
            continue
          raise
        self._apply(self._readRecursive(curfp, curname, encoding=encoding), ret)
    for section in src.sections():
      if not src.has_option(section, self.IM_INHERITTAG):
        continue
      inilist = src.get(section, self.IM_INHERITTAG)
      src.remove_option(section, self.IM_INHERITTAG)
      inilist = self._interpolate_with_vars(
        src, section, self.IM_INHERITTAG, inilist)
      for curname in inilist.split():
        optional = curname.startswith('?')
        if optional:
          curname = curname[1:]
        fromsect = section
        if '[' in curname and curname.endswith(']'):
          curname, fromsect = curname.split('[', 1)
          fromsect = urllib.parse.unquote(fromsect[:-1])
        curname = os.path.join(dirname, urllib.parse.unquote(curname))
        try:
          curfp = self._load(curname, encoding=encoding)
        except IOError:
          if optional:
            continue
          raise
        self._apply(self._readRecursive(curfp, curname, encoding=encoding), ret,
                    sections={fromsect: section})
    self._apply(src, ret)
    return ret

  #----------------------------------------------------------------------------
  def _apply(self, src, dst, sections=None):
    # todo: this does not detect the case that a section overrides
    #       the default section with the exact same value... ugh.
    if sections is None:
      for option, value in src.items(self.IM_DEFAULTSECT):
        value = interpolation.interpolate_super(
          self, src, dst, self.IM_DEFAULTSECT, option, value)
        self._im_setraw(dst, self.IM_DEFAULTSECT, option, value)
    if sections is None:
      sections = OrderedDict([(s, s) for s in src.sections()])
    for srcsect, dstsect in sections.items():
      if not dst.has_section(dstsect):
        dst.add_section(dstsect)
      for option, value in src.items(srcsect):
        # todo: this is a *terrible* way of detecting if this option is
        #       defaulting...
        if src.has_option(self.IM_DEFAULTSECT, option) \
            and value == src.get(self.IM_DEFAULTSECT, option):
          continue
        value = interpolation.interpolate_super(
          self, src, dst, dstsect, option, value)
        self._im_setraw(dst, dstsect, option, value)

  #----------------------------------------------------------------------------
  def _im_setraw(self, parser, section, option, value):
    if six.PY3 and hasattr(parser, '_interpolation'):
      # todo: don't do this for systems that have
      #       http://bugs.python.org/issue21265 fixed
      try:
        tmp = parser._interpolation.before_set
        parser._interpolation.before_set = lambda self,s,o,v,*a,**k: v
        _real_RawConfigParser.set(parser, section, option, value)
      finally:
        parser._interpolation.before_set = tmp
    else:
      _real_RawConfigParser.set(parser, section, option, value)

  #----------------------------------------------------------------------------
  def _interpolate_with_vars(self, parser, section, option, rawval):
    ## TODO: ugh. this just doesn't feel "right"...
    try:
      vars = dict(parser.items(section, raw=True))
    except:
      vars = dict(parser.items(section))
    if not isinstance(parser, _real_ConfigParser):
      parser = self._makeParser(raw=False)
    base_interpolate = _get_real_interpolate(parser)
    return interpolation.interpolate(
      parser, base_interpolate, section, option, rawval, vars)

  #----------------------------------------------------------------------------
  # todo: yikes! overriding a private method!...
  def _interpolate(self, section, option, rawval, vars):
    base_interpolate = _get_real_interpolate(self)
    return interpolation.interpolate(
      self, base_interpolate, section, option, rawval, vars)
  if not hasattr(_real_ConfigParser, '_interpolate') and not six.PY3:
    warnings.warn(
      'ConfigParser did not have a "_interpolate" method'
      ' -- iniherit may be broken on this platform',
      RuntimeWarning)


#------------------------------------------------------------------------------
# todo: i'm a little worried about the diamond inheritance here...
class RawConfigParser(IniheritMixin, _real_RawConfigParser):
  _DEFAULT_INTERPOLATION = interpolation.IniheritInterpolation()
  def __init__(self, *args, **kw):
    loader = kw.pop('loader', None)
    IniheritMixin.__init__(self, loader=loader)
    _real_RawConfigParser.__init__(self, *args, **kw)
class ConfigParser(RawConfigParser, _real_ConfigParser):
  def __init__(self, *args, **kw):
    loader = kw.pop('loader', None)
    RawConfigParser.__init__(self, loader=loader)
    _real_ConfigParser.__init__(self, *args, **kw)
class SafeConfigParser(ConfigParser, _real_SafeConfigParser):
  def __init__(self, *args, **kw):
    loader = kw.pop('loader', None)
    ConfigParser.__init__(self, loader=loader)
    _real_SafeConfigParser.__init__(self, *args, **kw)


#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
