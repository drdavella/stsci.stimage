import os
import pyfits
import time
from pytools import fileutil
import os.path

#Note: The order of corrections is important

__docformat__ = 'restructuredtext'

# A dictionary which lists the allowed corrections for each instrument.
# These are the default corrections applied also in the pipeline.

allowed_corrections={'WFPC2': ['DET2IMCorr', 'MakeWCS','CompSIP', 'VACorr'],
                    'ACS': ['DET2IMCorr', 'TDDCorr', 'MakeWCS', 'CompSIP','VACorr', 'DGEOCorr'],
                    'STIS': ['MakeWCS', 'CompSIP','VACorr'],
                    'NICMOS': ['MakeWCS', 'CompSIP','VACorr'],
                    'WFC3': ['MakeWCS', 'CompSIP','VACorr'],
                    }

cnames = {'DET2IMCorr': 'Detector to Image Correction',
         'TDDCorr': 'Time Dependent Distortion Correction',
         'MakeWCS': 'Recalculate basic WCS keywords based on the distortion model',
         'CompSIP': 'Given IDCTAB distortion model calculate the SIP coefficients',
         'VACorr':  'Velocity Aberration Correction',
         'DGEOCorr': 'Lookup Table Distortion'
         }
                            
def setCorrections(fname, vacorr=True, tddcorr=True, dgeocorr=True, d2imcorr=True):
    """
    Purpose
    =======
    Creates a list of corrections to be applied to a file.
    based on user input paramters and allowed corrections
    for the instrument.
    """
    instrument = pyfits.getval(fname, 'INSTRUME')
    # make a copy of this list !
    acorr = allowed_corrections[instrument][:]
    
    # Check if idctab is present on disk
    # If kw IDCTAB is present in the header but the file is 
    # not found on disk, do not run TDDCorr, MakeCWS and CompSIP
    if not foundIDCTAB(fname):
        acorr.remove('TDDCorr')
        acorr.remove('MakeWCS')
        acorr.remove('CompSIP')   
    
    if 'VACorr' in acorr and vacorr==False:  acorr.remove('VACorr')
    if 'TDDCorr' in acorr:
        tddcorr = applyTDDCorr(fname, tddcorr)
        if tddcorr == False: acorr.remove('TDDCorr')
        
    if 'DGEOCorr' in acorr:
        dgeocorr = applyDgeoCorr(fname, dgeocorr)
        if dgeocorr == False: acorr.remove('DGEOCorr')
    if 'DET2IMCorr' in acorr:
        d2imcorr = applyD2ImCorr(fname, d2imcorr)
        if d2imcorr == False: acorr.remove('DET2IMCorr')
    print acorr
    return acorr

def foundIDCTAB(fname):
    idctab_found = True
    try:
        idctab = fileutil.osfn(pyfits.getval(fname, 'IDCTAB'))
        if idctab == 'N/A' or idctab == "": 
            idctab_found = False
        if os.path.exists(idctab):
            idctab_found = True
        else:
            idctab_found = False
    except KeyError:
        idctab_found = False
    return idctab_found
   
def applyTDDCorr(fname, utddcorr):
    """
    The default value of tddcorr for all ACS images is True.
    This correction will be performed if all conditions below are True:
    - the user did not turn it off on the command line
    - the detector is WFC
    - the idc table specified in the primary header is available.
    """
    instrument = pyfits.getval(fname, 'INSTRUME')
    try:
        detector = pyfits.getval(fname, 'DETECTOR')
    except KeyError:
        detector = None
    try:
        tddswitch = pyfits.getval(fname, 'TDDCORR')
    except KeyError:
        tddswitch = 'PERFORM'
        
    if instrument == 'ACS' and detector == 'WFC' and utddcorr == True and tddswitch == 'PERFORM':
        tddcorr = True
        try:
            idctab = pyfits.getval(fname, 'IDCTAB')    
        except KeyError:
            tddcorr = False
            #print "***IDCTAB keyword not found - not applying TDD correction***\n"
        if os.path.exists(fileutil.osfn(idctab)):
            tddcorr = True
        else:
            tddcorr = False
            #print "***IDCTAB file not found - not applying TDD correction***\n"
    else: 
        tddcorr = False

    return tddcorr

