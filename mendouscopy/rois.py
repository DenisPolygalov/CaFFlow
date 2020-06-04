#!/usr/bin/env python3


import math
import warnings
import numpy as np
import cv2 as cv


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


class CFrameWiseROIDetector(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        # frames are counted starting from zero, each time when the process_frame() method called.
        self._i_frame_cnt = -1
        self._PROJ_NUM = 2501
        self._MAX_NUM_OF_NO_ROI_FRAMES = 100
        self.f_circ_min = float(d_param['ROI_circularity_min'])
        self.f_circ_max = float(d_param['ROI_circularity_max'])
        self.f_area_min = int(d_param['ROI_area_min'])
        self.f_area_max = int(d_param['ROI_area_max'])
        self.i_thresh_drop = int(d_param['ROI_thresh_drop'])
        self.i_zero_roi_frame_cnt = 0
        # mask array, same size as the input frame, contain zeros or 255s, where
        # 255s correspond to ALL ROIs within processed frame (for internal usage)
        self._na_mask_8U = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        # list of ROI candidates (for internal usage)
        self._l_ROI_candidates = []
        # main data exchange interface for this class
        self.na_out = np.zeros([i_frame_h, i_frame_w], dtype=frame_dtype)
        # mask array containing values (0 ~ 0xFFFF) where
        # zeros correspond to out-of-ROIs area,
        # ones correspond to pixels belong to ROI number 1,
        # 2s correspond to pixels belong to ROI number 2 and so one...
        self.na_mask_16U = np.zeros([i_frame_h, i_frame_w], dtype=np.uint16)
        # all these lists are same length which is equal to number of ROIs
        # found (detected) in the current processed frame
        self.l_ROI_id = []     # ROI id. Same as in the self.na_mask_16U (not necessary the index of this list!)
        self.l_ROI_area = []   # Area value of the ROI
        self.l_ROI_circ = []   # Circularity value
        self.l_ROI_CoidXY = [] # Centroid (x,y) coordinates
        self.l_ROI_CoMxy  = [] # Center of Mass (x,y) coordinates
        self.l_ROI_fluo_sum  = [] # total fluorescence per ROI
        self.l_ROI_fluo_mean = [] # mean fluorescence per ROI
        self.l_ROI_SNR_dB = [] # signal-to-noise ratio in decibels
        # cumulative storage for the data in self.l_ROI_* lists above
        self.d_ROI = {}
        self.d_ROI['ROI_id'] = []
        self.d_ROI['ROI_area'] = []
        self.d_ROI['ROI_circ'] = []
        self.d_ROI['ROI_CoidXY'] = []
        self.d_ROI['ROI_CoMxy'] = []
        self.d_ROI['ROI_fluo_sum'] = []
        self.d_ROI['ROI_fluo_mean'] = []
        self.d_ROI['ROI_SNR_dB'] = []
    #
    def process_frame(self, na_input, b_verbose=False):
        self._i_frame_cnt += 1
        i_thr_min = 127
        i_thr_max = 255
        self._na_mask_8U.fill(0)
        self.na_mask_16U.fill(0)
        self._l_ROI_candidates.clear()
        self.l_ROI_id.clear()
        self.l_ROI_area.clear()
        self.l_ROI_circ.clear()
        self.l_ROI_CoidXY.clear()
        self.l_ROI_CoMxy.clear()
        self.l_ROI_fluo_sum.clear()
        self.l_ROI_fluo_mean.clear()
        self.l_ROI_SNR_dB.clear()
        # Copy all data from input frame to output frame arrays.
        # Later on the output array will be masked with self._na_mask_8U
        # zeroing all non-ROIs pixels of the self.na_out array
        self.na_out[...] = na_input[...]
        b_new_ROI_found = False
        i_safeguard_cnt = 0

        # check data type of the input frame and normalize it
        # to 8 bit because 8 bit depth is required by cv.findContours()
        if type(na_input.dtype) != cv.CV_8U:
            na_frame_8U = cv.normalize(na_input, None, alpha=0, beta=(2**8-1), norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)
        else:
            na_frame_8U = na_input

        # perform preliminary ROI search, save results in self._na_mask_8U
        # The self._l_ROI_candidates is used for temporary storage
        while(True):
            i_safeguard_cnt += 1
            if i_safeguard_cnt >= 0xFFFF:
                raise RuntimeError("Infinite loop safeguard overflow! Your input data have unexpected properties!")

            # get thresholded image
            _, na_thresh_frame = cv.threshold(na_frame_8U, i_thr_min, i_thr_max, 0)

            # get list of contours from the thresholded image
            _, l_contours, _ = cv.findContours(na_thresh_frame, cv.RETR_TREE, cv.CHAIN_APPROX_NONE)

            b_new_ROI_found = False
            for na_contour in l_contours:
                f_perimeter = cv.arcLength(na_contour, True)
                if f_perimeter < 1: continue
                f_area = cv.contourArea(na_contour)
                f_circularity = 4 * math.pi * ( f_area / (f_perimeter**2) )
                if (self.f_circ_min < f_circularity <= self.f_circ_max) and \
                   (self.f_area_min < f_area        <  self.f_area_max):
                    b_new_ROI_found = True
                    self._l_ROI_candidates.append(na_contour)
                    # draw single FILLED contour inside of the self._na_mask_8U RIGHT AFTER you append() it!
                    cv.drawContours(self._na_mask_8U, self._l_ROI_candidates, len(self._l_ROI_candidates)-1, 255, thickness=cv.FILLED)

            if b_new_ROI_found is False:
                # no more contours found, so interrupt the loop
                break
            else:
                # decrease threshold
                i_thr_max = i_thr_min
                i_thr_min = i_thr_max - self.i_thresh_drop
        # print("len(l_contours)=", len(l_contours), "(candidates)")

        # apply the mask to copy of the input frame
        t_noise_pix_idxs = np.where(self._na_mask_8U == 0)
        f_noise_std = np.std(self.na_out[t_noise_pix_idxs])
        self.na_out[t_noise_pix_idxs] = 0

        # perform final ROI search by using the self._na_mask_8U as input
        _, l_contours, _ = cv.findContours(self._na_mask_8U, cv.RETR_TREE, cv.CHAIN_APPROX_NONE)

        for i_contid, _ in enumerate(l_contours):
            f_perimeter = cv.arcLength(l_contours[i_contid], True)
            if f_perimeter < 1e-3:
                raise ValueError("Algorithm error! Unexpected input data!")
            f_area = cv.contourArea(l_contours[i_contid])
            f_circularity = 4 * math.pi * ( f_area / (f_perimeter**2) )

            if f_area < self.f_area_min or f_area >= self.f_area_max: continue
            if f_circularity < self.f_circ_min or f_circularity >= self.f_circ_max: continue

            i_roi_id = self._PROJ_NUM + i_contid

            # draw a single filled contour inside of the self.na_mask_16U
            cv.drawContours(self.na_mask_16U, l_contours, i_contid, i_roi_id, thickness=cv.FILLED)

            # extract a tuple of (x,y) indices belong to the ROI
            t_idx_xy = np.where(self.na_mask_16U == i_roi_id) # dtype == np.int64 (!)

            # total fluorescence value of the ROI (integer by definition)
            na_fluo_per_pixel = self.na_out[t_idx_xy]
            i_fluo_per_ROI = na_fluo_per_pixel.sum()

            # (x, y) coordinates of Centroid of the ROI
            f_CoidX = t_idx_xy[0].sum() / t_idx_xy[0].size
            f_CoidY = t_idx_xy[1].sum() / t_idx_xy[1].size

            # (x, y) coordinates of Center of Mass (fluorescence treated as density) of the ROI
            f_CoMx = (t_idx_xy[0] * na_fluo_per_pixel).sum() / i_fluo_per_ROI
            f_CoMy = (t_idx_xy[1] * na_fluo_per_pixel).sum() / i_fluo_per_ROI

            # calculate and store area, circularity, CoM etc. values of each ROI
            self.l_ROI_id.append(i_roi_id)
            self.l_ROI_area.append(f_area)
            self.l_ROI_circ.append(f_circularity)
            self.l_ROI_CoidXY.append([f_CoidX, f_CoidY])
            self.l_ROI_CoMxy.append([f_CoMx, f_CoMy])
            self.l_ROI_fluo_sum.append(i_fluo_per_ROI)
            self.l_ROI_fluo_mean.append(na_fluo_per_pixel.mean())
            self.l_ROI_SNR_dB.append( 20 * np.log10(self.l_ROI_fluo_mean[-1] / f_noise_std) )

        if len(self.l_ROI_id) == 0:
            self.i_zero_roi_frame_cnt += 1
        else:
            self.i_zero_roi_frame_cnt = 0
        if self.i_zero_roi_frame_cnt >= self._MAX_NUM_OF_NO_ROI_FRAMES:
            s_msg = "Unable to find any good ROIs in %i sequential frames!" % self._MAX_NUM_OF_NO_ROI_FRAMES
            warnings.warn(s_msg)

        self.d_ROI['ROI_id'].append(        np.array(self.l_ROI_id)        )
        self.d_ROI['ROI_area'].append(      np.array(self.l_ROI_area)      )
        self.d_ROI['ROI_circ'].append(      np.array(self.l_ROI_circ)      )
        self.d_ROI['ROI_CoidXY'].append(    np.array(self.l_ROI_CoidXY)    )
        self.d_ROI['ROI_CoMxy'].append(     np.array(self.l_ROI_CoMxy)     )
        self.d_ROI['ROI_fluo_sum'].append(  np.array(self.l_ROI_fluo_sum)  )
        self.d_ROI['ROI_fluo_mean'].append( np.array(self.l_ROI_fluo_mean) )
        self.d_ROI['ROI_SNR_dB'].append(    np.array(self.l_ROI_SNR_dB)    )

        if b_verbose:
            for i_roi_cnt in range(len(self.l_ROI_id)):
                i_CoMx = int(np.ceil(self.l_ROI_CoMxy[i_roi_cnt][1]))
                i_CoMy = int(np.ceil(self.l_ROI_CoMxy[i_roi_cnt][0]))
                f_CoM_Coid_dist = \
                np.sqrt((self.l_ROI_CoMxy[i_roi_cnt][0] - self.l_ROI_CoidXY[i_roi_cnt][0])**2 + \
                        (self.l_ROI_CoMxy[i_roi_cnt][1] - self.l_ROI_CoidXY[i_roi_cnt][1])**2)
                print("frame: %i\tROI_id: %i\tCoM(x,y): (%i %i)\tCoM<->Coid: %.3f\tAREA: %.4i\tCIRC: %.2f\tSNR: %.2f\tFLUO: %i" % (\
                    self._i_frame_cnt,
                    self.l_ROI_id[i_roi_cnt],
                    i_CoMx, i_CoMy, f_CoM_Coid_dist,
                    self.l_ROI_area[i_roi_cnt],
                    self.l_ROI_circ[i_roi_cnt],
                    self.l_ROI_SNR_dB[i_roi_cnt],
                    self.l_ROI_fluo_mean[i_roi_cnt]
                ))
            if len(self.l_ROI_id) > 0: print()
        #
    #
#


class CMovieWiseROIPicker(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.f_SNR_thr = float(d_param['ROI_SNR_discard_threshold'])
        self.i_max_ovl = int(d_param['ROI_max_overlap'])
        self._b_pickup_finalized = False
        self._i_nframes_proc = 0 # number of frames processed (number of times the pickup() method was called)
        self._i_mask_id = 0
        self.t_bgr_idx = None
        # BINARY mask of SINGLE ROI - a candidate for collection
        self.na_mask_8Us = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        # BINARY mask of ALL already collected ROIs
        self.na_mask_8UA = np.zeros([i_frame_h, i_frame_w], dtype=np.uint8)
        # main data exchange interface for this class
        # masks of ALL already collected ROIs, pixels of each ROI == self._i_mask_id
        self.na_mask_16U = np.zeros([i_frame_h, i_frame_w], dtype=np.uint16)
        # list of dictionaries - collected ROIs
        self.l_ROI = []
        # raw and post-processed fluorescence traces
        self.na_fluo_raw_mean = None
        self.na_fluo_raw_sum = None
        self.na_fluo_dFF = None
        self.na_fluo_bgr = None
        self.d_FLUO = {}

    def __test(self, i_frame_id, ii, d_roi_data, na_1f_mask):
        f_SNR_dB = d_roi_data['ROI_SNR_dB'][i_frame_id][ii]
        i_roi_id = d_roi_data['ROI_id'][i_frame_id][ii]
        if f_SNR_dB > self.f_SNR_thr:
            self.na_mask_8Us.fill(0)
            self.na_mask_8Us[np.where(na_1f_mask == i_roi_id)] = 1
            na_mask_ovl = cv.bitwise_and(self.na_mask_8Us, self.na_mask_8UA)
            i_nz = np.count_nonzero(na_mask_ovl)
            if i_nz <= self.i_max_ovl:
                if i_nz > 0:
                    self.na_mask_8Us[np.where(na_mask_ovl > 0)] = 0
                return True
        return False

    def __append(self, i_frame_id, ii, d_roi_data_in):
        self._i_mask_id += 1
        t_non_ovl_roi_idx = np.where(self.na_mask_8Us > 0)
        self.na_mask_16U[t_non_ovl_roi_idx] = self._i_mask_id
        self.na_mask_8UA[t_non_ovl_roi_idx] = 1

        d_roi_data_out = {}
        d_roi_data_out['frame_id'] = i_frame_id
        d_roi_data_out['mask_id'] = self._i_mask_id
        t_mask_pix_idx = np.where(self.na_mask_16U == d_roi_data_out['mask_id'])
        d_roi_data_out['mask_pix_idx'] = (t_mask_pix_idx[0].astype(np.uint16), t_mask_pix_idx[1].astype(np.uint16))
        for k_in in d_roi_data_in.keys():
            if k_in not in d_roi_data_out:
                d_roi_data_out[k_in] = d_roi_data_in[k_in][i_frame_id][ii]
        self.l_ROI.append(d_roi_data_out)

        if i_frame_id < 20 and len(self.l_ROI) != self.na_mask_16U.max():
            raise ValueError("Sanity check failed. Check the data you passing into this object.")

    def pickup(self, i_frame_id, d_roi_data, na_1f_mask):
        """
        Accept *lists* of ROI parameters detected within a *single* frame.
        Test each ROI by using various criteria and append
        to the self.l_ROI or reject.
        """
        if i_frame_id != self._i_nframes_proc:
            raise ValueError("Gap in subsequent calls detected.")
        self._i_nframes_proc += 1

        i_nrois_in = len(d_roi_data['ROI_id'][i_frame_id]) # number of input ROIs

        for ii in range(i_nrois_in):
            if self.__test(   i_frame_id, ii, d_roi_data, na_1f_mask):
                self.__append(i_frame_id, ii, d_roi_data)

    def finalize_pickup(self):
        # allocate storage arrays for fluorescence traces
        self.na_fluo_raw_mean = np.zeros( [ self._i_nframes_proc, len(self.l_ROI) ], dtype=np.float32 )
        self.na_fluo_raw_sum  = np.zeros( [ self._i_nframes_proc, len(self.l_ROI) ], dtype=np.float32 )
        self.na_fluo_dFF      = np.zeros( [ self._i_nframes_proc, len(self.l_ROI) ], dtype=np.float32 )
        self.na_fluo_bgr = np.zeros(self._i_nframes_proc, dtype=np.float32)
        self.t_bgr_idx  = np.where(self.na_mask_16U == 0)
        self._i_nframes_proc = 0 # RESET THE FRAME COUNTER
        self._b_pickup_finalized = True

    def extract_fluo_from_frame(self, na_in):
        if not self._b_pickup_finalized:
            raise ValueError("Inappropriate method calling sequence detected. Call finalize_pickup() first.")
        if len(na_in.shape) != 2:
            raise ValueError("Unexpected frame shape")
        if na_in.shape[0] != self.i_frame_h:
            raise ValueError("Unexpected frame height")
        if na_in.shape[1] != self.i_frame_w:
            raise ValueError("Unexpected frame width")
        for ii in range(len(self.l_ROI)):
            self.na_fluo_raw_mean[self._i_nframes_proc, ii] = na_in[ self.l_ROI[ii]['mask_pix_idx'] ].mean()
            self.na_fluo_raw_sum[ self._i_nframes_proc, ii] = na_in[ self.l_ROI[ii]['mask_pix_idx'] ].sum()
        self.na_fluo_bgr[self._i_nframes_proc] = na_in[self.t_bgr_idx].mean()
        self._i_nframes_proc += 1

    def finalize_fluo(self):
        if not self._b_pickup_finalized:
            raise ValueError("Inappropriate method calling sequence detected. Call finalize_pickup() first.")
        if (self.na_fluo_bgr < 1.0).any():
            raise ValueError("Small background level detected. You probably doing something wrong.")
        for ii in range(len(self.l_ROI)):
            na_dFF = (self.na_fluo_raw_mean[...,ii] - self.na_fluo_bgr) / self.na_fluo_bgr
            if na_dFF.min() < 0:
                na_dFF -= na_dFF.min()
            self.na_fluo_dFF[...,ii] = na_dFF
        #
        self.d_FLUO['ROI_mask'] = self.na_mask_16U
        self.d_FLUO['ROI_data'] = self.l_ROI
        self.d_FLUO['raw_mean'] = self.na_fluo_raw_mean
        self.d_FLUO['raw_sum'] = self.na_fluo_raw_sum
        self.d_FLUO['dFF'] = self.na_fluo_dFF
        self.d_FLUO['background'] = self.na_fluo_bgr
    #
#


class CMovieWiseWeightedROIPicker(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.i_frame_h = i_frame_h
        self.i_frame_w = i_frame_w
        self.f_SNR_thr = float(d_param['ROI_SNR_discard_threshold'])
        self.f_jaccard_thr = float(d_param['wROI_jaccard_threshold'])
        self.f_c2cds_thr = float(d_param['wROI_inter_centroid_threshold'])
        self._HASH_NONCE = +100500
        self._b_pickup_finalized = False
        self._i_nframes_proc = 0 # number of frames processed (number of times the pickup() method was called)
        self.na_wROI_canvas = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.float32)
        self._t_bgr_idx = None

        self.d_wROI_hashes  = {}
        self.d_wROI_CoidXY  = {}
        self.d_wROI_pix_idx = {}
        self.d_wROI_weights = {}

        self.l_wROI_jaccs = []
        self.l_wROI_c2cds = []
        self.l_wROI_idxs  = []
        self.i_new_roi_id = 0

        # main data exchange interface for this class

        # all weighted ROIs blended into a single frame
        self.na_wROI_blend_raw  = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.float32)
        self.na_wROI_blend_norm = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.float32)
        self.na_wROI_residual = np.zeros([self.i_frame_h, self.i_frame_w], dtype=np.float32)
        self.i_residual_roi_cnt = 0
        # list of (scalar) ROIs data
        # this will be also assigned as 'ROI_data' key in the self.d_FLUO
        self.l_ROI = []

        # raw and post-processed fluorescence traces
        self.na_fluo_raw_mean = None
        self.na_fluo_raw_sum = None
        self.na_fluo_dFF = None
        self.na_fluo_bgr = None
        self.d_FLUO = {}

    def __pickup(self, i_frame_id, ii, d_roi_data_in, na_1f_mask):
        na_roi_centroid = d_roi_data_in['ROI_CoidXY'][i_frame_id][ii]
        t_roi_idx = np.where(na_1f_mask == d_roi_data_in['ROI_id'][i_frame_id][ii])

        na_new_hash = np.array(t_roi_idx[0]) # dtype == np.int64
        na_new_hash *= self._HASH_NONCE
        na_new_hash += t_roi_idx[1]
        st_new_hash  = set(na_new_hash.astype(np.uint32))
        self.i_new_roi_id = int(round(na_roi_centroid[0]) * self._HASH_NONCE + round(na_roi_centroid[1]))
        s_new_roi_id = str(self.i_new_roi_id)

        # this is the first ROI we see, so accept it and return.
        if len(self.d_wROI_hashes) == 0:
            self.d_wROI_hashes[s_new_roi_id] = st_new_hash
            self.d_wROI_CoidXY[s_new_roi_id] = na_roi_centroid
            self.d_wROI_pix_idx[s_new_roi_id] = (t_roi_idx[0].astype(np.uint16), t_roi_idx[1].astype(np.uint16))
            self.d_wROI_weights[s_new_roi_id] = np.ones(t_roi_idx[0].shape, dtype=np.float32)
            self.na_wROI_blend_raw[t_roi_idx] += 1
            self.__append(i_frame_id, ii, d_roi_data_in) # call this AFTER updating self.d_wROI_*
            return

        # we already have some ROIs accepted, so compare the new one with each of them
        # by using Jaccard index (0~1) and inter-centroid distance (in pixels) in order
        # to decide - treat this ROI as new one or overlay it with one of existed.
        self.l_wROI_jaccs.clear()
        self.l_wROI_c2cds.clear()
        self.l_wROI_idxs.clear()

        for _, (s_old_roi_id, st_old_hash) in enumerate(self.d_wROI_hashes.items()):
            self.l_wROI_jaccs.append(len(st_old_hash.intersection(st_new_hash)) / len(st_old_hash.union(st_new_hash)))
            self.l_wROI_c2cds.append(np.linalg.norm(na_roi_centroid - self.d_wROI_CoidXY[s_old_roi_id]))
            self.l_wROI_idxs.append(s_old_roi_id)

        i_max_jacc_idx = np.argmax(self.l_wROI_jaccs)
        f_max_jacc = self.l_wROI_jaccs[i_max_jacc_idx]
        f_c2cds    = self.l_wROI_c2cds[i_max_jacc_idx]
        s_roi_id   = self.l_wROI_idxs[i_max_jacc_idx]

        # the Jaccard index is very small, so treat this ROI as a new one
        if f_max_jacc < 1e-3:
            self.d_wROI_hashes[s_new_roi_id] = st_new_hash
            self.d_wROI_CoidXY[s_new_roi_id] = na_roi_centroid
            self.d_wROI_pix_idx[s_new_roi_id] = (t_roi_idx[0].astype(np.uint16), t_roi_idx[1].astype(np.uint16))
            self.d_wROI_weights[s_new_roi_id] = np.ones(t_roi_idx[0].shape, dtype=np.float32)
            self.na_wROI_blend_raw[t_roi_idx] += 1
            self.__append(i_frame_id, ii, d_roi_data_in) # call this AFTER updating self.d_wROI_*

        elif f_max_jacc > self.f_jaccard_thr and f_c2cds < self.f_c2cds_thr:
            # update existing ROI
            self.na_wROI_canvas.fill(0)
            self.na_wROI_canvas[self.d_wROI_pix_idx[s_roi_id]] = self.d_wROI_weights[s_roi_id][...]
            self.na_wROI_canvas[t_roi_idx] += 1

            # re-calculate self.d_wROI_* stuff by using updated ROI shape
            # BUT KEEP the s_roi_id and it's centroid value.
            # < *** re-use t_roi_idx, na_new_hash etc here *** >
            t_roi_idx = np.where(self.na_wROI_canvas > 0)

            na_new_hash = np.array(t_roi_idx[0]) # dtype == np.int64
            na_new_hash *= self._HASH_NONCE
            na_new_hash += t_roi_idx[1]
            st_new_hash  = set(na_new_hash.astype(np.uint32))

            self.d_wROI_hashes[s_roi_id] = st_new_hash
            self.d_wROI_pix_idx[s_roi_id] = (t_roi_idx[0].astype(np.uint16), t_roi_idx[1].astype(np.uint16))
            self.d_wROI_weights[s_roi_id] = self.na_wROI_canvas[t_roi_idx]
            self.na_wROI_blend_raw[t_roi_idx] += 1
        else:
            self.na_wROI_residual[t_roi_idx] += 1
            self.i_residual_roi_cnt += 1

    def __test(self, i_frame_id, ii, d_roi_data_in, na_1f_mask):
        if d_roi_data_in['ROI_SNR_dB'][i_frame_id][ii] > self.f_SNR_thr:
            return True
        # The place for additional tests of each new ROI
        return False

    def __append(self, i_frame_id, ii, d_roi_data):
        d_roi_data_out = {}
        d_roi_data_out['frame_id'] = i_frame_id
        d_roi_data_out['mask_id'] = self.i_new_roi_id
        d_roi_data_out['mask_pix_idx'] = self.d_wROI_pix_idx[str(self.i_new_roi_id)]
        self.l_ROI.append(d_roi_data_out)

        if i_frame_id < 20 and len(self.l_ROI) != len(self.d_wROI_hashes):
            raise ValueError("Sanity check failed. Check the data you passing into this object.")

    def pickup(self, i_frame_id, d_roi_data, na_1f_mask):
        """
        Accept dictionary of *lists* plural(!) of ROI parameters
        detected within a *single* frame.
        Test each ROI by using various criterias and append
        to the self... or reject.
        """
        if i_frame_id != self._i_nframes_proc:
            raise ValueError("Gap in subsequent calls detected.")
        self._i_nframes_proc += 1

        i_nrois_in = len(d_roi_data['ROI_id'][i_frame_id]) # number of input ROIs

        for ii in range(i_nrois_in):
            if self.__test(   i_frame_id, ii, d_roi_data, na_1f_mask):
                self.__pickup(i_frame_id, ii, d_roi_data, na_1f_mask)

    def finalize_pickup(self):
        # allocate storage arrays for fluorescence traces
        self.na_fluo_raw_mean = np.zeros( [ self._i_nframes_proc, len(self.d_wROI_hashes) ], dtype=np.float32 )
        self.na_fluo_raw_sum  = np.zeros( [ self._i_nframes_proc, len(self.d_wROI_hashes) ], dtype=np.float32 )
        self.na_fluo_dFF      = np.zeros( [ self._i_nframes_proc, len(self.d_wROI_hashes) ], dtype=np.float32 )
        self.na_fluo_bgr = np.zeros(self._i_nframes_proc, dtype=np.float32)
        self._t_bgr_idx = np.where(self.na_wROI_blend_raw == 0)

        # normalize wROI weight values to (0 ~ 1) range
        for _, (s_key, na_wROI_weights) in enumerate(self.d_wROI_weights.items()):
            na_wROI_weights /= na_wROI_weights.max()

        for _, (s_key, t_pix_idx) in enumerate(self.d_wROI_pix_idx.items()):
            self.na_wROI_blend_norm[t_pix_idx] += self.d_wROI_weights[s_key]

        for ii in range(len(self.l_ROI)):
            d_roi_data_out = self.l_ROI[ii]
            d_roi_data_out['mask_weights'] = self.d_wROI_weights[str(d_roi_data_out['mask_id'])]
            self.l_ROI[ii] = d_roi_data_out

        # self.na_wROI_residual /= self.i_residual_roi_cnt
        self._i_nframes_proc = 0 # RESET THE FRAME COUNTER
        self._b_pickup_finalized = True

    def extract_fluo_from_frame(self, na_in):
        if not self._b_pickup_finalized:
            raise ValueError("Inappropriate method calling sequence detected. Call finalize_pickup() first.")
        if len(na_in.shape) != 2:
            raise ValueError("Unexpected frame shape")
        if na_in.shape[0] != self.i_frame_h:
            raise ValueError("Unexpected frame height")
        if na_in.shape[1] != self.i_frame_w:
            raise ValueError("Unexpected frame width")

        for ii in range(len(self.l_ROI)):
            s_key = str(self.l_ROI[ii]['mask_id'])
            na_tmp = na_in[self.d_wROI_pix_idx[s_key]].astype(np.float32)
            na_tmp *= self.d_wROI_weights[s_key]
            self.na_fluo_raw_mean[self._i_nframes_proc, ii] = na_tmp.mean()
            self.na_fluo_raw_sum[ self._i_nframes_proc, ii] = na_tmp.sum()

        self.na_fluo_bgr[self._i_nframes_proc] = na_in[self._t_bgr_idx].mean()
        self._i_nframes_proc += 1

    def finalize_fluo(self):
        if not self._b_pickup_finalized:
            raise ValueError("Inappropriate method calling sequence detected. Call finalize_pickup() first.")
        if (self.na_fluo_bgr < 1.0).any():
            raise ValueError("Small background level detected. You probably doing something wrong.")
        for ii in range(len(self.d_wROI_hashes)):
            na_dFF = (self.na_fluo_raw_mean[...,ii] - self.na_fluo_bgr) / self.na_fluo_bgr
            if na_dFF.min() < 0:
                na_dFF -= na_dFF.min()
            self.na_fluo_dFF[...,ii] = na_dFF
        #
        self.d_FLUO['wROI_blend_raw']  = self.na_wROI_blend_raw
        self.d_FLUO['wROI_blend_norm'] = self.na_wROI_blend_norm
        self.d_FLUO['wROI_residual'] = self.na_wROI_residual
        self.d_FLUO['ROI_data'] = self.l_ROI
        self.d_FLUO['raw_mean'] = self.na_fluo_raw_mean
        self.d_FLUO['raw_sum'] = self.na_fluo_raw_sum
        self.d_FLUO['dFF'] = self.na_fluo_dFF
        self.d_FLUO['background'] = self.na_fluo_bgr
    #
#

