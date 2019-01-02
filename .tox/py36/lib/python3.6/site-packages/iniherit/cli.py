# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2013/08/26
# copy: (C) Copyright 2013 Cadit Health Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import sys, os, logging, time, argparse, gettext
import six

import iniherit, iniherit.parser

log = logging.getLogger(__name__)

# todo: reading from 'STDIN' and watching results in an unexpected
#       behavior: if reading from a real pipe, it comes up as empty the
#       non-first time. if reading from tty, you need to re-type the
#       data... it should probably buffer it!

#------------------------------------------------------------------------------
def isstr(obj):
  return isinstance(obj, six.string_types)

#------------------------------------------------------------------------------
def _(message, *args, **kw):
  if args or kw:
    return gettext.gettext(message).format(*args, **kw)
  return gettext.gettext(message)

#------------------------------------------------------------------------------
class WatchingLoader(iniherit.Loader):
  def __init__(self, options):
    self.options = options
    self.files   = set()
  def load(self, name, encoding):
    log.debug(_('loading file "%s"'), name)
    self.files.add(name)
    return iniherit.Loader.load(self, name, encoding)

#------------------------------------------------------------------------------
def flatten(input, output, loader=None):
  cfg = iniherit.RawConfigParser(loader=loader)
  cfg.optionxform = str
  if isstr(input):
    cfg.read(input)
  else:
    cfg.readfp(input)
  out = iniherit.parser.CP.RawConfigParser()
  out.optionxform = str
  cfg._apply(cfg, out)
  if not isstr(output):
    out.write(output)
  else:
    with open(output, 'wb') as fp:
      out.write(fp)

#------------------------------------------------------------------------------
def getFilestats(files):
  # todo: perhaps use an md5 checksum instead?...
  ret = dict()
  for filename in files:
    try:
      stat = os.stat(filename)
      if stat:
        mtime = stat.st_mtime
      else:
        mtime = None
    except (OSError, IOError):
      mtime = None
    ret[filename] = mtime
  return ret

#------------------------------------------------------------------------------
def run(options):
  try:
    while True:
      loader = WatchingLoader(options)
      flatten(options.input, options.output, loader)
      if not options.watch:
        return 0
      filestats = getFilestats(loader.files)
      changed = set()
      while True:
        time.sleep(options.interval)
        log.debug(_('checking for changes...'))
        newstats = getFilestats(loader.files)
        for k, v in filestats.items():
          if newstats.get(k) != v:
            changed.add(k)
        if len(changed) > 0:
          break
      if len(changed) == 1:
        log.info(_('"%s" changed; updating output...'), list(changed)[0])
      else:
        log.info(_('%d files changed; updating output...'), len(changed))
      continue
  except KeyboardInterrupt:
    return 0

#------------------------------------------------------------------------------
def main(argv=None):

  cli = argparse.ArgumentParser(
    description = _(
      'Flatten inherited attributes in INI files. With the "--watch"'
      ' option, all input files can also be monitored for changes, and'
      ' any change will cause the output file to be automatically'
      ' updated.'
      )
    )

  cli.add_argument(
    _('-v'), _('--verbose'),
    dest='verbose', action='count', default=0,
    help=_('increase verbosity (can be specified multiple times)'))

  cli.add_argument(
    _('-w'), _('--watch'),
    dest='watch', action='store_true', default=False,
    help=_('watch all input files for changes and automatically'
           ' generate a new output file when a change is detected'
           ' (only useful when used with "--output")'))

  cli.add_argument(
    _('-i'), _('--watch-interval'),
    dest='interval', type=float, default=2.0,
    help=_('number of seconds (with decimal precision)'
           ' to wait between checks for changes (only useful when'
           ' used with "--watch") [defaults to %(default)s]'))

  cli.add_argument(
    metavar=_('INPUT'),
    dest='input', nargs='?', default=sys.stdin,
    help=_('set input filename; if unspecified or "-", reads input'
           ' from STDIN, in which case all inherits are taken relative'
           ' to the current working directory.'))

  cli.add_argument(
    metavar=_('OUTPUT'),
    dest='output', nargs='?', default=sys.stdout,
    help=_('set output filename; if unspecified or "-", writes output'
           ' to STDOUT.'))

  options = cli.parse_args(argv)

  if options.input == '-':
    options.input = sys.stdin

  if options.output == '-':
    options.output = sys.stdout

  if options.verbose > 0:
    logging.basicConfig()
    rootlog = logging.getLogger()
    if options.verbose == 1:
      rootlog.setLevel(logging.INFO)
    elif options.verbose > 1:
      rootlog.setLevel(logging.DEBUG)

  return run(options)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