def applyDgeoCorr(fname, udgeocorr):
    """
    Purpose
    =======
    Adds dgeo extensions to files based on the DGEOFILE keyword in the primary 
    header. This is a default correction and will always run in the pipeline.
    The file used to generate the extensions is 
    recorded in the DGEOEXT keyword in each science extension.
    If 'DGEOFILE' in the primary header is different from 'DGEOEXT' in the 
    extension header and the file exists on disk and is a 'new type' dgeofile, 
    then the dgeo extensions will be updated.
    """
    applyDGEOCorr = True
    try:
        # get DGEOFILE kw from primary header
        fdgeo0 = pyfits.getval(fname, 'DGEOFILE')
        if fdgeo0 == 'N/A':
            return False
        fdgeo0 = fileutil.osfn(fdgeo0)
        if not fileutil.findFile(fdgeo0):
            print 'Kw DGEOFILE exists in primary header but file %s not found\n' % fdgeo0
            print 'DGEO correction will not be applied\n'
            applyDGEOCorr = False
            return applyDGEOCorr 
        try:
            # get DGEOEXT kw from first extension header
            fdgeo1 = pyfits.getval(fname, 'DGEOEXT', ext=1)
            fdgeo1 = fileutil.osfn(fdgeo1)
            if fdgeo1 and fileutil.findFile(fdgeo1):
                if fdgeo0 != fdgeo1:
                    applyDGEOCorr = True
                else:
                    applyDGEOCorr = False
            else: 
                # dgeo file defined in first extension may not be found
                # but if a valid kw exists in the primary header, dgeo should be applied.
                applyDGEOCorr = True
        except KeyError:
            # the case of DGEOFILE kw present in primary header but DGEOEXT missing 
            # in first extension header
            applyDGEOCorr = True
    except KeyError:
        print 'DGEOFILE keyword not found in primary header'
        applyDGEOCorr = False
        return applyDGEOCorr 
    
    if isOldStyleDGEO(fname, fdgeo0):
            applyDGEOCorr = False       
    return (applyDGEOCorr and udgeocorr)

def isOldStyleDGEO(fname, dgname):
    # checks if the file defined in a DGEOFILE kw is a full size 
    # (old style) image
    
    sci_naxis1 = pyfits.getval(fname, 'NAXIS1', ext=1)
    sci_naxis2 = pyfits.getval(fname, 'NAXIS2', ext=1)
    dg_naxis1 = pyfits.getval(dgname, 'NAXIS1', ext=1)
    dg_naxis2 = pyfits.getval(dgname, 'NAXIS2', ext=1)
    if sci_naxis1 <= dg_naxis1 or sci_naxis2 <= dg_naxis2:
        print 'Only full size (old style) XY file was found.'
        print 'DGEO correction will not be applied.\n'
        return True
    else:
        return False
    
def applyD2ImCorr(fname, d2imcorr):
    applyD2IMCorr = True
    try:
        # get DGEOFILE kw from primary header
        fd2im0 = pyfits.getval(fname, 'D2IMFILE')
        if fd2im0 == 'N/A':
            return False
        fd2im0 = fileutil.osfn(fd2im0)
        if not fileutil.findFile(fd2im0):
            print 'Kw D2IMFILE exists in primary header but file %s not found\n' % fd2im0
            print 'DGEO correction will not be applied\n'
            applyD2IMCorr = False
            return applyD2IMCorr 
        try:
            # get DGEOEXT kw from first extension header
            fd2imext = pyfits.getval(fname, 'D2IMEXT', ext=1)
            fd2imext = fileutil.osfn(fd2imext)
            if fd2imext and fileutil.findFile(fd2imext):
                if fd2im0 != fd2imext:
                    applyD2IMCorr = True
                else:
                    applyD2IMCorr = False
            else: 
                # dgeo file defined in first extension may not be found
                # but if a valid kw exists in the primary header, dgeo should be applied.
                applyD2IMCorr = True
        except KeyError:
            # the case of DGEOFILE kw present in primary header but DGEOEXT missing 
            # in first extension header
            applyD2IMCorr = True
    except KeyError:
        print 'D2IMFILE keyword not found in primary header'
        applyD2IMCorr = False
        return applyD2IMCorr 
    