#!/usr/bin/env python3


import warnings
from collections import deque
import cv2 as cv
import numpy as np
from .filtering import CFastGuidedFilter
from .tiling import draw_border
from .tiling import CTiledFrame
from .tiling import CStiBordFrame


"""
Copyright (C) 2018,2019 Denis Polygalov,
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


class CRigidMotionEstimator(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.frame_dtype = frame_dtype
        self.t_frame_wh = (i_frame_w, i_frame_h)
        self.i_frame_id = 0

        self.na_wM_dummy = np.eye(2, 3, dtype=np.float32)
        self.na_wM_ref   = np.eye(2, 3, dtype=np.float32)
        self.na_wM_prev  = np.eye(2, 3, dtype=np.float32)
        self.na_wM_curr  = np.eye(2, 3, dtype=np.float32)

        if d_param["ecc_motion_type"] == "translation":
            self.i_warp_mode = cv.MOTION_TRANSLATION
        elif d_param["ecc_motion_type"] == "euclidean":
            self.i_warp_mode = cv.MOTION_EUCLIDEAN
        else:
            raise ValueError("Unsupported motion type")

        # ecc_num_iter == 100, ecc_termination_eps == 1e-6
        self.t_criteria = (
            cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT,
            int(d_param["ecc_num_iter"]),
            float(d_param["ecc_termination_eps"])
        )

        self._na_curr_frame = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.uint8)
        self._na_prev_frame = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.uint8)

        # main data exchange interface for this class
        self.d_MSTAT = {}
        self.d_MSTAT['MSTAT_corr_coef'] = []
        self.d_MSTAT['MSTAT_inter_frame_dist'] = []
        self.d_MSTAT['MSTAT_warp_matrix'] = []
    #
    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")

        self._na_curr_frame[...] = cv.normalize(na_input, None, alpha=0, beta=255, norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)

        if self.i_frame_id == 0:
            self._na_prev_frame[...] = self._na_curr_frame[...]
            self.d_MSTAT['MSTAT_corr_coef'].append(1.0)
            self.d_MSTAT['MSTAT_inter_frame_dist'].append(0.0)
            self.d_MSTAT['MSTAT_warp_matrix'].append(self.na_wM_curr.copy())
            self.i_frame_id += 1
            return

        self.na_wM_dummy[...] = self.na_wM_ref[...]
        f_cc, self.na_wM_curr[...] = cv.findTransformECC(
            self._na_prev_frame,
            self._na_curr_frame,
            self.na_wM_dummy,
            self.i_warp_mode,
            self.t_criteria
        )
        f_f2f_dist = np.linalg.norm(self.na_wM_prev[:,-1] - self.na_wM_curr[:,-1])

        self.d_MSTAT['MSTAT_corr_coef'].append(f_cc)
        self.d_MSTAT['MSTAT_inter_frame_dist'].append(f_f2f_dist)
        self.d_MSTAT['MSTAT_warp_matrix'].append(self.na_wM_curr.copy())

        self.na_wM_prev[...] = self.na_wM_curr[...]
        self._na_prev_frame[...] = self._na_curr_frame[...]

        if b_verbose:
            print("frame_id: %i\tf2f_dist: %.3f\tcorr_coeff: %.3f" % (self.i_frame_id, f_f2f_dist, f_cc))
        #
        self.i_frame_id += 1
    #
#


class CFrameRegNone(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.frame_dtype = frame_dtype
        self.t_frame_wh = (i_frame_w, i_frame_h)
        self.i_frame_id = 0
        self.na_wM = np.eye(2, 3, dtype=np.float32)

        self.oc_filter = CFastGuidedFilter(int(d_param["filter_size"])) # 5

        t_krnl_sz = (int(d_param["kernel_size"]), int(d_param["kernel_size"])) # (15,15)
        self.oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, t_krnl_sz)

        self.i_morph_niter = int(d_param["morph_num_iter"]) # 3
        self.na_bgr = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        # main data exchange interface for this class
        self.na_out     = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        self.na_out_reg = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        self.d_REG = {}
        self.d_REG['REG_warp_flag'] = []
        self.d_REG['REG_corr_coef'] = []
        self.d_REG['REG_inter_frame_dist'] = []
        self.d_REG['REG_warp_matrix'] = []
    #
    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")

        self.oc_filter.process_frame(cv.normalize(na_input, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))
        self.na_bgr[...] = cv.morphologyEx(self.oc_filter.na_out, cv.MORPH_OPEN, self.oc_strel_kernel, iterations=self.i_morph_niter)
        self.na_out[...] = cv.normalize(self.oc_filter.na_out - self.na_bgr, None, alpha=0, beta=255, norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)

        self.d_REG['REG_warp_flag'].append(0)
        self.d_REG['REG_corr_coef'].append(1.0)
        self.d_REG['REG_inter_frame_dist'].append(0.0)
        self.d_REG['REG_warp_matrix'].append(self.na_wM.copy())

        if self.i_frame_id == 0:
            self.na_out_reg[...] = self.oc_filter.na_out - self.na_bgr

        self.i_frame_id += 1
    #
    def register_frame(self):
        if self.i_frame_id == 0:
            raise ValueError("Unexpected method call. Call process_frame() first!")
        if self.i_frame_id == 1: return
        self.na_out_reg[...] = self.oc_filter.na_out - self.na_bgr
    #
#


class CFrameRegECCfifo(object):
    """
    Frame-wise rigid motion correction by calculating geometric
    transform (warp) between two images in terms of the ECC criterion.
    """
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.frame_dtype = frame_dtype
        self.t_frame_wh = (i_frame_w, i_frame_h)
        self.i_frame_id = 0
        self.WARP_FLAGS = cv.INTER_LINEAR + cv.WARP_INVERSE_MAP
        self.BORDER_MODE = cv.BORDER_REPLICATE

        self.i_fifo_max_len = int(d_param["fifo_maxlen"])
        self.oc_Ffifo = deque(maxlen=self.i_fifo_max_len)
        self.oc_Mfifo = deque(maxlen=self.i_fifo_max_len)
        self.na_wM    = np.eye(2, 3, dtype=np.float32)
        self.na_wMref = np.eye(2, 3, dtype=np.float32)

        self.oc_filter = CFastGuidedFilter(int(d_param["filter_size"])) # 5

        t_krnl_sz = (int(d_param["kernel_size"]), int(d_param["kernel_size"])) # (15,15)
        self.oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, t_krnl_sz)
        self.f_warp_threshold = float(d_param["warp_threshold"])

        if d_param["ecc_motion_type"] == "translation":
            self.i_warp_mode = cv.MOTION_TRANSLATION
        elif d_param["ecc_motion_type"] == "euclidean":
            self.i_warp_mode = cv.MOTION_EUCLIDEAN
        else:
            raise ValueError("Unsupported motion type")

        # ecc_num_iter == 100, ecc_termination_eps == 1e-6
        self.t_criteria = (
            cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT,
            int(d_param["ecc_num_iter"]),
            float(d_param["ecc_termination_eps"])
        )
        self.i_morph_niter = int(d_param["morph_num_iter"]) # 3
        self.na_bgr = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)
        self.na_avg = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        # main data exchange interface for this class
        self.na_out     = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        self.na_out_reg = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        self.d_REG = {}
        self.d_REG['REG_warp_flag'] = []
        self.d_REG['REG_corr_coef'] = []
        self.d_REG['REG_inter_frame_dist'] = []
        self.d_REG['REG_warp_matrix'] = []
    #
    def __calc_fifo_avg(self):
        self.na_avg.fill(0.0)
        i_fifo_len = len(self.oc_Ffifo) # current(!) FIFO length
        for ii in range(i_fifo_len):
            self.na_avg += self.oc_Ffifo[ii]
        self.na_avg /= float(i_fifo_len)
        # this works as expected and replace last (newest) FIFO
        # element with average frame calculated across the whole FIFO
        self.oc_Ffifo[-1][...] = cv.normalize(
            self.na_avg, None,
            alpha=0, beta=255,
            norm_type=cv.NORM_MINMAX,
            dtype=cv.CV_8U
        )
    #
    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")

        self.oc_filter.process_frame(cv.normalize(na_input, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))
        self.na_bgr[...] = cv.morphologyEx(self.oc_filter.na_out, cv.MORPH_OPEN, self.oc_strel_kernel, iterations=self.i_morph_niter)
        self.na_out[...] = cv.normalize(self.oc_filter.na_out - self.na_bgr, None, alpha=0, beta=255, norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)

        if self.i_frame_id == 0:
            self.d_REG['REG_warp_flag'].append(0)
            self.d_REG['REG_corr_coef'].append(1.0)
            self.d_REG['REG_inter_frame_dist'].append(0.0)
            self.oc_Ffifo.append(self.na_out.copy())
            self.oc_Mfifo.append(self.na_wM.copy())
            self.d_REG['REG_warp_matrix'].append(self.na_wM.copy())
            self.na_out_reg[...] = self.oc_filter.na_out - self.na_bgr
            self.i_frame_id += 1
            return

        else:
            self.na_wMref[...] = self.oc_Mfifo[0][...]
            f_cc, self.na_wM[...] = cv.findTransformECC(
                self.oc_Ffifo[0],
                self.na_out,
                self.na_wMref,
                self.i_warp_mode,
                self.t_criteria
            )
            self.d_REG['REG_corr_coef'].append(f_cc)

            # calculate euclidean distnce between las column of the self.na_wM (2x3) matrix
            # and last column of the last (newest) entry of the self.oc_Mfifo double queue (FIFO)
            # the result will be shift in pixels between two frames. This shift is the shift that
            # will be compensated in the following cv.warpAffine() call.
            self.d_REG['REG_inter_frame_dist'].append(
                np.linalg.norm(
                    self.na_wM[:,-1] - self.oc_Mfifo[-1][:,-1]
                )
            )

            if self.d_REG['REG_inter_frame_dist'][-1] > self.f_warp_threshold:
                self.na_out[...] = cv.warpAffine(
                    self.na_out,
                    self.na_wM,
                    self.t_frame_wh,
                    flags=self.WARP_FLAGS,
                    borderMode=self.BORDER_MODE
                )
                self.d_REG['REG_warp_flag'].append(1)
            else:
                self.d_REG['REG_warp_flag'].append(0)

            if self.i_fifo_max_len  == 1:
                self.oc_Ffifo.append(self.na_out.copy())
            elif self.i_fifo_max_len > 1:
                self.oc_Ffifo.append(self.na_out.copy()) # DO THIS FIRST
                self.__calc_fifo_avg()
            else:
                raise ValueError("Unsupported FIFO maximal length")

            self.oc_Mfifo.append(self.na_wM.copy())
            self.d_REG['REG_warp_matrix'].append(self.na_wM.copy())
            self.i_frame_id += 1
        #
    #
    def register_frame(self):
        if self.i_frame_id == 0:
            raise ValueError("Unexpected method call. Call process_frame() first!")
        if self.i_frame_id == 1: return
        if self.d_REG['REG_inter_frame_dist'][-1] > self.f_warp_threshold:
            self.na_out_reg[...] = cv.warpAffine(
                self.oc_filter.na_out - self.na_bgr,
                self.na_wM,
                self.t_frame_wh,
                flags=self.WARP_FLAGS,
                borderMode=self.BORDER_MODE
            )
        else:
            self.na_out_reg[...] = self.oc_filter.na_out - self.na_bgr
        #
    #
#


class CFrameRegECC(object):
    """
    Frame-wise rigid motion correction by calculating geometric
    transform (warp) between two images in terms of the ECC criterion.
    """
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.frame_dtype = frame_dtype
        self.t_frame_wh = (i_frame_w, i_frame_h)
        self.i_frame_id = 0
        self.WARP_FLAGS = cv.INTER_LINEAR + cv.WARP_INVERSE_MAP
        self.BORDER_MODE = cv.BORDER_REPLICATE

        self.na_wM       = np.eye(2, 3, dtype=np.float32)
        self.na_wM_eye   = np.eye(2, 3, dtype=np.float32)
        self.na_wM_dummy = np.eye(2, 3, dtype=np.float32)

        self.oc_filter = CFastGuidedFilter(int(d_param["filter_size"])) # 5
        t_krnl_sz = (int(d_param["kernel_size"]), int(d_param["kernel_size"])) # (15,15)
        self.oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, t_krnl_sz)

        if d_param["ecc_motion_type"] == "translation":
            self.i_warp_mode = cv.MOTION_TRANSLATION
        elif d_param["ecc_motion_type"] == "euclidean":
            self.i_warp_mode = cv.MOTION_EUCLIDEAN
        else:
            raise ValueError("Unsupported motion type")

        # ecc_num_iter == 100, ecc_termination_eps == 1e-6
        self.t_criteria = (
            cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT,
            int(d_param["ecc_num_iter"]),
            float(d_param["ecc_termination_eps"])
        )
        self.i_morph_niter = int(d_param["morph_num_iter"]) # 3
        self.na_bgr    = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)
        self.na_ecc_in = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)

        # main data exchange interface for this class
        self.na_out     = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        self.na_out_reg = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        self.d_REG = {}
        self.d_REG['REG_warp_flag'] = []
        self.d_REG['REG_corr_coef'] = []
        self.d_REG['REG_inter_frame_dist'] = []
        self.d_REG['REG_warp_matrix'] = []
    #
    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")

        self.oc_filter.process_frame(cv.normalize(na_input, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))
        self.na_bgr[...] = cv.morphologyEx(self.oc_filter.na_out, cv.MORPH_OPEN, self.oc_strel_kernel, iterations=self.i_morph_niter)
        self.na_ecc_in[...] = cv.normalize(self.oc_filter.na_out - self.na_bgr, None, alpha=0, beta=255, norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)

        if self.i_frame_id == 0:
            self.d_REG['REG_warp_flag'].append(0)
            self.d_REG['REG_corr_coef'].append(1.0)
            self.d_REG['REG_inter_frame_dist'].append(0.0)
            self.d_REG['REG_warp_matrix'].append(self.na_wM.copy())
            self.na_out_reg[...] = self.oc_filter.na_out - self.na_bgr
            self.na_out[...] = self.na_ecc_in[...]
            self.i_frame_id += 1
            return

        else:
            self.na_wM_dummy[...] = self.na_wM_eye[...]
            b_findTransformECC_failed = False
            try:
                f_cc, self.na_wM[...] = cv.findTransformECC(
                    self.na_out,
                    self.na_ecc_in,
                    self.na_wM_dummy,
                    self.i_warp_mode,
                    self.t_criteria
                )
            except cv.error:
                warnings.warn("findTransformECC() failed to converge at frame %d" % self.i_frame_id)
                b_findTransformECC_failed = True

            if b_findTransformECC_failed:
                self.d_REG['REG_warp_flag'].append(0)
            else:
                self.d_REG['REG_warp_flag'].append(1)

            self.d_REG['REG_corr_coef'].append(f_cc)

            # calculate euclidean distance between las column of the self.na_wM (2x3) matrix
            # and last column of the last (newest) entry of the self.d_REG['REG_warp_matrix']
            # the result will be shift in pixels between two frames. This shift is the shift that
            # will be compensated in the following cv.warpAffine() call.
            self.d_REG['REG_inter_frame_dist'].append(
                np.linalg.norm(
                    self.na_wM[:,-1] - self.d_REG['REG_warp_matrix'][-1][:,-1]
                )
            )
            self.d_REG['REG_warp_matrix'].append(self.na_wM.copy())

            self.na_out[...] = cv.warpAffine(
                self.na_ecc_in,
                self.na_wM,
                self.t_frame_wh,
                flags=self.WARP_FLAGS,
                borderMode=self.BORDER_MODE
            )
            self.i_frame_id += 1
        #
    #
    def register_frame(self):
        if self.i_frame_id == 0:
            raise ValueError("Unexpected method call. Call process_frame() first!")
        if self.i_frame_id == 1: return
        self.na_out_reg[...] = cv.warpAffine(
            self.oc_filter.na_out - self.na_bgr,
            self.na_wM,
            self.t_frame_wh,
            flags=self.WARP_FLAGS,
            borderMode=self.BORDER_MODE
        )
    #
#


class CMotionFieldDrawer(object):
    def __init__(self, i_frame_h, i_frame_w, i_nrow_tiles, i_ncol_tiles, f_zoom_coef=5.0):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.i_nrow_tiles = i_nrow_tiles
        self.i_ncol_tiles = i_ncol_tiles
        self.f_zoom_coef = f_zoom_coef
        self.na_bgr = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.int32)
        self.oc_tbgr = CTiledFrame(self.na_bgr, self.i_nrow_tiles, self.i_ncol_tiles)
        for ix, iy in np.ndindex(self.oc_tbgr.shape):
            na_tile = self.oc_tbgr[ix, iy]
            draw_border(na_tile, border_width=1, border_value=1)
            i_cy = int(na_tile.shape[0]/2)
            i_cx = int(na_tile.shape[1]/2)
            na_tile[i_cy, i_cx-1] = 1
            na_tile[i_cy,   i_cx] = 1
            na_tile[i_cy, i_cx+1] = 1
            na_tile[i_cy-1, i_cx] = 1
            na_tile[i_cy+1, i_cx] = 1
            na_tile[i_cy, i_cx-2] = 1
            na_tile[i_cy, i_cx+2] = 1
            na_tile[i_cy-2, i_cx] = 1
            na_tile[i_cy+2, i_cx] = 1
        self.na_out = np.zeros_like(self.na_bgr)
        self.na_out[...] = self.na_bgr[...]
        self.oc_tout = CTiledFrame(self.na_out, self.i_nrow_tiles, self.i_ncol_tiles)
    #

    def process_frame(self, oc_tiled_warp_matrix, b_verbose=False):
        self.na_out[...] = self.na_bgr[...]
        for ix, iy in np.ndindex(oc_tiled_warp_matrix.shape):
            na_warp_matrix = oc_tiled_warp_matrix[ix, iy]
            na_tile = self.oc_tout[ix, iy]
            i_cy = int(na_tile.shape[0]/2)
            i_cx = int(na_tile.shape[1]/2)
            i_trg_x = int(np.round(na_warp_matrix[0,2] * self.f_zoom_coef))
            i_trg_y = int(np.round(na_warp_matrix[1,2] * self.f_zoom_coef))
            cv.line(na_tile, (i_cx, i_cy), (i_cx + i_trg_x, i_cy + i_trg_y), 1, thickness=1)
    #
#


class CPieceWiseECC(object):
    """Piece-wise implementation of OpenCV's findTransformECC() method.
    """
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.frame_dtype = frame_dtype
        self.i_frame_id = 0
        self.WARP_FLAGS = cv.INTER_LINEAR + cv.WARP_INVERSE_MAP

        self.na_wM    = np.eye(2, 3, dtype=np.float32)
        self.na_wMref = np.eye(2, 3, dtype=np.float32)

        self.oc_filter = CFastGuidedFilter(int(d_param["filter_size"])) # 5

        t_krnl_sz = (int(d_param["kernel_size"]), int(d_param["kernel_size"])) # (15,15)
        self.oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, t_krnl_sz)

        # ECC specific parameters
        if d_param["ecc_motion_type"] == "translation":
            self.i_warp_mode = cv.MOTION_TRANSLATION
        elif d_param["ecc_motion_type"] == "euclidean":
            self.i_warp_mode = cv.MOTION_EUCLIDEAN
        else:
            raise ValueError("Unsupported motion type")

        self.t_criteria = (
            cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT,
            int(d_param["ecc_num_iter"]),
            float(d_param["ecc_termination_eps"])
        )
        self.i_morph_niter = int(d_param["morph_num_iter"]) # 3
        self.na_bgr = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        # Piece-Wise ECC specific parameters
        self.i_nrow_tiles = int(d_param["pw_ecc_nrow_tiles"])
        self.i_ncol_tiles = int(d_param["pw_ecc_ncol_tiles"])
        self.i_border_sz =  int(d_param["pw_ecc_border_size"])
        self.f_max_shift = np.sqrt(2*((0.5 * self.i_border_sz)**2))

        if d_param["pw_ecc_border_type"] == "REFLECT":
            self.i_border_type = cv.BORDER_REFLECT
        elif d_param["pw_ecc_border_type"] == "REFLECT_101":
            self.i_border_type = cv.BORDER_REFLECT_101
        elif d_param["pw_ecc_border_type"] == "WRAP":
            self.i_border_type = cv.BORDER_WRAP
        else:
            raise ValueError("Unsupported border type")

        if d_param["pw_ecc_border_mode"] == "REPLICATE":
            self.i_border_mode = cv.BORDER_REPLICATE
        elif d_param["pw_ecc_border_mode"] == "CONSTANT":
            self.i_border_mode = cv.BORDER_CONSTANT
        else:
            raise ValueError("Unsupported border mode")

        # input frame and it's Piece-Wise representation.
        na_input = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.float32)
        self.oc_pw_input = CStiBordFrame(
            na_input,
            self.i_nrow_tiles,
            self.i_ncol_tiles,
            self.i_border_sz,
            self.i_border_type
        )

        # main data exchange interface for this class
        self.na_out     = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        self.na_out_reg = np.zeros([i_frame_h, i_frame_w], dtype=np.float32)

        self.d_REG = {}
        self.d_REG['PW_REG_corr_coef'] = []
        self.d_REG['PW_REG_inter_patch_dist'] = []
        self.d_REG['PW_REG_warp_matrix'] = []
        self.d_REG['PW_REG_not_converged'] = []
        self.d_REG['PW_REG_high_jumps'] = []

        # auxiliary stuff

        # the Piece-Wise version of the self.na_out_reg
        # NOTE that the self.na_out will be filled at the end of register_frame()
        # by calling cv.normalize() on the self.na_out_reg
        self.oc_pw_out_reg = CStiBordFrame(
            self.na_out_reg,
            self.i_nrow_tiles,
            self.i_ncol_tiles,
            self.i_border_sz,
            self.i_border_type
        )
        self.oc_pw_pre_reg = CStiBordFrame(
            self.na_out_reg,
            self.i_nrow_tiles,
            self.i_ncol_tiles,
            self.i_border_sz,
            self.i_border_type
        )

        # Output, piece-wise cross-correlation values.
        # Storage container for the first return argument of findTransformECC()
        self.na_pw_cc = np.zeros([self.i_nrow_tiles, self.i_ncol_tiles], np.float32)

        # Output, matrix of distances between patches in adjacent frames
        self.na_pw_dist = np.zeros([self.i_nrow_tiles, self.i_ncol_tiles], np.float32)

        # Output, matrix of booleans representing "warp flags"
        # each flag set to True if and only if the estimated shift between
        # adjacent patches is less than the maximal shift allowed: self.f_max_shift
        self.na_do_warp = np.zeros([self.i_nrow_tiles, self.i_ncol_tiles], np.bool)

        # Output, a tiled matrix, each tile have size 2x3 -
        # the warp matrix for each input tile.
        self.na_pw_wM = np.zeros([2 * self.i_nrow_tiles, 3 * self.i_ncol_tiles], np.float32)

        # tiled version of the warp matrix storage above
        self.oc_twM = CTiledFrame(self.na_pw_wM, self.i_nrow_tiles, self.i_ncol_tiles)

        # fill the tiled warp matrix storage with [2 x 3] eye matrices.
        # Not absolutely necessary, but useful for debugging...
        for ix, iy in np.ndindex(self.oc_twM.shape):
            self.oc_twM[ix, iy] = np.eye(2, 3, dtype=np.float32)
    #
    def __assign_all_outputs(self):
        self.oc_pw_out_reg.stitch()
        self.na_out_reg[...] = self.oc_pw_out_reg['inner']
        self.na_out[...] = cv.normalize(
            self.na_out_reg, None,
            alpha=0, beta=255,
            norm_type=cv.NORM_MINMAX,
            dtype=cv.CV_8U
        )
    #
    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 2:
            raise ValueError("Unexpected frame shape")

        self.oc_filter.process_frame(cv.normalize(na_input, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))
        self.na_bgr[...] = cv.morphologyEx(self.oc_filter.na_out, cv.MORPH_OPEN, self.oc_strel_kernel, iterations=self.i_morph_niter)

        if self.i_frame_id == 0:
            # copy input frame data into output storage container(s)
            self.oc_pw_out_reg['new'] = self.oc_filter.na_out - self.na_bgr
            for ix, iy in np.ndindex(self.oc_pw_out_reg.shape):
                self.oc_pw_out_reg[ix, iy] = self.oc_pw_out_reg[ix, iy]
            self.__assign_all_outputs()

            self.d_REG['PW_REG_corr_coef'].append(self.na_pw_cc.copy())
            self.d_REG['PW_REG_inter_patch_dist'].append(self.na_pw_dist.copy())
            self.d_REG['PW_REG_warp_matrix'].append(self.na_pw_wM.copy())
            self.i_frame_id += 1
            return

        self.oc_pw_input.clean()
        self.oc_pw_input['new'] = self.oc_filter.na_out - self.na_bgr
        self.na_do_warp.fill(False)

        for ix, iy in np.ndindex(self.oc_pw_input.shape):
            self.na_wM[...] = self.na_wMref[...]
            try:
                self.na_pw_cc[ix, iy], self.na_wM[...] = cv.findTransformECC(
                    self.oc_pw_out_reg[ix, iy],
                    self.oc_pw_input[ix, iy],
                    self.na_wM,
                    self.i_warp_mode,
                    self.t_criteria
                )
            except(cv.error):
                self.d_REG['PW_REG_not_converged'].append((self.i_frame_id, ix, iy))

            self.na_pw_dist[ix, iy] = np.linalg.norm(self.na_wM[:,-1] - self.oc_twM[ix, iy][:,-1])
            if self.na_pw_dist[ix, iy] < self.f_max_shift:
                self.na_do_warp[ix, iy] = True
            else:
                self.na_wM[:,-1] = 0
                self.d_REG['PW_REG_high_jumps'].append((self.i_frame_id, ix, iy))
            self.oc_twM[ix, iy] = self.na_wM[...]

        if b_verbose:
            print("frame_id: %i\tmax_shift: %.3f" % (self.i_frame_id, self.na_pw_dist.max()))

        self.d_REG['PW_REG_corr_coef'].append(self.na_pw_cc.copy())
        self.d_REG['PW_REG_inter_patch_dist'].append(self.na_pw_dist.copy())
        self.d_REG['PW_REG_warp_matrix'].append(self.na_pw_wM.copy())
        self.i_frame_id += 1
    #
    def register_frame(self, na_input=None):
        if self.i_frame_id == 0:
            raise ValueError("Unexpected method call. Call process_frame() first!")

        self.oc_pw_pre_reg.clean()
        self.oc_pw_out_reg.clean()

        if isinstance(na_input, type(None)):
            self.oc_pw_pre_reg['new'] = self.oc_filter.na_out - self.na_bgr
        else:
            if len(na_input.shape) != 2:
                raise ValueError("Unexpected frame shape")
            self.oc_pw_pre_reg['new'] = na_input

        if self.i_frame_id == 1:
            for ix, iy in np.ndindex(self.oc_pw_out_reg.shape):
                self.oc_pw_out_reg[ix, iy] = self.oc_pw_pre_reg[ix, iy]
            self.__assign_all_outputs()
            return

        for ix, iy in np.ndindex(self.oc_pw_out_reg.shape):
            if not self.na_do_warp[ix, iy]:
                self.oc_pw_out_reg[ix, iy] = self.oc_pw_pre_reg[ix, iy]
                continue
            self.oc_pw_out_reg[ix, iy] = cv.warpAffine(
                self.oc_pw_pre_reg[ix, iy],
                self.oc_twM[ix, iy],
                # tuple of (W x H) of the output image (patch in this case).
                # Must be a tuple. Notice the order (ncols x nrows)!
                (self.oc_pw_out_reg[ix, iy].shape[1], self.oc_pw_out_reg[ix, iy].shape[0]),
                flags=self.WARP_FLAGS,
                borderMode=self.i_border_mode
            )
        self.__assign_all_outputs()
    #
#
