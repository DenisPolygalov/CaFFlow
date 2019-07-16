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


"""
* ABOUT THIS FILE *

Shows the sample images (video frames) in file
CW2003_H14_M57_S54_msCam1_frame0to99.tiff
where the frames can be changed interactively
(can go to *next* and *previous* frames).
"""


def main():
    # make a tuple of strings - input file names
    t_input_files = ("CW2003_H14_M57_S54_msCam1_frame0to99.tiff",) # notice comma(!)
    for s_fname in t_input_files:
        print("Input file: %s" % s_fname)

    # create a multi-part movie object
    oc_movie = CMuPaMovieTiff(t_input_files)

    print("\nMovie information:")
    print(oc_movie.df_info)
    print()

    l_frames = []
    i_frame_id = 0

    # read first N frames
    while(oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())
        l_frames.append(oc_movie.na_frame)
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
    main()
#
