#!/usr/bin/env python3


import os
import sys
import time
import numpy as np


"""
Used some code from from following projects:
miniscoPy (Guillaume Viejo):
https://github.com/PeyracheLab/miniscoPy
and CaImAn (Andrea Giovannucci et al.)
https://github.com/flatironinstitute/CaImAn
https://github.com/flatironinstitute/CaImAn/graphs/contributors
"""

"""
Copyright (C) 2018 Denis Polygalov,
Laboratory for Circuit and Behavioral Physiology,
RIKEN Center for Brain Science, Saitama, Japan.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, a copy is available at
http://www.fsf.org/
"""

def bin_median(na_input, i_win_sz=10, b_exclude_nans=True):
    """
    Compute median of 3D array in along axis o by binning values

    Parameters:
    ----------

    na_input: ndarray
        input 3D matrix, time along first dimension

    i_win_sz: int
        number of frames in a bin

    Returns:
    -------
    na_out: ndarray
        median image
    """

    T, d1, d2 = np.shape(na_input)
    if T < i_win_sz:
        i_win_sz = T
    num_windows = np.int(np.floor(T / i_win_sz)) # re-implementation of the old_div()
    num_frames = num_windows * i_win_sz
    if b_exclude_nans:
        na_out = np.nanmedian(np.nanmean(np.reshape(
            na_input[:num_frames], (i_win_sz, num_windows, d1, d2)), axis=0), axis=0)
    else:
        na_out = np.median(np.mean(np.reshape(
            na_input[:num_frames], (i_win_sz, num_windows, d1, d2)), axis=0), axis=0)
    return na_out
#

def bootstrap_template(oc_movie, i_tmpl_nframes, s_method="head", i_color_ch=0, b_verbose=False):
    """
    Read 'i_tmpl_nframes' frames from multi-part movie object 'oc_movie'
    by using method 's_method'. Input frames will be converted to, and output is
    returned as 3D array of (TIME x FRAME_HEIGHT x FRAME_WIDTH) shape and np.float32 type.
    Only single color/grayscale/np.float32 type of input supported.
    """
    i_max_nframes = oc_movie.df_info['frames'].sum()
    i_half_nframes = np.int(i_max_nframes/2)
    i_half_ntmpl   = np.int(i_tmpl_nframes/2)

    if i_tmpl_nframes >= i_max_nframes:
        raise ValueError("Requested template size(%d) is too big for this movie(%d)" % (i_tmpl_nframes,i_max_nframes) )

    if s_method == "head":
        na_indices = np.arange(i_tmpl_nframes)

    elif s_method == "tail":
        na_indices = np.arange(i_max_nframes - i_tmpl_nframes, i_max_nframes, 1)

    elif s_method == "middle":
        na_indices = np.arange(i_half_nframes - i_half_ntmpl, i_half_nframes + i_half_ntmpl, 1)

    elif s_method == "random":
        na_indices = np.random.randint(0, high=i_max_nframes, size=i_tmpl_nframes)

    else: raise ValueError("Unsupported method: %s" % s_method)

    oc_movie.read_frame(0)

    # make sure the shape of this array is (T x H x W) where
    # (H x W) is the shape of the frame and T is the time axis.
    na_template = np.zeros([na_indices.shape[0], oc_movie.na_frame.shape[0], oc_movie.na_frame.shape[1]], dtype=np.float32)

    if b_verbose:
        print("bootstrap_template: s_method=%s i_tmpl_nframes=%d i_color_ch=%d na_template.shape=%s" % \
            (s_method, i_tmpl_nframes, i_color_ch, repr(na_template.shape)) \
        )

    for tt, idx in enumerate(na_indices):
        oc_movie.read_frame(idx) # read the next requested frame

        if len(oc_movie.na_frame.shape) == 3:
            if i_color_ch >= oc_movie.na_frame.shape[2]:
                 raise ValueError("Color channel mismatch: i_color_ch=%d oc_movie.na_frame.shape=%s" % (i_color_ch, repr(oc_movie.na_frame.shape)))
            else:
                na_template[tt,:,:] = oc_movie.na_frame[:,:,i_color_ch].astype(np.float32)
        #
        elif len(oc_movie.na_frame.shape) == 2:
            na_template[tt,:,:] = oc_movie.na_frame[:,:].astype(np.float32)
        else:
            raise ValueError("Unsupported frame shape: %s" % repr(oc_movie.na_frame.shape))
        #
        # if b_verbose: print("bootstrap_template: %s" % oc_movie.get_frame_stat())
    #
    return na_template
#
