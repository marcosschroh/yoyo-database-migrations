# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2016/12/14
# copy: (C) Copyright 2016-EOT Cadit Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import re
import os

import six
from six.moves import configparser as CP

#------------------------------------------------------------------------------

if six.PY3:
  _real_BasicInterpolation              = CP.BasicInterpolation
  _real_BasicInterpolation_before_get   = CP.BasicInterpolation.before_get
else:
  _real_BasicInterpolation              = object
  _real_BasicInterpolation_before_get   = None

#------------------------------------------------------------------------------
class InterpolationMissingEnvError(CP.InterpolationMissingOptionError): pass
class InterpolationMissingSuperError(CP.InterpolationMissingOptionError): pass


#------------------------------------------------------------------------------
class BasicInterpolationMixin(object):
  def before_get(self, parser, section, option, value, defaults):
    def base_interpolate(*args, **kw):
      return _real_BasicInterpolation_before_get(parser._interpolation, *args, **kw)
    return interpolate(parser, base_interpolate, section, option, value, defaults)


#------------------------------------------------------------------------------
class IniheritInterpolation(BasicInterpolationMixin, _real_BasicInterpolation):
  # todo: rewrite this to use a more PY3-oriented approach...
  pass


#------------------------------------------------------------------------------
_env_cre = re.compile(r'%\(ENV:([^:)]+)(:-([^)]*))?\)s', flags=re.DOTALL)
_super_cre = re.compile(r'%\(SUPER(:-([^)]*))?\)s', flags=re.DOTALL)
def interpolate(parser, base_interpolate, section, option, rawval, vars):
  # todo: ugh. this should be rewritten so that it uses
  #       `BasicInterpolationMixin` so as to be more "future-proof"...
  value = rawval
  depth = CP.MAX_INTERPOLATION_DEPTH
  erepl = lambda match: _env_replace(
    match, parser, base_interpolate, section, option, rawval, vars)
  srepl = lambda match: _super_replace(
    match, parser, parser, None, section, option, rawval, vars)
  while depth and ( _env_cre.search(value) or _super_cre.search(value) ):
    depth -= 1
    value = _env_cre.sub(erepl, value)
    value = _super_cre.sub(srepl, value)
  if not depth and ( _env_cre.search(value) or _super_cre.search(value) ):
    raise CP.InterpolationDepthError(option, section, rawval)
  if '%(SUPER)s' in value:
    raise InterpolationMissingSuperError(option, section, rawval, 'SUPER')
  if base_interpolate is None:
    return value
  vars = dict(vars)
  while True:
    # ok, this is... uh... "tricky"... basically, we don't want to
    # pre-emptively expand SUPER & ENV expressions because then we may
    # trip invalid expressions that aren't actually used. thus, we
    # only expand keys that are actually requested, and we detect by
    # catching InterpolationMissingOptionError's...
    try:
      return base_interpolate(parser, section, option, value, vars)
    except CP.InterpolationMissingOptionError as err:
      for key, val in list(vars.items()):
        if err.reference.lower() in val.lower():
          newval = interpolate(parser, None, section, key, val, vars)
          if newval != val:
            vars[key] = newval
            break
      else:
        raise

#------------------------------------------------------------------------------
def interpolate_super(parser, src, dst, section, option, value):
  srepl = lambda match: _super_replace(
    match, parser, src, dst, section, option, value, None)
  value = _super_cre.sub(srepl, value)
  return value

#------------------------------------------------------------------------------
def _env_replace(match, parser, base_interpolate, section, option, rawval, vars):
  if match.group(1) in os.environ:
    return os.environ.get(match.group(1))
  if match.group(2):
    return match.group(3)
  raise InterpolationMissingEnvError(option, section, rawval, match.group(1))

#------------------------------------------------------------------------------
def _super_replace(match, parser, src, dst, section, option, rawval, vars):
  if dst \
     and ( section == parser.IM_DEFAULTSECT or dst.has_section(section) ) \
     and dst.has_option(section, option):
    try:
      return dst.get(section, option, raw=True, vars=vars)
    except TypeError:
      return dst.get(section, option)
  if dst:
    return match.group(0)
  if match.group(1):
    return match.group(2)
  raise InterpolationMissingSuperError(option, section, rawval, 'SUPER')

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
