import pyfits
from pytools import irafglob, fileutil, parseinput

def parseSingleInput(f=None, ext=None):
    if isinstance(f, str):
        # create an HSTWCS object from a filename
        if ext != None:
            filename = f
            if isinstance(ext,tuple):
                if ext[0] == '':
                    extnum = ext[1] # handle ext=('',1)
                else:
                    extnum = ext
            else:
                extnum = int(ext)
        elif ext == None:
            filename, ext = fileutil.parseFilename(f)
            ext = fileutil.parseExtn(ext)
            if ext[0] == '':
                extnum = int(ext[1]) #handle ext=('',extnum)
            else:
                extnum = ext
        phdu = pyfits.open(filename)
        hdr0 = pyfits.getheader(filename)
        try:
            ehdr = pyfits.getheader(filename, ext=extnum)
        except (IndexError,KeyError):
            print 'Unable to get extension.', extnum
            raise

    elif isinstance(f, pyfits.HDUList):
        phdu = f
        if ext == None:
            extnum = 0
        else:
            extnum = ext
        ehdr = f[extnum].header
        hdr0 = f[0].header
        filename = hdr0.get('FILENAME', "")

    return filename, hdr0, ehdr, phdu


def parseMultipleInput(input):
    if isinstance(input, str):
        if input[0] == '@':
            # input is an @ file
            filelist = irafglob.irafglob(input)
        else:
            try:
                filelist, output = parseinput.parseinput(input)
            except IOError: raise
    elif isinstance(input, list):
        if isinstance(input[0], wcsutil.HSTWCS):
            # a list of HSTWCS objects
            return input
        else:
            filelist = input[:]
    return filelist