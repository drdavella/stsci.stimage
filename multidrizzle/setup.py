from distutils.core import setup, Extension
import numarray
from numarray.numarrayext import NumarrayExtension
import sys

if not hasattr(sys, 'version_info') or sys.version_info < (2,3,0,'alpha',0):
    raise SystemExit, "Python 2.3 or later required to build multidrizzle."

def dolocal():
    """Adds a command line option --local=<install-dir> which is an abbreviation for
    'put all of multidrizzle in <install-dir>/multidrizzle'."""
    if "--help" in sys.argv:
        print >>sys.stderr
        print >>sys.stderr, " options:"
        print >>sys.stderr, "--local=<install-dir>    same as --install-lib=<install-dir>"
    for a in sys.argv:
        if a.startswith("--local="):
            dir = a.split("=")[1]
            sys.argv.extend([
                "--install-lib="+dir,
                ])
            sys.argv.remove(a)

def getExtensions():
    ext = None                   
    return ext


def dosetup(ext):
    r = setup(name = "multidrizzle",
              version = "2.0.0",
              description = "Automated process for HST image combination and cosmic-ray rejection",
              author = "Warren Hack, Christopher Hanley, Ivo Busko, Robert Jedrzejewski, and Anton Koekemoer",
              author_email = "help@stsci.edu",
              license = "http://www.stsci.edu/resources/software_hardware/pyraf/LICENSE",
              platforms = ["Linux","Solaris","Mac OS X"],
              packages=['multidrizzle'],
              package_dir={'multidrizzle':'lib'},
              ext_modules=ext)
    return r


def main():
    args = sys.argv
    dolocal()
    ext = getExtensions()
    dosetup(ext)


if __name__ == "__main__":
    main()

