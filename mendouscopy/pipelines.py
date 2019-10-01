#!/usr/bin/env python3


import os
import sys
import cv2 as cv
import numpy as np

from .mupamovie import CMuPaMovieCV
from .mupamovie import CMuPaMovieZF
from .mupamovie import CMuPaMovieTiff
from .mupamovie import CSingleTiffWriter
from .filtering import CPrinCompWiper
from .registration import CFrameRegECC
from .registration import CFrameRegNone
from .registration import CPieceWiseECC
from .rois import CFrameWiseROIDetector
from .rois import CMovieWiseROIPicker
from .rois import CMovieWiseWeightedROIPicker


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


def _check_file(s_fname, b_check_absence=False):
    if b_check_absence:
        if os.path.isfile(s_fname):
            print("ERROR: Output file exist. Exit here in order to prevent data loss.")
            print("The file: %s" % s_fname)
            sys.exit(2500)
    else:
        if not os.path.isfile(s_fname):
            print("ERROR: File not found: %s" % s_fname)
            sys.exit(2501)
        #
    #
#


def pickup_rois_extract_fluo(s_target_dir, d_param, s_out_fname_prefix, b_overwrite_output=False, i_max_nframes=None):
    s_roi_data_in_fname   = os.path.join(s_target_dir, s_out_fname_prefix + "roi_data.npy")
    s_roi_mask_in_fname   = os.path.join(s_target_dir, s_out_fname_prefix + "roi_mask.tiff")
    s_register_in_fname   = os.path.join(s_target_dir, s_out_fname_prefix + "register.tiff")
    s_fluo_data_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "fluo.npy")

    _check_file(s_roi_data_in_fname)
    _check_file(s_roi_mask_in_fname)
    _check_file(s_register_in_fname)
    if not b_overwrite_output: _check_file(s_fluo_data_out_fname, b_check_absence=True)

    # load ROI data detected frame-wise
    d_roi_data = np.load(s_roi_data_in_fname, allow_pickle=True).item()

    # create a multi-part movie object
    oc_mask_movie = CMuPaMovieTiff((s_roi_mask_in_fname,)) # notice the comma(!)

    i_frame_id = 0
    oc_roi_picker = None
    if 'wROI_jaccard_threshold' in d_param['moviewise_roi_pickup']:
        s_picker_type = "weighted"
    else:
        s_picker_type = "non-overlapped"

    while(oc_mask_movie.read_next_frame()):
        if i_frame_id % 100 == 0: print("process frame (%s ROI pickup): %i" % (s_picker_type, i_frame_id))

        if i_frame_id == 0:
            if 'wROI_jaccard_threshold' in d_param['moviewise_roi_pickup']:
                oc_roi_picker = CMovieWiseWeightedROIPicker(
                    oc_mask_movie.na_frame.shape[0], # frame height
                    oc_mask_movie.na_frame.shape[1], # frame width
                    oc_mask_movie.na_frame.dtype,
                    d_param['moviewise_roi_pickup']
                )
            else:
                oc_roi_picker = CMovieWiseROIPicker(
                    oc_mask_movie.na_frame.shape[0], # frame height
                    oc_mask_movie.na_frame.shape[1], # frame width
                    oc_mask_movie.na_frame.dtype,
                    d_param['moviewise_roi_pickup']
                )
            #

        oc_roi_picker.pickup(i_frame_id, d_roi_data, oc_mask_movie.na_frame)
        i_frame_id += 1
        if i_max_nframes != None and i_frame_id >= i_max_nframes: break
    oc_roi_picker.finalize_pickup()

    print("Number of frames processed: %i" % i_frame_id)
    print("Number of ROIs collected: %i" % len(oc_roi_picker.l_ROI))

    # create a multi-part movie object
    oc_reg_movie = CMuPaMovieTiff((s_register_in_fname,)) # notice the comma(!)

    i_frame_id = 0 # <--- RESET THE FRAME COUNTER ---

    while(oc_reg_movie.read_next_frame()):
        if i_frame_id % 100 == 0: print("process frame (extract fluorescence traces): %i" % i_frame_id)
        oc_roi_picker.extract_fluo_from_frame(oc_reg_movie.na_frame)
        i_frame_id += 1
        if i_max_nframes != None and i_frame_id >= i_max_nframes: break
    oc_roi_picker.finalize_fluo()

    # save the results
    np.save(s_fluo_data_out_fname, oc_roi_picker.d_FLUO)
#


