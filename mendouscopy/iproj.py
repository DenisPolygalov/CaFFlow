#!/usr/bin/env python3


import numpy as np


"""
Copyright (C) 2020 Denis Polygalov,
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


class CIntensityProjector(object):
    """Process each incoming frame and update internal data.
    At the end of the movie after calling the finalize_projection() method
    calculate various types (max, min, std) of intensity projections.
    """
    def __init__(self, i_frame_h, i_frame_w):
        # frames are counted starting from zero, each time when the process_frame() method called.
        self._i_nframes_proc = -1
        self._b_projection_finalized = False
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.d_IPROJ = {}

        self.na_iproj_max = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_idx_max = np.zeros([i_frame_h, i_frame_w], dtype=np.bool)

        self.na_iproj_min = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_idx_min = np.zeros([i_frame_h, i_frame_w], dtype=np.bool)

        self.na_iproj_std_delta = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_iproj_std_mean = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_iproj_std_M2 = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.i_ddof = 0

    def process_frame(self, na_input, b_verbose=False):
        if self._b_projection_finalized:
            raise ValueError("Inappropriate method calling sequence. This object cannot be reused after finalization!")
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")
        if na_input.shape[0] != self.i_frame_h:
            raise ValueError("Unexpected frame height")
        if na_input.shape[1] != self.i_frame_w:
            raise ValueError("Unexpected frame width")

        self._i_nframes_proc += 1

        # Maximum Intensity Projection
        np.greater(na_input, self.na_iproj_max, out=self.na_idx_max)
        self.na_iproj_max[self.na_idx_max] = na_input[self.na_idx_max]

        # Minimum Intensity Projection
        np.less(na_input, self.na_iproj_min, out=self.na_idx_min)
        self.na_iproj_min[self.na_idx_min] = na_input[self.na_idx_min]

        # Standard Deviation Intensity Projection
        # https://stackoverflow.com/questions/5543651/computing-standard-deviation-in-a-stream
        # https://stackabuse.com/calculating-variance-and-standard-deviation-in-python/
        # https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        self.na_iproj_std_delta = na_input - self.na_iproj_std_mean
        self.na_iproj_std_mean += self.na_iproj_std_delta / (self._i_nframes_proc + 1)
        self.na_iproj_std_M2 += self.na_iproj_std_delta * (na_input - self.na_iproj_std_mean)

    def finalize_projection(self):
        self.d_IPROJ['IPROJ_max'] = self.na_iproj_max
        self.d_IPROJ['IPROJ_min'] = self.na_iproj_min
        self.d_IPROJ['IPROJ_std'] = np.sqrt( self.na_iproj_std_M2 / (self._i_nframes_proc + 1 - self.i_ddof) )
        self._b_projection_finalized = True
    #
#

