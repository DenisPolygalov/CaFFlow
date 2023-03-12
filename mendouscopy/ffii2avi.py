#!/usr/bin/env python3


import os
import sys
import struct

import numpy as np
import cv2 as cv


"""
Copyright (C) 2019 Denis Polygalov,
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


def convert(f_fps, s_fname_in, s_fname_out):
    print("Input file:\t", s_fname_in)
    print("Output file:\t", s_fname_out)
    print("Output FPS:\t", f_fps)

    h_file_in = open(s_fname_in, 'rb')
    bytes_chunk = h_file_in.read(8)
    i_frame_h, i_frame_w = struct.unpack(">2I", bytes_chunk)

    oc_fourcc = cv.VideoWriter_fourcc(*'FFV1')
    oc_video_writer = cv.VideoWriter(s_fname_out, oc_fourcc, f_fps, (i_frame_w, i_frame_h), isColor=False)

    i_frame_id = 0
    while True:
        bytes_frame = h_file_in.read(i_frame_h * i_frame_w)
        na_frame = np.frombuffer(bytes_frame, dtype=np.uint8).reshape(i_frame_h, i_frame_w)
        oc_video_writer.write(na_frame)

        i_frame_id += 1

        if i_frame_id % 100 == 0:
            print("Read %i frames" % i_frame_id)

        bytes_chunk = h_file_in.read(8)
        if not bytes_chunk:
            break
        i_frame_h, i_frame_w = struct.unpack(">2I", bytes_chunk)

    h_file_in.close()
    oc_video_writer.release()
    print("Written %i frames in total" % i_frame_id)
#


def usage():
    print("ERROR: not enough input arguments!")
    print("Usage: ffii2avi.py FPS input_file.ffii [output_file.avi]")
    print("If no third argument was given the output file name")
    print("will be assigned automatically as: input_file.avi")
    print("NO CHECKS IS DONE ON THE INPUT FILE FORMAT")
    print("WILL ABORT IF THE OUTPUT FILE ALREADY EXIST")
#


if __name__ == "__main__":
    if not cv.__version__.startswith('3'):
        print("ERROR: this script can only work with OpenCV 3.x. You have: %s" % cv.__version__)
        sys.exit(-1)
    if len(sys.argv) == 3:
        s_fps = sys.argv[1]
        s_fname_in = sys.argv[2]
        s_base, _ = os.path.splitext(s_fname_in)
        s_fname_out = s_base + ".avi"

    elif len(sys.argv) == 4:
        s_fps = sys.argv[1]
        s_fname_in = sys.argv[2]
        s_fname_out = sys.argv[3]

    else:
        usage()
        sys.exit(-1)

    if not os.path.isfile(s_fname_in):
        raise IOError("Input file does not exist or not accessible")
    if os.path.isfile(s_fname_out):
        raise IOError("Output file already exist. Abort operation in order to prevent data loss.")

    convert(float(s_fps), s_fname_in, s_fname_out)
#

