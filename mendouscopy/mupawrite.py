#!/usr/bin/env python3


import os
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
    def __init__(self, s_root_dir, s_file_prefix, f_fps, i_frame_w, i_frame_h, i_nframes_per_file=1000, master=None):
        if not os.path.isdir(s_root_dir):
            raise IOError("Root directory does not exist or not accessible!")

        self.s_root_dir = s_root_dir # e.g. '.' or './data'
        self.s_file_prefix = s_file_prefix # e.g. 'msCam' or 'behavCam'
        self.f_fps = float(f_fps)
        self.i_frame_w = int(i_frame_w)
        self.i_frame_h = int(i_frame_h)
        self.i_nframes_per_file = i_nframes_per_file
        self.oc_master_writer = master
        # Use EXTERNAL (MUST be provided by FFMPEG) lossless codec
        self.oc_fourcc = cv.VideoWriter_fourcc(*'FFV1')
        self.b_new_file_at_next_write = False

        # e.g. ./data/2019-04-16_16-12-34
        if self.oc_master_writer == None:
            self.s_out_root_dir = os.path.join(self.s_root_dir, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
            os.mkdir(self.s_out_root_dir)
        else:
            self.s_out_root_dir = self.oc_master_writer.s_out_root_dir

        if not os.path.isdir(self.s_out_root_dir):
            raise IOError("Unable to make/access output root directory!")

        # these variables are changed every new recording session
        self.s_out_rses_dir = None
        self.i_out_file_id = 1  # start from 1 for backward compatibility
        self.i_out_frame_id = 0 # compared to the self.i_nframes_per_file
        self.i_out_frame_id_cumsum = 0
        self.s_out_fname = None
        self.s_out_ts_fname = None
        self.h_ts_file = None
        self.oc_video_writer = None
        self.__prepare_new_session()

    def __prepare_new_session(self):
        self.close()

        # e.g. ./data/2019-04-16_16-12-34/H16_M12_S34
        if self.oc_master_writer is None:
            self.s_out_rses_dir = os.path.join(self.s_out_root_dir, datetime.datetime.now().strftime('H%H_M%M_S%S'))
            os.mkdir(self.s_out_rses_dir)
        else:
            self.s_out_rses_dir = self.oc_master_writer.s_out_rses_dir

        if not os.path.isdir(self.s_out_rses_dir):
            raise IOError("Unable to make/access recording session directory!")

        if self.oc_master_writer is None:
            self.s_out_ts_fname = os.path.join(self.s_out_rses_dir, 'timestamp.dat')
            self.h_ts_file = open(self.s_out_ts_fname, 'w')
            self.h_ts_file.write('camNum\tframeNum\tsysClock\tbuffer\n')

        self.i_out_file_id = 1
        self.i_out_frame_id = 0
        self.i_out_frame_id_cumsum = 0

        # e.g. ./data/2019-04-16_16-12-34/H16_M12_S34/msCam1.avi
        self.s_out_fname = os.path.join(self.s_out_rses_dir, "%s%i.avi" % (self.s_file_prefix, self.i_out_file_id))

        # request to make new output file at next call of the self.write_next_frame() method
        self.b_new_file_at_next_write = True

    def __del__(self):
        if self.oc_video_writer is not None:
            self.oc_video_writer.release()

    def write_next_frame(self, na_in):
        if na_in.ndim != 3 or na_in.shape[2] != 3:
            raise ValueError("Unexpected frame shape: %s" % repr(na_in.shape))

        if not self.b_new_file_at_next_write and self.oc_video_writer is None:
            raise ValueError("Unexpected state. Please contact developer(s)")

        if self.b_new_file_at_next_write:
            self.oc_video_writer = cv.VideoWriter(self.s_out_fname, self.oc_fourcc, self.f_fps, (self.i_frame_w, self.i_frame_h))
            self.b_new_file_at_next_write = False

        self.oc_video_writer.write(na_in)
        self.i_out_frame_id += 1
        self.i_out_frame_id_cumsum += 1

        if self.i_out_frame_id >= self.i_nframes_per_file:
            self.oc_video_writer.release()
            self.i_out_file_id += 1
            self.i_out_frame_id = 0
            self.s_out_fname = os.path.join(self.s_out_rses_dir, "%s%i.avi" % (self.s_file_prefix, self.i_out_file_id))
            self.b_new_file_at_next_write = True

    def write_time_stamp(self, i_frame_src_idx, f_time_stamp):
        if self.oc_master_writer is None:
            self.h_ts_file.write('%i\t%i\t%i\t%i\n' % (i_frame_src_idx, self.i_out_frame_id_cumsum, round(1000 * f_time_stamp), 1))
        else:
            self.oc_master_writer.write_time_stamp(i_frame_src_idx, f_time_stamp)

    def close(self):
        if self.oc_video_writer is not None:
            self.oc_video_writer.release()
            del self.oc_video_writer
            self.oc_video_writer = None

        if self.h_ts_file is not None:
            self.h_ts_file.close()
            self.h_ts_file = None

        if self.s_out_ts_fname is not None:
            del self.s_out_ts_fname
            self.s_out_ts_fname = None

    def write_last_frame(self, na_in):
        self.write_next_frame(na_in)
        self.close()

    def start_new_session(self):
        self.__prepare_new_session()
        return self.s_out_rses_dir
    #
#


class CMuStreamVideoWriter(object):
    def __init__(self, l_do_capture, *args, **kwargs):
        self.t_do_capture = tuple(l_do_capture)
        self.l_video_writers = []
        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            self.l_video_writers.append(None)

    def start_recording(self, d_rec_info):
        s_data_root_dir = d_rec_info['DATA_ROOT_DIR']
        l_vstream_list  = d_rec_info['VSTREAM_LIST']
        if len(l_vstream_list) != len(self.t_do_capture):
            raise RuntimeError("Sanity check failed. This should never happen.")

        i_idx_master = -1
        for i_idx, d_vstream_info in enumerate(l_vstream_list):
            if d_vstream_info is not None and d_vstream_info['IS_MASTER'] == 1:
                i_idx_master = i_idx
                break
        if i_idx_master == -1:
            raise RuntimeError("Sanity check failed. This should never happen.")

        oc_master_writer = CMuPaVideoWriter(
            s_data_root_dir,
            l_vstream_list[i_idx_master]['OUTPUT_FILE_PREFIX'],
            l_vstream_list[i_idx_master]['FPS'],
            l_vstream_list[i_idx_master]['FRAME_WIDTH'],
            l_vstream_list[i_idx_master]['FRAME_HEIGHT']
        )

        for i_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                if i_idx == i_idx_master:
                    self.l_video_writers[i_idx] = oc_master_writer
                    continue
                self.l_video_writers[i_idx] = CMuPaVideoWriter(
                    s_data_root_dir,
                    l_vstream_list[i_idx]['OUTPUT_FILE_PREFIX'],
                    l_vstream_list[i_idx]['FPS'],
                    l_vstream_list[i_idx]['FRAME_WIDTH'],
                    l_vstream_list[i_idx]['FRAME_HEIGHT'],
                    master=oc_master_writer
                )

    def write_next_frame(self, i_sink_id, na_frame):
        self.l_video_writers[i_sink_id].write_next_frame(na_frame)

    def write_time_stamp(self, i_sink_id, f_ts):
        self.l_video_writers[i_sink_id].write_time_stamp(i_sink_id, f_ts)

    def close(self):
        for i_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap and self.l_video_writers[i_idx] is not None:
                self.l_video_writers[i_idx].close()
    #
#
