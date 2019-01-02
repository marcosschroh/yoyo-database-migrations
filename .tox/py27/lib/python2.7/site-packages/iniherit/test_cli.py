# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <grabner@cadit.com>
# date: 2014/04/15
# copy: (C) Copyright 2014-EOT Cadit Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import unittest
import six

from .cli import flatten

#------------------------------------------------------------------------------
class TestIniheritCli(unittest.TestCase):

  #----------------------------------------------------------------------------
  def test_optionKeyCaseStaysConstant(self):
    src = '''\
[app]
someURL = http://example.com/PATH

'''

    buf = six.StringIO()
    flatten(six.StringIO(src), buf)
    out = buf.getvalue()

    self.assertMultiLineEqual(out, src)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