def register_frames_detect_rois(s_target_dir, oc_frame_source, d_param, s_out_fname_prefix, b_overwrite_output=False, i_max_nframes=None):
    s_register_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "register.tiff")
    s_roi_fluo_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "roi_fluo.tiff")
    s_roi_mask_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "roi_mask.tiff")
    s_roi_data_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "roi_data.npy")
    s_reg_data_out_fname = os.path.join(s_target_dir, s_out_fname_prefix + "reg_data.npy")

    if not b_overwrite_output:
        _check_file(s_register_out_fname, b_check_absence=True)
        _check_file(s_roi_fluo_out_fname, b_check_absence=True)
        _check_file(s_roi_mask_out_fname, b_check_absence=True)
        _check_file(s_roi_data_out_fname, b_check_absence=True)
        _check_file(s_reg_data_out_fname, b_check_absence=True)

    if isinstance(oc_frame_source, tuple):
        t_in_files = oc_frame_source
        if t_in_files[0].endswith(".tiff") or t_in_files[0].endswith(".tif"):
            oc_movie = CMuPaMovieTiff(t_in_files)
        elif t_in_files[0].endswith(".zip"):
            oc_movie = CMuPaMovieZF(t_in_files)
        else:
            oc_movie = CMuPaMovieCV(t_in_files)
    else:
        oc_movie = oc_frame_source

    d_reg_param = d_param["frame_registration"]
    d_roi_det_param = d_param["framewise_roi_detection"]

    if 'pcs2rm' in d_reg_param.keys():
        l_pcs2rm = list(map(int, d_reg_param['pcs2rm'].split(',')))
        s_pcs2rm = "pcs2rm: %s" % repr(l_pcs2rm)
    else:
        l_pcs2rm = []
        s_pcs2rm = ""

    if 'median_blur' in d_reg_param.keys():
        i_median_blur_size = int(d_reg_param['median_blur'])
        if i_median_blur_size <= 0: raise ValueError("Wrong filter size")
        s_med_blur = "median_blur: %i" % i_median_blur_size
    else:
        i_median_blur_size = 0
        s_med_blur = ""

    # tiff file writer objects for output data
    oc_register_writer = CSingleTiffWriter(s_register_out_fname, b_delete_existing=b_overwrite_output)
    oc_roi_fluo_writer = CSingleTiffWriter(s_roi_fluo_out_fname, b_delete_existing=b_overwrite_output)
    oc_roi_mask_writer = CSingleTiffWriter(s_roi_mask_out_fname, b_delete_existing=b_overwrite_output)

    oc_pcs_wiper = None
    oc_register = None
    oc_roi_detector = None
    i_frame_id = 0

    while(oc_movie.read_next_frame()):
        if i_frame_id == 0:
            i_frame_h = oc_movie.na_frame.shape[0]
            i_frame_w = oc_movie.na_frame.shape[1]
            frame_dtype = oc_movie.na_frame.dtype

            if len(l_pcs2rm) > 0: oc_pcs_wiper = CPrinCompWiper(i_frame_h, i_frame_w)
            s_mocorr_method = d_reg_param['mocorr_method']
            if s_mocorr_method == 'pw_ecc':
                oc_register = CPieceWiseECC(i_frame_h, i_frame_w, frame_dtype, d_reg_param)
            elif s_mocorr_method == 'ecc':
                oc_register = CFrameRegECC(i_frame_h, i_frame_w, frame_dtype, d_reg_param)
            elif s_mocorr_method == 'none':
                oc_register = CFrameRegNone(i_frame_h, i_frame_w, frame_dtype, d_reg_param)
            else:
                raise NotImplementedError('requested motion correction method is not yet implemented')
            oc_roi_detector = CFrameWiseROIDetector(i_frame_h, i_frame_w, frame_dtype, d_roi_det_param)

        # WARNING: we will be reusing the na_frame variable from here(!)
        if   len(oc_movie.na_frame.shape) == 2:
            na_frame = oc_movie.na_frame
        elif len(oc_movie.na_frame.shape) == 3:
            na_frame = oc_movie.na_frame[...,0]
        else:
            raise ValueError("Unsupported frame shape")

        if len(l_pcs2rm) > 0:
            oc_pcs_wiper.process_frame(na_frame)
            na_frame = oc_pcs_wiper.na_out

        if i_median_blur_size > 0:
            oc_register.process_frame( cv.medianBlur(na_frame, i_median_blur_size) )
        else:
            oc_register.process_frame(na_frame)

        oc_register.register_frame()
        oc_roi_detector.process_frame(oc_register.na_out)
        print("frame: %i shape: %s %s %s ROIs: %i" % (
            i_frame_id,
            repr(oc_movie.na_frame.shape),
            s_pcs2rm,
            s_med_blur,
            len(oc_roi_detector.l_ROI_id)
        ))

        oc_register_writer.write_next_frame(oc_register.na_out_reg)
        oc_roi_fluo_writer.write_next_frame(oc_roi_detector.na_out)
        oc_roi_mask_writer.write_next_frame(oc_roi_detector.na_mask_16U)

        i_frame_id += 1
        if i_max_nframes != None and i_frame_id >= i_max_nframes: break

    oc_register_writer.close()
    oc_roi_fluo_writer.close()
    oc_roi_mask_writer.close()
    np.save(s_reg_data_out_fname, oc_register.d_REG)
    np.save(s_roi_data_out_fname, oc_roi_detector.d_ROI)
#

