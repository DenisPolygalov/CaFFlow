#!/usr/bin/env python3

import os
import sys
import warnings
from collections import deque

import cv2 as cv
import numpy as np

"""
Copyright (C) 2018,2019 Lilia Evgeniou, Denis Polygalov
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

"""
An example of parameters for detection (for mendouscopy.ini file):
[behavior]
# Blob Detector parameters

# Change thresholds
blobdet_minThreshold: 10
blobdet_maxThreshold: 200

# Filter by Area
blobdet_filterByArea: yes
blobdet_minArea: 300
blobdet_maxArea: 700

# Filter by Circularity
blobdet_filterByCircularity: yes
blobdet_minCircularity: 0.1

# Filter by Convexity
blobdet_filterByConvexity: yes
blobdet_minConvexity: 0.5

# Filter by Inertia
blobdet_filterByInertia: no
blobdet_minInertiaRatio: 0.8

# Filter by light or dark color
blobdet_filterByColor: yes
# finds light colored blobs
blobdet_blobColor: 255

# detect_position method minmax of size of blob made by LED
# should be changed if different size blob
detpos_min_keypoint_sz: 15
detpos_max_keypoint_sz: 35

# color channel to view gray scale
# used for detection of position; can be 0, 1, or 2
color_channel: 2
"""


class CBehavPositionDetector(object):
    def __init__(self, oc_param):
        oc_blob_detector_params = cv.SimpleBlobDetector_Params()

        # include parameters from ini file

        # Threshold
        oc_blob_detector_params.minThreshold      = int(oc_param["blobdet_minThreshold"])
        oc_blob_detector_params.maxThreshold      = int(oc_param["blobdet_maxThreshold"])

        # Area
        oc_blob_detector_params.filterByArea      = oc_param.getboolean("blobdet_filterByArea")
        oc_blob_detector_params.minArea           = int(oc_param["blobdet_minArea"])
        oc_blob_detector_params.maxArea           = int(oc_param["blobdet_maxArea"])
        # Circularity
        oc_blob_detector_params.filterByCircularity = oc_param.getboolean("blobdet_filterByCircularity")
        oc_blob_detector_params.minCircularity      = float(oc_param["blobdet_minCircularity"])
        # Convexity
        oc_blob_detector_params.filterByConvexity = oc_param.getboolean("blobdet_filterByConvexity")
        oc_blob_detector_params.minConvexity      = float(oc_param["blobdet_minConvexity"])
        # Inertia
        oc_blob_detector_params.filterByInertia   = oc_param.getboolean("blobdet_filterByInertia")
        oc_blob_detector_params.minInertiaRatio   = float(oc_param["blobdet_minInertiaRatio"])
        # Color
        oc_blob_detector_params.filterByColor     = oc_param.getboolean("blobdet_filterByColor")
        oc_blob_detector_params.blobColor         = int(oc_param["blobdet_blobColor"])

        self.oc_blob_detector = cv.SimpleBlobDetector_create(oc_blob_detector_params)

        self.i_min_kp_sz = int(oc_param["detpos_min_keypoint_sz"])
        self.i_max_kp_sz = int(oc_param["detpos_max_keypoint_sz"])

        # used for detection
        self.i_c_channel = int(oc_param["color_channel"])  # = 2

        self.i_pos_history_depth = int(oc_param["pos_history_depth"])
        self.f_pos_max_jump_pixels = float(oc_param["pos_max_jump_pixels"])

        self.l_call_cnt = []
        self.l_kp_id    = []
        self.l_kp_size  = []
        self.l_position = []

        self.i_call_cnt = 0
        self.i_fail_cnt = 0

        # main data exchange interface for this class
        self.d_POS = {}
    #


    def detect_position(self, na_input, b_verbose=False):
        """
        Detects LED light where mouse is in behaviour videos
        by detecting blob on "red" gray scale image.
        :param na_input: numpy array of frame image
        :param detector: cv.SimpleBlobDetector whose parameters are already defined
        :return: the best estimated coordinates of the center of the LED light circle.
                 (None, None) if no LED light detected
        Function also changes self.l_call_cnt, self.l_kp_id, self.l_kp_size,
        self.l_position, and self.i_call_cnt (adds 1 to it).
        - appends all possible keypoints found into lists.
        Later on, will make ndarray with a matrix as follows:
            ______________________________________________________
            | l_call_cnt | l_kp_id | l_kp_size | x_coor | y_coor |
            |     0      |    0    |   20.4    |  15.8  |  19.3  | <- only 1 kp found
            |     1      |    0    |   25.2    |  12.4  |  20.5  | <- 2 kps found
            |     1      |    1    |   27.5    |  50.3  |  94.1  |
            |     2      |    0    |   NaN     |  NaN   |  NaN   | <- handles no kp found
            .            .         .           .        .        .
            .            .         .           .   l_position    .
            .            .         .           .        .        .
        """

        # make the LED stand out brighter by converting to red gray scale
        # finds key points
        keypoints = self.oc_blob_detector.detect(na_input[:, :, self.i_c_channel])

        # if no key points are found, will append what is needed into lists,
        # and will return (None, None)
        if len(keypoints) == 0:
            if b_verbose:
                print("WARNING: failed to detect any key points. Check your detection parameters.")
            self.l_call_cnt.append(self.i_call_cnt)
            self.l_kp_id.append(0)
            self.l_kp_size.append(np.nan)
            self.l_position.append([np.nan, np.nan])
            # add 1 to call_cnt, which keeps track of frame number
            self.i_call_cnt += 1
            self.i_fail_cnt += 1
            return (None, None)

        if b_verbose:
            for idx_kp, kp in enumerate(keypoints):
                print("call_id=%i\tkeypoint: id=%i\tsize=%.3f\tx=%.3f\ty=%.3f" % \
                      (self.i_call_cnt, idx_kp, kp.size, kp.pt[0], kp.pt[1]))

        # keeps one set of estimated coordinates (in this case, first keypoint)
        kp_xcoor, kp_ycoor = None, None
        # finds keypoints of right size,
        # and appends all into lists if more than one found.
        for idx_kp, kp in enumerate(keypoints):
            if self.i_min_kp_sz < kp.size < self.i_max_kp_sz:
                # keeps set of estimated coordinates
                if idx_kp == 0:
                    kp_xcoor = kp.pt[0]
                    kp_ycoor = kp.pt[1]
                # appends to lists
                self.l_call_cnt.append(self.i_call_cnt)
                self.l_kp_id.append(idx_kp)
                self.l_kp_size.append(kp.size)
                self.l_position.append([kp.pt[0], kp.pt[1]])

        # returning when keypoints found
        if (kp_xcoor, kp_ycoor) != (None, None):
            # add 1 to call_cnt, which keeps track of frame number
            self.i_call_cnt += 1
            return (kp_xcoor, kp_ycoor)

        # returning when a keypoint of the right size is not found.
        # appends what is needed to lists,
        # and returns (None, None)
        self.l_call_cnt.append(self.i_call_cnt)
        self.l_kp_id.append(0)
        self.l_kp_size.append(np.nan)
        self.l_position.append([np.nan, np.nan])
        # add 1 to call_cnt, which keeps track of frame number
        self.i_call_cnt += 1
        self.i_fail_cnt += 1
        return (None, None)
    #


    def finalize_detection(self):
        self.d_POS["call_cnt_raw"]     = np.array(self.l_call_cnt, dtype=np.int32)
        self.d_POS["keypoint_id_raw"]  = np.array(self.l_kp_id,    dtype=np.int32)
        self.d_POS["keypoint_sz_raw"]  = np.array(self.l_kp_size,  dtype=np.float)
        self.d_POS["position_rel_raw"] = np.array(self.l_position, dtype=np.float)
        self.d_POS["position_rel"] = remove_extra_keypoints(
            self.d_POS["position_rel_raw"],
            self.d_POS["call_cnt_raw"],
            self.i_pos_history_depth,
            self.f_pos_max_jump_pixels
        )
    #


    def get_success_rate(self):
        if self.i_fail_cnt == 0:
            return 100.0
        else:
            return 100.0 - (self.i_fail_cnt * 100.0) / self.i_call_cnt
    #


    def draw_cross(self, t_xy, na_input, i_sz=10, t_color=(225, 255, 255)):
        """
        Modifies numpy array of image directly to draw a cross at coordinates t_xy

        * TO REMEMBER: The array's shape is organised into: (rows, columns, depth)
                       so the array's "coordinates" are (y, x)
                       Hence, coordinate values must be flipped.
                       In addition, point (0, 0) is at top left corner.
                       x values increase to the right ->
                       y values increase to the bottom |
                                                       v

        :param t_xy: coordinate tuple (x, y)
        :param na_input: numpy array of frame image
        :param i_sz: size of cross (in pixels)
        :param t_color: color of cross
        :return: this function will directly modify the numpy array
        """

        # handles when detector returns (None, None); returns unmodified image
        if len(t_xy) != 2:    return na_input
        if t_xy[0] == None:   return na_input
        if t_xy[1] == None:   return na_input
        if np.isnan(t_xy[0]): return na_input
        if np.isnan(t_xy[1]): return na_input

        # horizontal and vertical coordinates
        # e.g. (300, 50), but in numpy array, it is first 50 rows, then 300 cols
        i_hcoor, i_vcoor = map(int, t_xy)

        # horizontal and vertical size of array
        # na_input.shape = (101, 624, 3)
        i_vsz, i_hsz, *_ = na_input.shape  # i_vsz: vertical width of image (around 100),
                                           # i_hsz: horizontal length of image (around 600 pixels)

        # size of cross on top, bottom, left, right
        # if cross at the edge of image, modify to partial cross
        i_sz_t = i_vcoor if i_vcoor - i_sz < 0 else i_sz
        i_sz_b = abs(i_vsz - i_vcoor) if i_vcoor + i_sz > i_vsz else i_sz
        i_sz_l = i_hcoor if i_hcoor - i_sz < 0 else i_sz
        i_sz_r = abs(i_hsz - i_hcoor) if i_hcoor + i_sz > i_hsz else i_sz

        # modification of array image
        # na_input[row (vert), col (horiz), depth]
        na_input[i_vcoor - i_sz_t:i_vcoor + i_sz_b, i_hcoor, :] = t_color
        na_input[i_vcoor, i_hcoor - i_sz_l:i_hcoor + i_sz_r, :] = t_color

        return na_input
    #
#


def find_segments(na_x, f_thr_amp, i_thr_len):
    """
    Finds indices of 'na_x' where values of 'na_x' are
    equal or above the 'amplitude threshold' value 'f_thr_amp'
    AND equal or longer than the 'duration threshold' value 'i_thr_len'.
    :param na_x: ndarray of one dimension
    :param f_thr_amp: amplitude threshold value (float)
    :param i_thr_len: length threshold - must be specified in number
                      of elements of na_x (2,3,4, ... X.size - 1)
    :return: M row x 2 column ndarray of beginning and ending (+1) indices, -
             so called 'segments' where M is the number of segments.
             * To remember: end idx + 1 because Python range excludes last number
             ________________________
             | beg idx  | end idx  |    <- segment 1
             |          |          |    <- segment 2
             .          .          .    <- ...
    """

    # just in case, makes na_x in 1 "row" format: array([a, b, c, ...])
    na_x = np.squeeze(na_x)

    if len(na_x.shape) != 1:
        raise TypeError("find_segments: na_x must be a ndarray of single row or column")

    if np.isnan(na_x).any():
        raise TypeError("find_segments: na_x contain NaN values")

    if (na_x <= f_thr_amp).all():
        raise ValueError("find_segments: ﻿amplitude threshold (f_thr_amp) is too high")

    if (na_x >= f_thr_amp).all():
        raise ValueError("find_segments: ﻿amplitude threshold (f_thr_amp) is too low")

    i_thr_len = np.int(np.floor(i_thr_len))

    if i_thr_len < 2:
        raise ValueError("find_segments: length threshold (i_thr_len) is too short (less than 2)")

    if i_thr_len > (na_x.size - 1):
        raise ValueError("find_segments: ﻿length threshold (i_thr_len) is too long (longer than length(X) - 1)")

    # special case when thr_amp is exactly equal to min(x)
    if (na_x >= f_thr_amp).all():
        na_segments = np.array([0, len(na_x)], dtype=np.int64)
        warnings.warn("find_segments: all values are equal or above the f_thr_amp value")
        return na_segments

    # Ideally, we need to find indices of all continuous chunks of ones longer or equal to i_thr_len
    # In order to detect 0 -> 1 and 1 -> 0 transitions in x1, we use np.diff()

    na_x_gt_thr_amp_bool = na_x >= f_thr_amp  # boolean ndarray: where na_x is greater than f_thr_amp
    na_x_gt_thr_amp      = np.array(list(map(np.int, na_x_gt_thr_amp_bool)))  # boolean converted to 0s and 1s
    na_diff_x            = np.diff(na_x_gt_thr_amp)  # array of differences
                                                     # 0: no change; 1: increase; -1: decrease
    # example:
    # na_x:                  array([ 1,  3,  4,  6,  9, 10,  5,  3,  1])
    # f_thr_amp:             4
    # na_x_gt_thr_amp_bool:  array([False, False,  True,  True,  True,  True,  True, False, False])
    # na_x_gt_thr_amp:       array([0, 0, 1, 1, 1, 1, 1, 0, 0])
    # na_diff_x:             array([ 0,  1,  0,  0,  0,  0, -1,  0])

    # filter na_x by amplitude
    # slicing is done in the Python way: end is 1 more than the actual end index

    if   na_x[0] <  f_thr_amp and na_x[-1] <  f_thr_amp:  # 00111100 (for na_x_gt_thr_amp)
        na_begs = np.where(na_diff_x > 0)[0] + 1
        na_ends = np.where(na_diff_x < 0)[0] + 1

    elif na_x[0] >= f_thr_amp and na_x[-1] >= f_thr_amp:  # 11000011
        na_begs = np.append(0, np.where(na_diff_x > 0)[0] + 1)
        na_ends = np.append(np.where(na_diff_x < 0)[0] + 1, na_x.size)

    elif na_x[0] >= f_thr_amp and na_x[-1] <  f_thr_amp:  # 11011000
        na_begs = np.append(0, np.where(na_diff_x > 0)[0] + 1)
        na_ends = np.where(na_diff_x < 0)[0] + 1

    elif na_x[0] <  f_thr_amp and na_x[-1] >= f_thr_amp:  # 00011011
        na_begs = np.where(na_diff_x > 0)[0] + 1
        na_ends = np.append(np.where(na_diff_x < 0)[0] + 1, na_x.size)

    else:
        raise ValueError("find_segments: algorithm error (1)")  # should never happen

    if len(na_begs) != len(na_ends):
        raise ValueError("find_segments: algorithm error (2)")

    na_diff_I = np.where(((na_ends - na_begs + 1) >= (i_thr_len + 1)) == True)[0]
    na_segments = np.column_stack((na_begs[na_diff_I], na_ends[na_diff_I]))  # ndarray of shape (M, 2) where M = number of segments

    return na_segments.astype(np.int64)
#


def _find_first_good_keypoint(na_pos_xy, i_pos_history_depth, f_max_jump_pixels):
    """
    Finds a legitimate keypoint (where mouse is) by checking the distance between
    a sequence of keypoints before that (of depth i_pos_history_depth)
    :param na_pos_xy: M-row 2-col array of ALL keypoints (multiple counts included
                      for each frame, so length longer than number of frames)
    :param i_pos_history_depth: the depth of the deque made
    :param f_max_jump_pixels: maximum number of pixels mouse can jump
    :return: index (in na_pos_xy) where first legitimate sequence of kpts is made.
             REMEMBER: index returned is NOT the same as frame number
    """
    fifo_pos  = deque(maxlen=i_pos_history_depth)
    fifo_dist = deque(maxlen=i_pos_history_depth)
    f_pos_history_depth = float(i_pos_history_depth)

    for i_idx in range(na_pos_xy.shape[0]):
        if np.isnan( na_pos_xy[i_idx,0] ) or np.isnan( na_pos_xy[i_idx,1] ):
            continue

        if len(fifo_pos) == 0:
            fifo_pos.append( na_pos_xy[i_idx,:] )
            continue

        # find distance between previous position and current
        # then update vars
        fifo_dist.append( np.linalg.norm(na_pos_xy[i_idx,:] - fifo_pos[-1]) )
        fifo_pos.append( na_pos_xy[i_idx,:] )

        if (sum(fifo_dist) / f_pos_history_depth) <= f_max_jump_pixels:
            return i_idx

    raise ValueError("Unable to find any good frame")
#


def _find_prev_non_nan_idx(l_prev_kpts):
    """
    Finds the last non-nan keypoint coordinates and
    returns the index of that keypoint in prev_kpts.
    :param l_prev_kpts: must be a list of ndarrays of
                        coordinates of previous kpts.
    :return: tuple - coordinates of last non-nan kpt,
             and the index number
    """
    # search for the reference keypoint in the l_prev_kpts,
    # the last keypoint which was not [nan, nan].
    # note that we travel back in time here
    b_ref_pt_found = False
    i_idx = len(l_prev_kpts) - 1
    for item in reversed(l_prev_kpts):
        if not np.isnan(item[0][0]) and not np.isnan(item[0][1]):
            b_ref_pt_found = True
            break
        i_idx -= 1
    #
    if not b_ref_pt_found:
        raise ValueError("Algorithm Error")

    return i_idx
#


def select_best_keypoint(l_prev_kpts, na_candidate_kpts):
    """
    Selects most appropriate keypoints within candidat kpts found
    in one frame, comparing it to the "cleaned" previous keypoints.
    :param l_prev_kpts: a Python list of (1,2) Numpy arrays.
    Contain previously 'detected' and 'selected' keypoints.
    May contain pairs of [np.nan np.nan] values.
    *** Do not change the content of l_prev_kpts here! ***
    :param na_candidate_kpts: Mx2 matrix of (x,y) values, where
           M is a number of keypoints detected for given frame.
    :return: coordinates of best keypoint found within candidates
    """

    # search for the reference keypoint in the l_prev_kpts
    # make sure the na_ref_xy is just a 2 element vector
    na_ref_xy = np.squeeze(l_prev_kpts[_find_prev_non_nan_idx(l_prev_kpts)])

    # make sure na_candidate_kpts has nrow > 1 and ncol == 2
    if na_candidate_kpts.shape[0] <= 1 and na_candidate_kpts.shape[1] != 2:
        raise ValueError("Unexpected argument na_candidate")

    # ndarray of distances between reference keypoint
    # and each of candidate keypoints
    na_dist = np.zeros(na_candidate_kpts.shape[1])

    # calculate the distances
    for i_pt in range(na_candidate_kpts.shape[1]):
        na_dist[i_pt] = np.linalg.norm(na_ref_xy - na_candidate_kpts[i_pt, :])

    i_best_ktp = na_dist.argmin()

    if np.isnan(na_dist[i_best_ktp]):
        return np.array([np.nan, np.nan])

    return na_candidate_kpts[i_best_ktp, :]
#


def remove_extra_keypoints(na_pos_xy, na_call_cnt, i_pos_history_depth, f_max_jump_pixels, b_verbose=False):
    """
    Finds some legitimate frames.
    Restricts number of keypoints to number of frames
    :param s_behav_fname: name of mat file
    :param i_pos_history_depth and f_max_jump_pixels: for find_first_good_keypoint function
    :return: 2-col, N-row array, N = frame number
    """
    i_1st_good_pos_idx = _find_first_good_keypoint(na_pos_xy, i_pos_history_depth, f_max_jump_pixels)
    i_1st_good_frame_num = na_call_cnt[i_1st_good_pos_idx]

    # total number of frames recorded in this session:
    i_nframes_total = na_call_cnt.max() + 1

    if b_verbose:
        print("1st good frame number: %i, pos=%s" % (
            i_1st_good_frame_num, repr(na_pos_xy[i_1st_good_pos_idx, :]))
        )
    #

    # clean up position values in the forward (fwd) direction
    # starting from the first good position
    l_pos_fwd = []
    l_pos_fwd.append(na_pos_xy[i_1st_good_pos_idx, :].reshape(1, 2))

    # start from the first "good" frame:
    for i_frame_num in range(i_1st_good_frame_num, i_nframes_total):
        # indices of all key points found for the given frame number
        na_bool_kpt_idx = (na_call_cnt == i_frame_num)
        if na_bool_kpt_idx.sum() == 1: # if only one keypoint (or no keypoint) was found
            na_best_kpt = na_pos_xy[na_bool_kpt_idx, :]
            l_pos_fwd.append(na_best_kpt.reshape(1, 2))
            continue
        else:  # if more than 1 keypoint was found
            na_best_kpt = select_best_keypoint(l_pos_fwd, na_pos_xy[na_bool_kpt_idx, :])
            # appends best positions to fwd frames
            l_pos_fwd.append(na_best_kpt.reshape(1, 2))

    na_pos_fwd = np.squeeze(np.array(l_pos_fwd))

    # clean up position values in the backward (backw) direction
    # starting from the first good position and moving back in time
    l_pos_backw = []
    l_pos_backw.append(na_pos_xy[i_1st_good_pos_idx, :].reshape(1, 2))

    for i_frame_num in reversed(range(i_1st_good_frame_num)):
        # indices of all key points found for the given frame number
        na_bool_kpt_idx = (na_call_cnt == i_frame_num)
        if na_bool_kpt_idx.sum() == 1: # if only one keypoint (or no keypoint) was found
            na_best_kpt = na_pos_xy[na_bool_kpt_idx, :]
            l_pos_backw.append(na_best_kpt.reshape(1, 2))
            continue
        else:  # if more than 1 keypoint was found
            na_best_kpt = select_best_keypoint(l_pos_backw, na_pos_xy[na_bool_kpt_idx, :])
            # appends best position to backw frames
            l_pos_backw.append(na_best_kpt.reshape(1, 2))

    na_pos_backw = np.squeeze(np.array(list(reversed(l_pos_backw))))

    # remove last point of the backward positions,
    # first point of the forward positions
    # (because these are duplicates of the "first good point")
    # and combine two arrays into single one.
    na_pos_xy_clean = np.vstack([na_pos_backw[0:-1, :], na_pos_fwd[1:, :]])

    if na_pos_xy_clean.shape[0] != i_nframes_total:
        raise ValueError("Sanity check failed: unexpected output shape")

    return na_pos_xy_clean
#


class CSingleSubjectTracker(object):
    def __init__(self, i_frame_h, i_frame_w, frame_dtype, d_param):
        self.t_aim_color = d_param['aim_color']
        self.i_aim_thickness = d_param['aim_thickness']
        self.f_frame_rate = d_param['frame_rate']
        self.f_frame_dt_sec = 1.0/self.f_frame_rate
        self.i_nframes = d_param['frames']
        self.t_init_ROI = d_param['initial_ROI']
        self.s_tracker_type = d_param['tracker_type']

        # frames are counted starting from zero
        # each time when the process_frame() method called.
        self._i_frame_cnt = -1

        # temporal storage for output data.
        self.l_TS_SEC = [] # ts_sec - scalar, float
        self.l_CNT_XY_RAW = [] # (center_x, center_y) tuple, float(!)
        self.l_ROI = []    # (i_roi_x, i_roi_y, i_roi_w, i_roi_h) tuple, float
        self.l_msel_frame_ids = [] # manual selection frame ids, vector of integers

        # create tracker instance based on requested type
        self.__create_tracker()

        # main data exchange interface for this class
        # NOTE that for this class na_out is a (H x W x 3) shaped array!
        self.na_out = np.zeros([i_frame_h, i_frame_w, 3], dtype=frame_dtype)

        # final storage for the Single TRACK data
        self.d_STRACK = {}
        self.d_STRACK['initial_frame_number'] = d_param['initial_frame_number']

    def __create_tracker(self):
        if self.s_tracker_type == 'BOOSTING':
            self.oc_tracker = cv.TrackerBoosting_create()
        elif self.s_tracker_type == 'MIL':
            self.oc_tracker = cv.TrackerMIL_create()
        elif self.s_tracker_type == 'KCF':
            self.oc_tracker = cv.TrackerKCF_create()
        elif self.s_tracker_type == 'TLD':
            self.oc_tracker = cv.TrackerTLD_create()
        elif self.s_tracker_type == 'MEDIANFLOW':
            self.oc_tracker = cv.TrackerMedianFlow_create()
        elif self.s_tracker_type == "CSRT":
            self.oc_tracker = cv.TrackerCSRT_create()
        else:
            raise TypeError("Unsupported tracker type: %s" % d_param['tracker_type'])

    def __process_ROI(self, t_ROI):
        if tuple is not type(t_ROI) or len(t_ROI) != 4:
            raise RuntimeError("something went seriously wrong")

        fx, fy, fw, fh = t_ROI
        fcx = fx + fw/2
        fcy = fy + fh/2
        i_aim_hsz = int((fw + fh)/4)
        i_aim_rad = int(i_aim_hsz/2)
        icx = int(fcx)
        icy = int(fcy)

        self.l_TS_SEC.append(self._i_frame_cnt * self.f_frame_dt_sec)
        self.l_CNT_XY_RAW.append((fcx, fcy))
        self.l_ROI.append(t_ROI)

        cv.circle(self.na_out, (icx, icy), i_aim_rad, self.t_aim_color, self.i_aim_thickness)
        cv.line(self.na_out, (icx-i_aim_hsz, icy), (icx+i_aim_hsz, icy), self.t_aim_color, self.i_aim_thickness)
        cv.line(self.na_out, (icx, icy-i_aim_hsz), (icx, icy+i_aim_hsz), self.t_aim_color, self.i_aim_thickness)

    def process_frame(self, na_input, b_verbose=False):
        if len(na_input.shape) != 3 or na_input.shape[2] != 3:
            raise ValueError("Unexpected frame shape")

        # the frame is accepted for processing...
        self._i_frame_cnt += 1
        self.na_out[...] = na_input[...]

        if self._i_frame_cnt == 0:
            self.b_tracking_status = self.oc_tracker.init(na_input, self.t_init_ROI)
            if not self.b_tracking_status:
                raise RuntimeError("Unable to initialize the tracker")
            self.l_msel_frame_ids.append(0)

        # Update tracker state. Note that this is also to be called for the frame #0
        self.b_tracking_status, t_curr_ROI = self.oc_tracker.update(na_input)

        # In the case of a tracking failure we return here in order to
        # give caller a choice - select another ROI and call restart_tracking()
        # with the SAME frame or call skip_frame() if selection of a new ROI 
        # is not possible for the frame at which this tracking failure occured.
        # NOTE that skip_frame() does not advance the frame itself, only tracking data,
        # so it is the caller's responsibility to call process_frame() after skip_frame()
        if not self.b_tracking_status: return
        # save ROI data in local storage if tracking went well
        self.__process_ROI(t_curr_ROI)

    def skip_frame(self):
        # We don't need to change self._i_frame_cnt here!
        self.l_TS_SEC.append(self._i_frame_cnt * self.f_frame_dt_sec)
        self.l_CNT_XY_RAW.append((np.nan, np.nan))
        self.l_ROI.append((np.nan, np.nan, np.nan, np.nan))

    def is_tracking_succeed(self):
        return self.b_tracking_status

    def restart_tracking(self, na_input, t_new_ROI):
        # We need to clear(!) and re-create the tracker object
        self.oc_tracker.clear()
        self.__create_tracker()
        # Re-Initialize tracker with current frame and new ROI
        self.b_tracking_status = self.oc_tracker.init(na_input, t_new_ROI)
        if not self.b_tracking_status:
            raise RuntimeError("Unable to re-initialize the tracker")
        self.l_msel_frame_ids.append(self._i_frame_cnt)
        self.__process_ROI(t_new_ROI)

    def finalize_tracking(self):
        self.d_STRACK['TS_SEC'] = np.array(self.l_TS_SEC)
        self.d_STRACK['CNT_XY_RAW'] = np.array(self.l_CNT_XY_RAW)
        self.d_STRACK['ROI'] = np.array(self.l_ROI)
        self.d_STRACK['MSEL_FRAME_IDS'] = np.array(self.l_msel_frame_ids)
        self.d_STRACK['frame_rate_Hz'] = self.f_frame_rate
        self.d_STRACK['number_of_input_frames'] = self.i_nframes
    #
#

