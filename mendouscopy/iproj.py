#!/usr/bin/env python3


import numpy as np


"""
Copyright (C) 2020-2021 Denis Polygalov,
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
    def __init__(self, i_frame_h, i_frame_w, features=None):
        # frames are counted starting from zero, each time when the process_frame() method called.
        self._i_nframes_proc = -1
        self._b_projection_finalized = False
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.i_fet_frame_idx = 0
        self.i_fet_frame_idx_accepted = 0
        self.d_IPROJ = {}

        self.na_iproj_max = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_idx_max = np.zeros([i_frame_h, i_frame_w], dtype=bool)

        self.na_iproj_min = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_idx_min = np.zeros([i_frame_h, i_frame_w], dtype=bool)

        self.na_iproj_std_delta = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_iproj_std_mean = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_iproj_std_M2 = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.i_ddof = 0

        self.na_iproj_mean = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)

        if isinstance(features, np.ndarray):
            print("CIntensityProjector: features.shape:", features.shape)
            print("CIntensityProjector: features.ndim:", features.ndim)
            if features.ndim > 2 or features.ndim < 1:
                raise ValueError("Unsupported shape of the 'features' array!")
            if features.ndim == 2:
                if features.shape[0] == 1 or features.shape[1] == 1:
                    raise ValueError("Unsupported shape of the 'features' array. Squeeze it in advance!")

            if features.ndim == 2 and features.shape[0] >= features.shape[1]:
                self.na_featured_frame_ids = np.where(features.sum(axis=1) > 0)[0]

            elif features.ndim == 2 and features.shape[0] <  features.shape[1]:
                self.na_featured_frame_ids = np.where(features.sum(axis=0) > 0)[0]

            elif features.ndim == 1:
                self.na_featured_frame_ids = np.where(features > 0)[0]

            print("CIntensityProjector: na_featured_frame_ids.shape:", self.na_featured_frame_ids.shape)
            print("CIntensityProjector: na_featured_frame_ids.size:", self.na_featured_frame_ids.size)

        else:
            print("CIntensityProjector: the 'features' array is NOT provided!")
            self.na_featured_frame_ids = None
        self.na_iproj_fet = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)

    def process_frame(self, na_input, b_verbose=False):
        if self._b_projection_finalized:
            raise ValueError("Inappropriate method calling sequence. This object cannot be reused after finalization!")
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")
        if na_input.shape[0] != self.i_frame_h:
            raise ValueError("Unexpected frame height")
        if na_input.shape[1] != self.i_frame_w:
            raise ValueError("Unexpected frame width")

        # initial value of the self._i_nframes_proc is -1
        # here we increment it and therefore indicate currently processed frame
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

        # Mean Intensity Projection
        self.na_iproj_mean[...] += (na_input.astype(np.float64))

        # Features (local) Intensity Projection
        if isinstance(self.na_featured_frame_ids, np.ndarray) and \
            self.i_fet_frame_idx < self.na_featured_frame_ids.size:

            if self._i_nframes_proc == self.na_featured_frame_ids[self.i_fet_frame_idx]:
                f_max_val = na_input.max()
                if f_max_val >= 1:
                    self.na_iproj_fet[...] += (na_input.astype(np.float64) / f_max_val)
                    self.i_fet_frame_idx_accepted += 1
                self.i_fet_frame_idx += 1

                if b_verbose:
                    if f_max_val >= 1:
                        print("CIntensityProjector: frame: %i max_val: %.2f (ACCEPTED)" % (self._i_nframes_proc, f_max_val))
                    else:
                        print("CIntensityProjector: frame: %i max_val: %.2f (rejected)" % (self._i_nframes_proc, f_max_val))

    def finalize_projection(self):
        self.d_IPROJ['IPROJ_max'] = self.na_iproj_max
        self.d_IPROJ['IPROJ_min'] = self.na_iproj_min
        self.d_IPROJ['IPROJ_std'] = np.sqrt( self.na_iproj_std_M2 / (self._i_nframes_proc + 1 - self.i_ddof) )
        if isinstance(self.na_featured_frame_ids, np.ndarray):
            print("CIntensityProjector: number of frames accepted:", self.i_fet_frame_idx_accepted)
            print("CIntensityProjector: number of frames rejected:", self.i_fet_frame_idx - self.i_fet_frame_idx_accepted)
            self.na_iproj_fet /= self.i_fet_frame_idx_accepted
        self.d_IPROJ['IPROJ_fet'] = self.na_iproj_fet
        self.d_IPROJ['IPROJ_mean'] = self.na_iproj_mean / self._i_nframes_proc
        self._b_projection_finalized = True
    #
#


class CROISpecificIntensityProjector(object):
    """Process each incoming frame and update internal data.
    At the end of the movie after calling the finalize_projection() method
    calculate various types of intensity projections.
    As distinct of CIntensityProjector this class require fluorescence
    data to be provided at the moment of object creation and calculate
    ROI-specific intensity projections based on ROI positions and dF/F
    traces detected in advance.
    """
    def __init__(self, i_frame_h, i_frame_w, d_FLUO):
        # frames are counted starting from zero, each time when the process_frame() method called.
        self._i_nframes_proc = -1
        self._b_projection_finalized = False
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.d_ROI_fimi = {} # {frame_id : [mask_id, mask_id, ...]}
        self.d_ROI_fimi_max = {} # {frame_id : [mask_id, mask_id, ...]}
        self.d_IPROJ = {}

        self.l_ROI_data = d_FLUO['ROI_data']
        self.i_nframes, self.i_nROIs = d_FLUO['dFF'].shape
        assert(self.i_nROIs == len(self.l_ROI_data))

        for i_roi_id in range(self.i_nROIs):
            s_frame_id = str(self.l_ROI_data[i_roi_id]['frame_id'])
            i_mask_id = self.l_ROI_data[i_roi_id]['mask_id']

            if s_frame_id not in self.d_ROI_fimi:
                self.d_ROI_fimi[s_frame_id] = []
                self.d_ROI_fimi[s_frame_id].append(i_mask_id)
            else:
                self.d_ROI_fimi[s_frame_id].append(i_mask_id)

            na_dFF_roi = d_FLUO['dFF'][:,i_roi_id]
            s_frame_id_at_max_fluo = str(np.argmax(na_dFF_roi))

            if s_frame_id_at_max_fluo not in self.d_ROI_fimi_max:
                self.d_ROI_fimi_max[s_frame_id_at_max_fluo] = []
                self.d_ROI_fimi_max[s_frame_id_at_max_fluo].append(i_mask_id)
            else:
                self.d_ROI_fimi_max[s_frame_id_at_max_fluo].append(i_mask_id)

        self.na_ROI_mask = d_FLUO['ROI_mask']
        self.na_canvas = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)

        self.na_ROI_fluo_raw  = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_ROI_fluo_norm = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)
        self.na_ROI_fluo_max  = np.zeros([i_frame_h, i_frame_w], dtype=np.float64)

    def process_frame(self, na_input, b_verbose=False):
        if self._b_projection_finalized:
            raise ValueError("Inappropriate method calling sequence. This object cannot be reused after finalization!")
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")
        if na_input.shape[0] != self.i_frame_h:
            raise ValueError("Unexpected frame height")
        if na_input.shape[1] != self.i_frame_w:
            raise ValueError("Unexpected frame width")

        # initial value of the self._i_nframes_proc is -1
        # here we increment it and therefore indicate currently processed frame
        self._i_nframes_proc += 1

        s_frame_id = str(self._i_nframes_proc)

        if s_frame_id in self.d_ROI_fimi:
            assert(len(self.d_ROI_fimi[s_frame_id]) != 0)
            if b_verbose:
                print("CROISpecificIntensityProjector: ", s_frame_id, d_ROI_fimi[s_frame_id])

            for i_mask_id in self.d_ROI_fimi[s_frame_id]:
                IDX = np.where(self.na_ROI_mask == i_mask_id)
                self.na_ROI_fluo_raw[IDX] += na_input[IDX]

                self.na_canvas.fill(0)
                self.na_canvas[IDX] = na_input[IDX]
                f_max = np.max(self.na_canvas)
                assert(f_max != 0)
                self.na_canvas /= f_max
                self.na_ROI_fluo_norm[...] += self.na_canvas[...]

        if s_frame_id in self.d_ROI_fimi_max:
            for i_mask_id in self.d_ROI_fimi_max[s_frame_id]:
                IDX = np.where(self.na_ROI_mask == i_mask_id)
                self.na_ROI_fluo_max[IDX] += na_input[IDX]

    def finalize_projection(self):
        self.na_ROI_fluo_raw[self.na_ROI_fluo_raw   == 0.0] = np.nan
        self.na_ROI_fluo_norm[self.na_ROI_fluo_norm == 0.0] = np.nan
        self.na_ROI_fluo_max[self.na_ROI_fluo_max   == 0.0] = np.nan
        self.d_IPROJ['IPROJ_ROI_fluo_raw'] = self.na_ROI_fluo_raw
        self.d_IPROJ['IPROJ_ROI_fluo_norm'] = self.na_ROI_fluo_norm
        self.d_IPROJ['IPROJ_ROI_fluo_max'] = self.na_ROI_fluo_max
        self._b_projection_finalized = True
    #
#
