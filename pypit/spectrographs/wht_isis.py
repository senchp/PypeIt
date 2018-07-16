""" Module for Shane/Kast specific codes
"""
from __future__ import absolute_import, division, print_function

try:
    basestring
except NameError:  # For Python 3
    basestring = str

import glob

import numpy as np

from pypit import msgs
from pypit.par.pypitpar import DetectorPar
from pypit.spectrographs import spectrograph
from pypit import telescopes
from pypit.par import pypitpar
from pypit.core import arsort

from pypit import ardebug as debugger

class WhtIsisSpectrograph(spectrograph.Spectrograph):
    """
    Child to handle Shane/Kast specific code
    """

    def __init__(self):
        super(WhtIsisSpectrograph, self).__init__()
        self.spectrograph = 'NULL'
        self.telescope = telescopes.WHTTelescopePar()

class WhtIsisBlueSpectrograph(WhtIsisSpectrograph):
    """
    Child to handle WHT/ISIS blue specific code
    """
    def __init__(self):
        # Get it started
        super(WhtIsisBlueSpectrograph, self).__init__()
        self.spectrograph = 'wht_isis_blue'
        self.camera = 'ISISb'
        self.detector = [
                # Detector 1
                DetectorPar(dataext         = 1,
                            dispaxis        = 0,
                            xgap            = 0.,
                            ygap            = 0.,
                            ysize           = 1.,
                            platescale      = 0.225,
                            darkcurr        = 0.0,
                            saturation      = 65535.,
                            nonlinear       = 0.76,
                            numamplifiers   = 1,
                            gain            = 1.2,
                            ronoise         = 5.0,
                            datasec         = '[:,2:4030]',
                            suffix          = '_blue'
                            )
            ]
        self.numhead = 2
        # Uses default timeunit
        # Uses default primary_hdrext
        # self.sky_file = ?

    @staticmethod
    def default_pypit_par():
        """
        Set default parameters for Keck LRISb reductions.
        """
        par = pypitpar.PypitPar()
        par['rdx']['spectrograph'] = 'wht_isis_blue'
        # Use the ARMS pipeline
        par['rdx']['pipeline'] = 'ARMS'
        # Set wave tilts order
        #
        par['calibrations']['pixelflatframe']['combine']['method'] = 'median'
        par['calibrations']['pixelflatframe']['combine']['sig_lohi'] = [10.,10.]
        par['calibrations']['wavelengths']['method'] = 'simple'
        # Always sky subtract, starting with default parameters
        par['skysubtract'] = pypitpar.SkySubtractionPar()
        # Always flux calibrate, starting with default parameters
        par['fluxcalib'] = None  #  pypitpar.FluxCalibrationPar()
        # Always correct for flexure, starting with default parameters
        par['flexure'] = pypitpar.FlexurePar()
        return par

    def header_keys(self):
        def_keys = self.default_header_keys()
        #
        def_keys[0]['idname'] = 'IMAGETYP'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['lamps'] = 'CAGLAMPS'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['dichroic'] = 'ISIDICHR'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['decker'] = 'ISISLITU'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['slitwid'] = 'ISISLITW'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['filter1'] = 'ISIFILTA'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['filter2'] = 'ISIFILTB'   # A time stamp of the observation; used to find calibrations proximate to science frames. The units of this value are specified by fits+timeunit below
        def_keys[0]['dispname'] = 'ISIGRAT'
        def_keys[0]['dispangle'] = 'CENWAVE'

        def_keys[1] = {}
        def_keys[1]['naxis1'] = 'NAXIS1'
        def_keys[1]['naxis0'] = 'NAXIS2'

        return def_keys

    def cond_dict(self, ftype):
        cond_dict = {}

        if ftype == 'science':
            cond_dict['condition1'] = 'lamps=Off'
            cond_dict['condition2'] = 'exptime>1'
        elif ftype == 'bias':
            cond_dict['condition1'] = 'exptime<1'
        elif ftype == 'pixelflat':
            cond_dict['condition1'] = 'lamps=W'
        elif ftype == 'pinhole':
            cond_dict['condition1'] = 'exptime>99999999'
        elif ftype == 'trace':
            cond_dict['condition1'] = 'lamps=W'
        elif ftype == 'arc':
            cond_dict['condition1'] = 'lamps=CuNe+CuAr'
            cond_dict['condition2'] = 'exptime<120'
        else:
            pass

        return cond_dict

    def get_match_criteria(self):
        match_criteria = {}
        for key in arsort.ftype_list:
            match_criteria[key] = {}
        #        # Science
        #        match_criteria['science']['number'] = 1
        # Standard
        #        match_criteria['standard']['number'] = 1  # Can be over-ruled by flux calibrate = False
        match_criteria['standard']['match'] = {}
        match_criteria['standard']['match']['naxis0'] = '=0'
        match_criteria['standard']['match']['naxis1'] = '=0'
        match_criteria['standard']['match']['decker'] = ''
        match_criteria['standard']['match']['dispangle'] = '|<=1'
        # Bias
        match_criteria['bias']['match'] = {}
        match_criteria['bias']['match']['naxis0'] = '=0'
        match_criteria['bias']['match']['naxis1'] = '=0'
        # Pixelflat
        match_criteria['pixelflat']['match'] = match_criteria['standard']['match'].copy()
        # Traceflat
        match_criteria['trace']['match'] = match_criteria['standard']['match'].copy()
        # Arc
        match_criteria['arc']['match'] = match_criteria['standard']['match'].copy()

        # Return
        return match_criteria

    def setup_arcparam(self, arcparam, disperser=None, fitstbl=None,
                       arc_idx=None, msarc_shape=None, **null_kwargs):
        """
        Setup the arc parameters

        Args:
            arcparam: dict
            disperser: str, REQUIRED
            **null_kwargs:
              Captured and never used

        Returns:
            arcparam is modified in place
            modify_dict: dict

        """
        modify_dict = dict(NeI={'min_wave': 3000.,'min_intensity': 299,
                                'min_Aki': 0.},ArI={'min_intensity': 399.})
        arcparam['lamps']=['CuI','NeI','ArI']
        if fitstbl["dichroic"][arc_idx].strip() == '5300':
            arcparam['wvmnx'][1] = 6000.
        else:
            msgs.error('Not ready for this dichroic {:s}!'.format(disperser))
        if disperser == 'R300B':
            arcparam['n_first']=1  #
            arcparam['disp']=0.80  # Ang per pixel (unbinned)
            arcparam['b1']= 1./arcparam['disp']/msarc_shape[0]
        else:
            msgs.error('Not ready for this disperser {:s}!'.format(disperser))
        #
        return modify_dict

