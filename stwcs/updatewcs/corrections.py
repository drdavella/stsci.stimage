from __future__ import division # confidence high

import datetime
import numpy as np
from numpy import linalg
from pytools import fileutil
from stwcs.utils import diff_angles
import makewcs, dgeo

MakeWCS = makewcs.MakeWCS
DGEOCorr = dgeo.DGEOCorr

class TDDCorr(object):
    """
    Purpose
    =======
    Apply time dependent distortion correction to SIP coefficients and basic
    WCS keywords. It is applicable only to ACS/WFC data.
    
    Ref: Jay Anderson, ACS ISR 2007-08, Variation of the Distortion 
    Solution of the WFC 
    
    :Parameters:
    `ext_wcs`: HSTWCS object
            An extension HSTWCS object to be modified
    `ref_wcs`: HSTWCS object
             A reference HSTWCS object
    """
    
    def updateWCS(cls, ext_wcs, ref_wcs):
        """
        - Calculates alpha and beta for ACS/WFC data.
        - Writes 2 new kw to the extension header: TDDALPHA and TDDBETA
        """
        
        alpha, beta = cls.compute_alpha_beta(ext_wcs)
        cls.apply_tdd2idc(ref_wcs, alpha, beta)
        cls.apply_tdd2idc(ext_wcs, alpha, beta)
        ext_wcs.idcmodel.refpix['TDDALPHA'] = alpha
        ext_wcs.idcmodel.refpix['TDDBETA'] = beta
        ref_wcs.idcmodel.refpix['TDDALPHA'] = alpha
        ref_wcs.idcmodel.refpix['TDDBETA'] = beta
        
        newkw = {'TDDALPHA': alpha, 'TDDBETA':beta, 'OCX10':ext_wcs.idcmodel.cx[1,0],
                'OCX11':ext_wcs.idcmodel.cx[1,1],'OCY10':ext_wcs.idcmodel.cy[1,0],
                'OCY11':ext_wcs.idcmodel.cy[1,1],}
        
        return newkw
    updateWCS = classmethod(updateWCS)
    
    def apply_tdd2idc(cls, hwcs, alpha, beta):
        """
        Applies TDD to the idctab coefficients of a ACS/WFC observation.
        This should be always the first correction.
        """
        theta_v2v3 = 2.234529
        mrotp = fileutil.buildRotMatrix(theta_v2v3)
        mrotn = fileutil.buildRotMatrix(-theta_v2v3)
        tdd_mat = np.array([[1+(beta/2048.), alpha/2048.],[alpha/2048.,1-(beta/2048.)]],np.float64)
        abmat1 = np.dot(tdd_mat, mrotn)
        abmat2 = np.dot(mrotp,abmat1)
        xshape, yshape = hwcs.idcmodel.cx.shape, hwcs.idcmodel.cy.shape
        icxy = np.dot(abmat2,[hwcs.idcmodel.cx.ravel(), hwcs.idcmodel.cy.ravel()])
        hwcs.idcmodel.cx = icxy[0]
        hwcs.idcmodel.cy = icxy[1]
        hwcs.idcmodel.cx.shape = xshape
        hwcs.idcmodel.cy.shape = yshape
        
    apply_tdd2idc = classmethod(apply_tdd2idc)
        
    def compute_alpha_beta(cls, ext_wcs):
        """
        Compute the ACS time dependent distortion skew terms
        as described in ACS ISR 07-08 by J. Anderson.
        
        Jay's code only computes the alpha/beta values based on a decimal year
        with only 3 digits, so this line reproduces that when needed for comparison
        with his results.
        rday = float(('%0.3f')%rday)
        
        The zero-point terms account for the skew accumulated between
        2002.0 and 2004.5, when the latest IDCTAB was delivered.
        alpha = 0.095 + 0.090*(rday-dday)/2.5
        beta = -0.029 - 0.030*(rday-dday)/2.5
        """
        skew_coeffs = ext_wcs.idcmodel.refpix['skew_coeffs']
        if skew_coeffs is None:
            err_str =  "------------------------------------------------------------------------  \n"
            err_str += "WARNING: the IDCTAB geometric distortion file specified in the image      \n"
            err_str += "         header did not have the time-dependent distortion coefficients.  \n"
            err_str += "         The pre-SM4 time-dependent skew solution will be used by default.\n"
            err_str += "         Please update IDCTAB with new reference file from HST archive.   \n"
            err_str +=  "------------------------------------------------------------------------  \n"
            print err_str
            # Using default pre-SM4 coefficients
            skew_coeffs = {'TDD_A':[0.095,0.090/2.5],
                        'TDD_B':[-0.029,-0.030/2.5],
                        'TDD_DATE':2004.5,'TDDORDER':1}
        
        if not isinstance(ext_wcs.date_obs,float):
            year,month,day = ext_wcs.date_obs.split('-')
            rdate = datetime.datetime(int(year),int(month),int(day))
            rday = float(rdate.strftime("%j"))/365.25 + rdate.year
        else:
            rday = ext_wcs.date_obs
        
        alpha = 0
        beta = 0
        # Compute skew terms, allowing for non-linear coefficients as well
        for c in range(skew_coeffs['TDDORDER']+1):
            alpha += skew_coeffs['TDD_A'][c]* np.power((rday-skew_coeffs['TDD_DATE']),c)
            beta += skew_coeffs['TDD_B'][c]*np.power((rday-skew_coeffs['TDD_DATE']),c)
            
        return alpha,beta
    compute_alpha_beta = classmethod(compute_alpha_beta)
    
        
