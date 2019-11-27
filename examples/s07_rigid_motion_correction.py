#!/usr/bin/env python3


import os
import sys
import configparser


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


def main():
    # load local configuration file
    oc_rec_cfg = configparser.ConfigParser()
    oc_rec_cfg.read("CW2003_H14_M57_S54_msCam1_frame0to99.ini")

    # make a tuple of strings - input file names
    t_input_files = ("CW2003_H14_M57_S54_msCam1_frame0to99.tiff",) # notice comma(!)

    for s_fname in t_input_files:
        print("Input file: %s" % s_fname)

    # create a multi-part movie object
    oc_movie = CMuPaMovieTiff(t_input_files)

    print("\nMovie information:")
    print(oc_movie.df_info)
    print()

    oc_pc1_wiper = None
    oc_register = None

    l_frames = []
    i_frame_id = 0

    # read the movie frame by frame, register frames, stack with raw frame and add into the l_frames
    while(oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())

        if i_frame_id == 0:
            oc_pc1_wiper = CPrinCompWiper(
                oc_movie.na_frame.shape[0], # frame height!
                oc_movie.na_frame.shape[1]  # frame width!
            )
            oc_register = CFrameRegECC(
                oc_movie.na_frame.shape[0], # frame height!
                oc_movie.na_frame.shape[1], # frame width!
                oc_movie.na_frame.dtype,
                oc_rec_cfg["frame_registration"]
            )

        oc_pc1_wiper.process_frame(oc_movie.na_frame)
        oc_register.process_frame(oc_pc1_wiper.na_out)
        oc_register.register_frame()

        na_frame_before = cv2.normalize(oc_movie.na_frame, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        na_frame_after = cv2.normalize(oc_register.na_out_reg, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        l_frames.append(np.vstack([na_frame_before, na_frame_after]))
        i_frame_id += 1
        # if i_frame_id >= 30: break

    # show the frames
    print("\nUsage: (p)revious frame, (n)ext frame, (q)uit.")
    moshow("frames", l_frames)
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.player import moshow
    from mendouscopy.mupamovie import CMuPaMovieTiff
    from mendouscopy.filtering import CPrinCompWiper
    from mendouscopy.registration import CFrameRegECC
    import numpy as np
    import cv2
    main()
#
