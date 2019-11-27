#!/usr/bin/env python3


import os, sys
import numpy as np
import cv2 as cv


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


def calc_squaring_margins(na_movie, b_verbose=False):
    """
    Return a tuple of two integers - best margins to
    convert the 'na_movie' array to square shape frame.
    input:  na_movie - (T x H x W) matrix of movie frames
    output: tuple(i_left_margin, i_right_margin) - best margins
            to slice the 'na_movie' to square (T x N x N) shape
            where N = min(H,W)
    """
    if len(na_movie.shape) != 3:
        raise ValueError("Unexpected shape: %s" % repr(na_movie.shape))
    #
    i_frame_number = 0
    oc_squaring_filter = CSquaringFilter(na_movie[i_frame_number,:,:].shape)
    while (i_frame_number < na_movie.shape[0]):
        oc_squaring_filter.process_frame(na_movie[i_frame_number,:,:], b_verbose=b_verbose)
        i_frame_number += 1
    #
    na_margins = np.array(oc_squaring_filter.l_all_margins, dtype=np.int32)
    return tuple( np.median(na_margins,axis=0).astype(np.int32) )
#

class CSquaringFilter(object):
    """
    Convert rectangular shape input frame into a square frame
    by cutting (left / right) or (top / bottom) margins.
    Margins to cut are calculated based in intensity changes along
    the longer size of the input frame. This can only be used for
    input data containing relatively bright FOV in the middle
    (not necessary center) of the frame surrounded by black sides.
    NOTE: only 2D arrays are acceptable as input!
    """
    def __init__(self, t_input_frame_shape):
        if len(t_input_frame_shape) != 2:
            raise ValueError("Unsupported frame shape: %s" % repr(t_input_frame_shape))

        nrows, ncols = t_input_frame_shape[0], t_input_frame_shape[1]
        self._t_init_shape = t_input_frame_shape

        if nrows < ncols:
            self.i_target_axis = 0
            self.i_target_sz = nrows
        elif nrows > ncols:
            self.i_target_axis = 1
            self.i_target_sz = ncols
        else: raise ValueError("Input is already a square")

        # main data exchange interface for this class
        self.t_curr_margins = None # a tuple consisting of two integers - margin width values
        self.l_all_margins  = []   # list of tuples, each tuple consist of self.t_curr_margins
        self.na_out = None
    #
    def _calc_margins(self, na_section):
        """
        'na_section' must be a 1D array (vector)
        'self.i_target_sz' must be less than na_section.size
        """
        # The left(top) and right(bottom) side margins
        i_Lm = 0
        i_Rm = na_section.size - 1 # point to the last element in the na_section vector
        while ((i_Rm - i_Lm) > self.i_target_sz):
            i_dLm = np.int32(na_section[i_Lm+1]) - np.int32(na_section[i_Lm])
            i_dRm = np.int32(na_section[i_Rm-1]) - np.int32(na_section[i_Rm])
            if i_dLm >= i_dRm: i_Rm -= 1
            if i_dRm >= i_dLm: i_Lm += 1
            # print(i_Lm, i_Rm)
        #
        self.t_curr_margins = (i_Lm, i_Rm)
        self.l_all_margins.append(self.t_curr_margins)
    #
    def process_frame(self, na_input, b_verbose=False):
        if na_input.shape != self._t_init_shape:
            raise ValueError("Unexpected frame shape: %s expecting: %s" % \
                (repr(na_input.shape), self._t_init_shape) \
            )
        self._calc_margins(na_input.sum(self.i_target_axis))

        # assign the output
        if self.i_target_axis == 0:
            self.na_out = na_input[:, self.t_curr_margins[0]:self.t_curr_margins[1]]

        elif self.i_target_axis == 1:
            self.na_out = na_input[self.t_curr_margins[0]:self.t_curr_margins[1], :]

        else: raise ValueError("Unexpected target axis: %s" % repr(self.i_target_axis))

        if b_verbose:
            print("na_input.shape=%s t_curr_margins=%s na_out.shape=%s" % \
                (repr(na_input.shape), repr(self.t_curr_margins), repr(self.na_out.shape)) \
            )
        #
    #
#