class VACorr(object):
    """
    Purpose
    =======
    Apply velocity aberation correction to WCS keywords.
    Modifies the CD matrix and CRVAL1/2

    """
    
    def updateWCS(cls, ext_wcs, ref_wcs):
        if ext_wcs.vafactor != 1:
            ext_wcs.wcs.cd = ext_wcs.wcs.cd * ext_wcs.vafactor
            ext_wcs.wcs.crval[0] = ref_wcs.wcs.crval[0] + ext_wcs.vafactor*diff_angles(ext_wcs.wcs.crval[0], ref_wcs.wcs.crval[0]) 
            ext_wcs.wcs.crval[1] = ref_wcs.wcs.crval[1] + ext_wcs.vafactor*diff_angles(ext_wcs.wcs.crval[1], ref_wcs.wcs.crval[1]) 
            ext_wcs.wcs.set()
        else:
            pass
        kw2update={'CD1_1': ext_wcs.wcs.cd[0,0], 'CD1_2':ext_wcs.wcs.cd[0,1], 
                    'CD2_1':ext_wcs.wcs.cd[1,0], 'CD2_2':ext_wcs.wcs.cd[1,1], 
                    'CRVAL1':ext_wcs.wcs.crval[0], 'CRVAL2':ext_wcs.wcs.crval[1]}    
        return kw2update
    
    updateWCS = classmethod(updateWCS)

        
class CompSIP(object):
    """
    Purpose
    =======
    Compute SIP coefficients from idc table coefficients.
    """
    
    def updateWCS(cls, ext_wcs, ref_wcs):
        kw2update = {}
        order = ext_wcs.idcmodel.norder
        kw2update['A_ORDER'] = order
        kw2update['B_ORDER'] = order
        pscale = ext_wcs.idcmodel.refpix['PSCALE']
        
        cx = ext_wcs.idcmodel.cx
        cy = ext_wcs.idcmodel.cy
        
        matr = np.array([[cx[1,1],cx[1,0]], [cy[1,1],cy[1,0]]], dtype=np.float64)
        imatr = linalg.inv(matr)
        akeys1 = np.zeros((order+1,order+1), dtype=np.float64)
        bkeys1 = np.zeros((order+1,order+1), dtype=np.float64)
        for n in range(order+1):
            for m in range(order+1):
                if n >= m and n>=2:
                    idcval = np.array([[cx[n,m]],[cy[n,m]]])
                    sipval = np.dot(imatr, idcval)
                    akeys1[m,n-m] = sipval[0]
                    bkeys1[m,n-m] = sipval[1]
                    Akey="A_%d_%d" % (m,n-m)
                    Bkey="B_%d_%d" % (m,n-m)
                    kw2update[Akey] = sipval[0,0]
                    kw2update[Bkey] = sipval[1,0]
        kw2update['CTYPE1'] = 'RA---TAN-SIP'
        kw2update['CTYPE2'] = 'DEC--TAN-SIP'
        return kw2update
    
    updateWCS = classmethod(updateWCS)


