#!/usr/bin/env python3


import os
import sys
import configparser


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
    oc_iproj = None

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
            oc_iproj = CIntensityProjector(
                oc_movie.na_frame.shape[0], # frame height
                oc_movie.na_frame.shape[1]  # frame width
            )

        oc_pc1_wiper.process_frame(oc_movie.na_frame)
        oc_register.process_frame(oc_pc1_wiper.na_out)
        oc_register.register_frame()
        oc_iproj.process_frame(oc_register.na_out_reg)

        i_frame_id += 1
        # if i_frame_id >= 30: break

    oc_iproj.finalize_projection()

    fig, axs = plt.subplots(1, 2, constrained_layout=True)
    axs[0].imshow(oc_iproj.d_IPROJ['IPROJ_max'])
    axs[0].set_title('Maximum Intensity Projection')
    axs[1].imshow(oc_iproj.d_IPROJ['IPROJ_std'])
    axs[1].set_title('Standard Deviation Intensity Projection')
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.player import moshow
    from mendouscopy.mupamovie import CMuPaMovieTiff
    from mendouscopy.filtering import CPrinCompWiper
    from mendouscopy.registration import CFrameRegECC
    from mendouscopy.iproj import CIntensityProjector
    import numpy as np
    import cv2
    import matplotlib.pyplot as plt
    main()
#
