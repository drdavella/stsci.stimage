import numpy as np
from matplotlib import pyplot as plt
import pyfits
import string

from pytools import parseinput, irafglob
from stwcs.distortion import utils
from stwcs import updatewcs, wcsutil
from stwcs.wcsutil import altwcs

def vmosaic(fnames, ext=None, extname=None, undistort=True, wkey='V', wname='VirtualMosaic', plot=False, clobber=False):
    """
    Create a virtual mosaic using the WCS of the input images.
    
    Parameters
    ----------
    fnames: a string or a list 
              a string or a list of filenames, or a list of wcsutil.HSTWCS objects
    ext:    an int, a tuple or a list
              an int - represents a FITS extension, e.g. 0 is the primary HDU
              a tuple - uses the notation (extname, extver), e.g. ('sci',1)
              Can be a list of integers or tuples representing FITS extensions
    extname: string
              the value of the EXTNAME keyword for the extensions to be used in the mosaic
    undistort: boolean (default: True)
               undistort (or not) the output WCS
    wkey:   string
              default: 'V'
              one character A-Z to be used to record the virtual mosaic WCS as 
              an alternate WCS in the headers of the input files.
    wname:  string
              default: 'VirtualMosaic
              a string to be used as a WCSNAME value for the alternate WCS representign 
              the virtual mosaic
    plot:   boolean
              if True and matplotlib is installed will make a plot of the tangent plane
              and the location of the input observations.
    clobber: boolean
              This covers the case when an alternate WCS with the requested key 
              already exists in the header of the input files.
              if clobber is True, it will be overwritten
              if False, it will compute the new one but will not write it to the headers.
              
    Notes
    -----
    The algorithm is:
    1. The output WCS is calculated based on the input WCSes.
       The first image is used as a reference, if no reference is given.
       This represents the virtual mosaic WCS
    2. For each input observation/chip, an HSTWCS object is created
       and its footprint on the sky is calculated (using only the four corners).
    3. For each input observation the footprint is projected on the output 
       tangent plane and the virtual WCS is recorded in the header.
    """
    wcsobjects = readWCS(fnames, ext, extname)
    outwcs = utils.output_wcs(wcsobjects, undistort=undistort)
    if plot:
        outc=np.array([[0.,0], [outwcs.naxis1,0], 
                             [outwcs.naxis1, outwcs.naxis2], 
                             [0,outwcs.naxis2], [0,0]])
        plt.plot(outc[:,0], outc[:,1])
    
    for wobj in wcsobjects:
        outcorners = outwcs.wcs_sky2pix(wobj.calcFootprint(),1)
        if plot:
            plt.plot(outcorners[:,0], outcorners[:,1])
            objwcs = outwcs.deepcopy()
        objwcs.wcs.crpix = objwcs.wcs.crpix - (outcorners[0])
        updatehdr(wobj.filename, objwcs,wkey=wkey, wcsname=wname, ext=wobj.extname, clobber=clobber)
    return outwcs

def updatehdr(fname, wcsobj, wkey, wcsname, ext=1, clobber=False):
    hdr = pyfits.getheader(fname, ext=ext)
    all_keys = list(string.ascii_uppercase)
    if wkey.upper() not in all_keys:
        raise KeyError, "wkey must be one character: A-Z"
    if wkey not in altwcs.available_wcskeys(hdr):
        if not clobber:
            raise ValueError, "wkey %s is already in use. Use clobber=True to overwrite it or specify a different key." %wkey
        else:
            altwcs.deleteWCS(fname, ext=ext, wcskey='V')
    f = pyfits.open(fname, mode='update')
    
    hwcs = wcs2header(wcsobj, wkey,wcsname).ascardlist()
    hdr = f[ext].header
    hdr.ascardlist().extend(hwcs)
    f.close()
    
def wcs2header(wcsobj, wkey='V', wname='VirtualMosaic'):
    
    h = wcsobj.to_header()
    wcsnamekey = 'WCSNAME' + wkey
    h.update(key=wcsnamekey, value=wname)
    if wcsobj.wcs.has_cd():
        altwcs.pc2cd(h)
    for k in h.keys():
        key = k[:7] + wkey
        h.update(key=key, value=h[k])
    norient = np.rad2deg(np.arctan2(h['CD1_2'],h['CD2_2']))
    okey = 'ORIENT%s' % wkey
    h.update(key=okey, value=norient) 
    #print h
    return h

def readWCS(input, exts=None, extname=None):
    if isinstance(input, str):
        if input[0] == '@':
            # input is an @ file
            filelist = irafglob.irafglob(input)
        else:
            try:
                filelist, output = parseinput.parseinput(input)
            except IOError: raise
    elif isinstance(input, list):
        if isinstance(input[0], str):
            # a list of file names
            try:
                filelist, output = parseinput.parseinput(input)
            except IOError: raise
        elif isinstance(input[0], wcsutil.HSTWCS):
            # a list of HSTWCS objects
            return input
    wcso = []
    fomited = []
    # figure out which FITS extension(s) to use 
    if exts == None and extname == None:
        #Assume it's simple FITS and the data is in the primary HDU
        for f in filelist:
            try:
                wcso = wcsutil.HSTWCS(f)
            except AttributeError:
                fomited.append(f)
                continue
    elif exts != None and validateExt(exts):
        exts = [exts]
        for f in filelist:
            try:
                wcso.extend([wcsutil.HSTWCS(f, ext=e) for e in exts])
            except KeyError:
                fomited.append(f)
                continue
    elif extname != None:
        for f in filelist:
            fobj = pyfits.open(f)
            for i in range(len(fobj)):
                try:
                    ename = fobj[i].header['EXTNAME']
                except KeyError:
                    continue
                if ename.lower() == extname.lower():
                    wcso.append(wcsutil.HSTWCS(f,ext=i))
                else:
                    continue
            fobj.close()
    if fomited != []:
        print "These files were skipped:"
        for f in fomited:
            print f
    return wcso
    
    
def validateExt(ext):
    if not isinstance(ext, int) and not isinstance(ext, tuple) \
       and not isinstance(ext, list):
        print "Ext must be integer, tuple, a list of int extension numbers, \
        or a list of tuples representing a fits extension, for example ('sci', 1)."
        return False
    else:
        return True


        