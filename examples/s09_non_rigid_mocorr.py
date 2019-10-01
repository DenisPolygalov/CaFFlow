#!/usr/bin/env python3


import os
import sys
import configparser


"""
Copyright (C) 2018, 2019 Denis Polygalov,
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


def show_diff(s_in_fname, i_frame_1, i_frame_2):
    oc_movie = CMuPaMovieTiff((s_in_fname,))

    print("\nMovie information:")
    print(oc_movie.df_info)
    print()

    i_frame_id = 0
    b_frame_1_found = False
    b_frame_2_found = False

    while(oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())

        if i_frame_id == i_frame_1:
            na_frame_1 = oc_movie.na_frame.copy().astype(np.float32)
            b_frame_1_found = True
        if i_frame_id == i_frame_2:
            na_frame_2 = oc_movie.na_frame.copy().astype(np.float32)
            b_frame_2_found = True

        if b_frame_1_found and b_frame_2_found: break
        i_frame_id += 1

    # show difference between the requested pair of frames
    plt.imshow(na_frame_1 - na_frame_2)
    plt.show()
#


def show_whole_input(s_in_fname):
    # create a multi-part movie object
    oc_movie = CMuPaMovieTiff((s_in_fname,))

    print("\nMovie information:")
    print(oc_movie.df_info)
    print()

    l_frames = []

    # read first N frames
    while(oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())
        l_frames.append(oc_movie.na_frame)

    # show the frames
    print("\nUsage: (p)revious frame, (n)ext frame, (q)uit.")
    moshow("frames", l_frames)
#


def pre_filter_all_frames(s_in_fname):
    l_frames = []
    i_frame_id = 0
    i_niter = 3
    i_median_blur_sz = 5
    oc_filter = CFastGuidedFilter(3)
    oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (7,7))
    oc_movie = CMuPaMovieTiff((s_in_fname,))

    while(oc_movie.read_next_frame()):
        na_frame = cv.medianBlur(oc_movie.na_frame, i_median_blur_sz)
        oc_filter.process_frame(cv.normalize(na_frame, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))
        na_background = cv.morphologyEx(oc_filter.na_out, cv.MORPH_OPEN, oc_strel_kernel, iterations=i_niter)
        na_signal = cv.normalize(oc_filter.na_out - na_background, None, alpha=0, beta=255, norm_type=cv.NORM_MINMAX, dtype=cv.CV_8U)
        # l_frames.append(na_signal)
        l_frames.append(np.hstack([
            cv.normalize(na_frame,  None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F),
            cv.normalize(na_signal, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F),
        ]))
        if i_frame_id % 10 == 0: print(i_frame_id)
        i_frame_id += 1
    moshow("frames", l_frames)
#


def pre_filter_single_frame(na_frame_in):
    i_niter = 3
    i_median_blur_sz = 5
    oc_filter = CFastGuidedFilter(3)
    oc_strel_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (7,7))

    # medianBlur returns uint8
    na_frame = cv.medianBlur(na_frame_in, i_median_blur_sz)

    # oc_filter.na_out returns float32
    oc_filter.process_frame(cv.normalize(na_frame, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F))

    # morphologyEx returns float32
    na_background = cv.morphologyEx(oc_filter.na_out, cv.MORPH_OPEN, oc_strel_kernel, iterations=i_niter)

    # don't need to normalize/convert to 8 bit here because
    # CPieceWiseECC -> CStiBordFrame require float32 as input
    return oc_filter.na_out - na_background
#


def pre_filter_all_with_mocorr(s_in_fname, oc_rec_cfg):
    oc_movie = CMuPaMovieTiff((s_in_fname,))
    l_frames = []
    i_frame_id = 0
    oc_pw_ecc = None
    oc_motion_field = None
    i_median_flt_sz = int(oc_rec_cfg["median_blur"])

    while(oc_movie.read_next_frame()):
        # print("Frame number:", i_frame_id)

        # pre-filter each frame locally (used for debugging)
        # na_frame = pre_filter_single_frame(oc_movie.na_frame)

        na_frame = cv.medianBlur(oc_movie.na_frame, i_median_flt_sz)
        na_frame_to_register = cv.normalize(na_frame, None, alpha=0, beta=1, norm_type=cv.NORM_MINMAX, dtype=cv.CV_32F)

        if oc_pw_ecc == None:
            oc_pw_ecc = CPieceWiseECC(
                na_frame.shape[0], # frame height!
                na_frame.shape[1], # frame width!
                na_frame.dtype,
                oc_rec_cfg
            )
            oc_motion_field = CMotionFieldDrawer(
                na_frame.shape[0], # frame height!
                na_frame.shape[1], # frame width!
                int(oc_rec_cfg["pw_ecc_nrow_tiles"]),
                int(oc_rec_cfg["pw_ecc_ncol_tiles"]),
                f_zoom_coef=10.0
            )
        oc_pw_ecc.process_frame(na_frame, b_verbose=True)
        # normal way to register the frames
        oc_pw_ecc.register_frame()
        # you can register frames with background left untouched, for debugging
        # oc_pw_ecc.register_frame(na_input=na_frame_to_register)
        
        if i_frame_id < 3:
            plt.subplot(221)
            plt.imshow(oc_pw_ecc.d_REG['PW_REG_corr_coef'][-1])
            plt.subplot(222)
            plt.imshow(oc_pw_ecc.d_REG['PW_REG_warp_matrix'][-1])
            plt.subplot(223)
            plt.imshow(oc_pw_ecc.d_REG['PW_REG_inter_patch_dist'][-1])
            plt.subplot(224)
            oc_motion_field.process_frame(oc_pw_ecc.oc_twM)
            plt.imshow(oc_motion_field.na_out)
            plt.show()

        # l_frames.append(oc_pw_ecc.na_out.copy())
        # l_frames.append(oc_pw_ecc.na_out_reg.copy())
        l_frames.append(np.hstack([na_frame_to_register, oc_pw_ecc.na_out_reg]))
        i_frame_id += 1
        # if i_frame_id >= 10: break
    print(oc_pw_ecc.d_REG['PW_REG_not_converged'])
    print(oc_pw_ecc.d_REG['PW_REG_high_jumps'])
    moshow("frames", l_frames)
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from mendouscopy.player import moshow
    from mendouscopy.mupamovie import CMuPaMovieTiff
    from mendouscopy.filtering import CFastGuidedFilter
    from mendouscopy.registration import CMotionFieldDrawer
    from mendouscopy.registration import CPieceWiseECC
    import numpy as np
    import cv2 as cv
    import matplotlib.pyplot as plt

    # load local configuration file
    oc_rec_cfg = configparser.ConfigParser()
    oc_rec_cfg.read("x16_frame0to99.ini")

    # show_diff("x16_frame0to99.tiff", 1, 2)
    # show_whole_input("x16_frame0to99.tiff")
    # pre_filter_all_frames("x16_frame0to99.tiff")
    pre_filter_all_with_mocorr("x16_frame0to99.tiff", oc_rec_cfg["frame_registration"])
#


