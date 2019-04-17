#!/usr/bin/env python3


import os
import sys
import time
import datetime

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


class CMuPaVideoWriter(object):
    def __init__(self, s_root_dir, s_file_prefix, f_fps, i_frame_w, i_frame_h, i_nframes_per_file=1000):
        if not os.path.isdir(s_root_dir):
            raise IOError("Root directory does not exist or not accessible!")

        self.s_root_dir = s_root_dir # e.g. '.' or './data'
        self.s_file_prefix = s_file_prefix # e.g. 'msCam' or 'behavCam'
        self.f_fps = float(f_fps)
        self.i_frame_w = int(i_frame_w)
        self.i_frame_h = int(i_frame_h)
        self.i_nframes_per_file = i_nframes_per_file
        # Use EXTERNAL (MUST be provided by FFMPEG) lossless codec
        self.oc_fourcc = cv.VideoWriter_fourcc(*'FFV1')
        self.b_new_file_at_next_write = False

        # e.g. ./data/2019-04-16_16-12-34
        self.s_out_root_dir = os.path.join(self.s_root_dir, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))

        os.mkdir(self.s_out_root_dir)
        if not os.path.isdir(self.s_out_root_dir):
            raise IOError("Unable to make output root directory!")

        # these variables are changed every new recording session
        self.s_out_rses_dir = None
        self.i_out_file_id = 1  # start from 1 for backward compatibility
        self.i_out_frame_id = 0 # compared to the self.i_nframes_per_file
        self.s_out_fname = None
        self.oc_video_writer = None
        self.__prepare_new_session()

    def __prepare_new_session(self):
        self.close()

        # e.g. ./data/2019-04-16_16-12-34/H16_M12_S34
        self.s_out_rses_dir = os.path.join(self.s_out_root_dir, datetime.datetime.now().strftime('H%H_M%M_S%S'))

        os.mkdir(self.s_out_rses_dir)
        if not os.path.isdir(self.s_out_rses_dir):
            raise IOError("Unable to make recording session directory!")

        self.i_out_file_id = 1
        self.i_out_frame_id = 0

        # e.g. ./data/2019-04-16_16-12-34/H16_M12_S34/msCam1.avi
        self.s_out_fname = os.path.join(self.s_out_rses_dir, "%s%i.avi" % (self.s_file_prefix, self.i_out_file_id))

        # request to make new output file at next call of the self.write_next_frame() method
        self.b_new_file_at_next_write = True

    def __del__(self):
        if self.oc_video_writer != None:
            self.oc_video_writer.release()

    def write_next_frame(self, na_in):
        if na_in.ndim != 3 or na_in.shape[2] != 3:
            raise ValueError("Unexpected frame shape: %s" % repr(na_in.shape))

        if not self.b_new_file_at_next_write and self.oc_video_writer == None:
            raise ValueError("Unexpected state. Please contact developer(s)")

        if self.b_new_file_at_next_write:
            self.oc_video_writer = cv.VideoWriter(self.s_out_fname, self.oc_fourcc, self.f_fps, (self.i_frame_w, self.i_frame_h))
            self.b_new_file_at_next_write = False

        self.oc_video_writer.write(na_in)
        self.i_out_frame_id += 1

        if self.i_out_frame_id >= self.i_nframes_per_file:
            self.oc_video_writer.release()
            self.i_out_file_id += 1
            self.i_out_frame_id = 0
            self.s_out_fname = os.path.join(self.s_out_rses_dir, "%s%i.avi" % (self.s_file_prefix, self.i_out_file_id))
            self.b_new_file_at_next_write = True

    def close(self):
        if self.oc_video_writer != None:
            self.oc_video_writer.release()
            del self.oc_video_writer
            self.oc_video_writer = None

    def write_last_frame(self, na_in):
        self.write_next_frame(na_in)
        self.close()

    def start_new_session(self):
        self.__prepare_new_session()
        return self.s_out_rses_dir
    #
#

