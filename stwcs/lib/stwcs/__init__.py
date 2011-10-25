""" STWCS

This package provides support for WCS based distortion models and coordinate
transformation. It relies on PyWCS (based on WCSLIB). It consists of two
subpackages:  updatewcs and wcsutil.

updatewcs performs corrections to the
basic WCS and includes other distortion infomation in the science files as
header keywords or file extensions.

Wcsutil provides an HSTWCS object which extends pywcs.WCS object and provides
HST instrument specific information as well as methods for coordinate
transformation. wcsutil also provides functions for manipulating alternate WCS
descriptions in the headers.

"""
from __future__ import division # confidence high
import os

import distortion
import pywcs
from stsci.tools import fileutil
from stsci.tools import teal

__docformat__ = 'restructuredtext'

if False :
    __version__ = ''
    __svn_version = ''
    __full_svn_info__ = ''
    __setup_datetime__ = None

    try:
        __version__ = __import__('pkg_resources').get_distribution('stwcs').version
    except:
        pass
else :
    __version__ = '0.9.1'


try:
    from stwcs.svninfo import (__svn_version__, __full_svn_info__,
                               __setup_datetime__)
except ImportError:
    __svn_version__ = 'Unable to determine SVN revision'

try:
    import gui
    teal.print_tasknames(gui.__name__, os.path.dirname(gui.__file__))
    print '\n'
except:
    print 'No TEAL-based tasks available for this package!'
