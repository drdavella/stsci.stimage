import numarray as N

import pytools.imagestats
from pytools.imagestats import ImageStats

class StaticMask:
    """
    This class manages the creation of the global static mask which
    masks pixels which are negative in the SCI array.
    A static mask numarray object gets created for each global
    mask needed, one for each chip from each instrument/detector.
    Each static mask array has type Int16, and resides in memory.

    The parameter 'badval' defaults to 64 and represents the
    DQ value used to mark pixels flagged as bad by this mask.

    The parameter 'goodval' defaults to 1.0 and represents the
    pixel value of the good pixels in any user-supplied static
    mask file.

    """
    def __init__ (self, badval=64, goodval=1.0, staticsig= 3.0):

        # For now, we don't use badval. It is supposed to
        # be used to flag back the DQ array of the input
        # images. This may lead to confusion when running
        # the task repeatedly over a set of images, whenever
        # additional images are included in the set each
        # time.
        
        self.static_sig = staticsig
        self.static_badval = badval
        self.static_goodval = goodval

        self.masklist = {}

    def addMember(self,sci_arr,signature):
        """
        Combines the input image with the static mask that
        has the same signature.  The signature parameter
        consists of the tuple:
        (instrument/detector, (nx,ny), chip_id)
        """
        # If this is a new signature, create a new Static Mask file
        if not self.masklist.has_key(signature):
            self.masklist[signature] = self._buildMaskArray(signature)

        # Operate on input image DQ array to flag 'bad' pixels in the
        # global static mask
        _stats = ImageStats(sci_arr,nclip=3,fields='mode')
        mode = _stats.mode
        rms  = _stats.stddev
        del _stats

        print('  mode = %9f;   rms = %7f')  %  (mode,rms)
        #
        # The scale value (3.0) could potentially become a useful 
        # user settable parameter.  Consider for future revisions.
        # 29-April-2004 WJH/CJH/AMK
        #
        sky_rms_diff = mode - (self.static_sig*rms)

        N.bitwise_and(self.masklist[signature],N.logical_not(N.less( sci_arr, sky_rms_diff)),self.masklist[signature])

    def _buildMaskArray(self,signature):
        """ Creates numarray array for static mask array signature. """
        return N.ones(signature[1],N.Int16)

    def getMask(self,signature):
        """ Returns the appropriate StaticMask array for the image. """
        if self.masklist.has_key(signature):
            _mask =  self.masklist[signature]
        else:
            _mask = None
        return _mask

    def applyStaticFile(self, static_mask, signature):
        """
        Applies the user-supplied static file to the StaticMask array.
        This static mask array should correspond to the chip that
        this object applies to.
        """
        #
        # If an input static mask file has been specified, then combine it
        # with the data quality array.
        #
        self.masklist[signature] = N.where( N.equal( \
                static_mask, self.static_goodval), \
                self.masklist[signature],self.static_badval)

    def delete(self):
        """ Deletes all static mask objects. """

        for key in self.masklist.keys():
            self.masklist[key] = None
        self.masklist = {}
