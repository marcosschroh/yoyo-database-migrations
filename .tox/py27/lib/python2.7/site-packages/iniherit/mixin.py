# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2013/08/20
# copy: (C) Copyright 2013 Cadit Health Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import six
from six.moves import configparser as CP

from .parser import IniheritMixin
from .interpolation import BasicInterpolationMixin

#------------------------------------------------------------------------------

# todo: should this perhaps use the `stub` package instead?...

raw_attrs = [attr for attr in dir(IniheritMixin) if not attr.startswith('__')]
base_attrs = ['_interpolate']
interpolation_attrs = [attr for attr in dir(BasicInterpolationMixin) if not attr.startswith('__')]

_replacements = [
  (IniheritMixin, CP.RawConfigParser,  raw_attrs),
  (IniheritMixin, CP.ConfigParser,     base_attrs),
  (IniheritMixin, CP.SafeConfigParser, base_attrs),
]

if six.PY3:
  _replacements += [
    (BasicInterpolationMixin, CP.BasicInterpolation, interpolation_attrs),
  ]

#------------------------------------------------------------------------------
def install_globally():
  '''
  Installs '%inherit'-enabled processing as the global default. Note
  that this is what one calls "dangerous". Please use with extreme
  caution.
  '''
  if hasattr(CP.RawConfigParser, '_iniherit_installed_'):
    return
  setattr(CP.RawConfigParser, '_iniherit_installed_', True)
  for source, target, attrs in _replacements:
    for attr in attrs:
      if hasattr(target, attr):
        setattr(target,
                '_iniherit_' + attr, getattr(target, attr))
      meth = getattr(source, attr)
      if six.callable(meth):
        if six.PY2:
          import new
          meth = new.instancemethod(meth.__func__, None, target)
        else:
          meth = meth.__get__(None, target)
      setattr(target, attr, meth)

#------------------------------------------------------------------------------
def uninstall_globally():
  '''
  Reverts the effects of :func:`install_globally`.
  '''
  if not hasattr(CP.RawConfigParser, '_iniherit_installed_'):
    return
  delattr(CP.RawConfigParser, '_iniherit_installed_')
  for source, target, attrs in _replacements:
    for attr in attrs:
      if hasattr(target, '_iniherit_' + attr):
        xattr = getattr(target, '_iniherit_' + attr)
        setattr(target, attr, xattr)
      else:
        delattr(target, attr)

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