class CPZhouFilter(object):
    """
    To my knowledge this filter appear first in preprint
    of the CNMF-E paper: https://arxiv.org/abs/1605.07266
    page 19-20 (chapter 5.4.1).
    The authors call it "high pass spatial filter" but
    de-facto this filter is not pure "high-pass" neither
    "low-pass" type. It can be viewed as one of so called
    "edge-preserving" smoothing filters. For review see for example:
    Bruno Tunjic - Edge-preserving Smoothing Methods: Overview and Comparison.
    In CaImAn code this filter's function name is: high_pass_filter_space
    In miniscoPy code this filter's function name is: low_pass_filter_space
    """
    def __init__(self, i_filter_sz):
        t_flt_sz = (i_filter_sz, i_filter_sz)
        kernel_size = tuple([(3 * i) // 2 * 2 + 1 for i in t_flt_sz])
        kernel = cv.getGaussianKernel(kernel_size[0], t_flt_sz[0])
        self.kernel2D = kernel.dot(kernel.T)
        nz = np.nonzero(self.kernel2D >= self.kernel2D[:, 0].max())
        zz = np.nonzero(self.kernel2D  < self.kernel2D[:, 0].max())
        self.kernel2D[nz] -= self.kernel2D[nz].mean()
        self.kernel2D[zz] = 0
        # main data exchange interface for this class
        self.na_out = None
    #
    def process_frame(self, na_input):
        self.na_out = cv.filter2D(na_input, -1, self.kernel2D, borderType=cv.BORDER_REFLECT)
    #
#

class CFastGuidedFilter(object):
    """
    Edge-preserving spatial smoothing filter.
    https://arxiv.org/abs/1505.00996
    http://kaiminghe.com/eccv10/
    """
    def __init__(self, i_filter_sz, f_eps=0.01):
        self.i_filter_sz = np.int(i_filter_sz)
        self.f_eps = f_eps
        self.t_filter_sz = ((2 * self.i_filter_sz) + 1, (2 * self.i_filter_sz) + 1)
        # main data exchange interface for this class
        self.na_out = None
    #
    def process_frame(self, na_input):
        na_I2 = cv.pow(na_input, 2);
        mean_I  = cv.boxFilter(na_input, -1, self.t_filter_sz)
        mean_I2 = cv.boxFilter(na_I2,    -1, self.t_filter_sz)

        cov_I = mean_I2 - cv.pow(mean_I, 2)

        na_a = cv.divide(cov_I, cov_I + self.f_eps)
        na_b = mean_I - (na_a * mean_I)

        mean_a = cv.boxFilter(na_a, -1, self.t_filter_sz)
        mean_b = cv.boxFilter(na_b, -1, self.t_filter_sz)

        self.na_out = (mean_a * na_input) + mean_b
    #
#


class CPrinCompWiper(object):
    def __init__(self, i_frame_h, i_frame_w, pcs2rm=[0], b_sanity_check=True):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w

        if not isinstance(pcs2rm, list) and not isinstance(pcs2rm, tuple):
            raise TypeError("pcs2rm must be a list or a tuple")
        for pc in pcs2rm:
            if not isinstance(pc,int) or pc < 0:
                raise ValueError("PCs to remove must be positive integers")
        if b_sanity_check:
            if len(pcs2rm) > 1 or pcs2rm[0] != 0:
                # for those ho wants to remove anything else than the first PC
                # Principal Components are counted starting from ZERO!
                raise ValueError("sanity check failed")
        self.pcs2rm = pcs2rm

        if self.i_frame_h > self.i_frame_w:
            self.na_in_mean = np.zeros(self.i_frame_w, dtype=np.float32)
        else:
            self.na_in_mean = np.zeros(self.i_frame_h, dtype=np.float32)

        # main data exchange interface for this class
        self.na_out = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

    def process_frame(self, na_input):
        # copy input frame data into the output array
        self.na_out[...] = na_input[...]

        # center input data by subtracting it's mean
        if self.i_frame_h > self.i_frame_w:
            np.mean(na_input, axis=0, out=self.na_in_mean)
            na_in_centered = (na_input - self.na_in_mean).T
        else:
            np.mean(na_input, axis=1, out=self.na_in_mean)
            na_in_centered = (na_input.T - self.na_in_mean).T

        # calculate eigenvalues and eigenvectors of the covariance matrix of input data
        [na_latent, na_coeff] = np.linalg.eigh(np.cov(na_in_centered))

        idx = np.argsort(na_latent) # sorting the eigenvalues
        idx = idx[::-1]             # in ascending order

        # sorting eigenvectors according to the sorted eigenvalues
        na_coeff = na_coeff[:,idx]

        # projection of the data in the new space
        na_score = np.dot(na_coeff[:, self.pcs2rm].T, na_in_centered)

        # reconstruct an image that contain only PCs requested to be removed
        na_pc2rm = np.dot(na_coeff[:, self.pcs2rm], na_score).T + self.na_in_mean

        # subtract reconstructed image from the input frame
        if self.i_frame_h > self.i_frame_w:
            self.na_out -= na_pc2rm
        else:
            self.na_out -= na_pc2rm.T
        #
    #
#

