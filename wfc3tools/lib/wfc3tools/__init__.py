"""The wfc3tools package holds Python tasks useful for analyzing WFC3 data.

These tasks include:

Utility and library functions used by these tasks are also included in this
module.


"""

if False :
    __version__ = ''

    __svn_version__ = 'Unable to determine SVN revision'
    __full_svn_info__ = ''
    __setup_datetime__ = None

    try:
        __version__ = __import__('pkg_resources').\
                            get_distribution('wfc3tools').version
    except:
        pass

else :
    __version__ = '1.0'

try:
    from wfc3tools.svninfo import (__svn_version__, __full_svn_info__,
                                  __setup_datetime__)
except ImportError:
    pass

import runastrodriz
import calwf3 
import wf32d
import wf3ccd
import wf3ir
import wf3rej

# These lines allow TEAL to print out the names of TEAL-enabled tasks
# upon importing this package.
import os
from stsci.tools import teal
teal.print_tasknames(__name__, os.path.dirname(__file__))