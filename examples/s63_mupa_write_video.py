#!/usr/bin/env python3


import os
import sys

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

"""
This script is designed for testing your PC hardware/software environment for
ability to record MULTI-STREAM video using lossless compression (FFV1) codec.
At least two video sources (web camera, Miniscope, etc) must be connected to
your PC prior to execution of this script.
The output video files will be saved in a sub-directory named automatically
according to the time of execution of this script, e.g. ./2018-08-18_12-35-56
"""


def write_single_session(oc_vcap, oc_writer, i_nframes_max):
    i_frame_cnt = 0
    while(oc_vcap.isOpened()):
        b_ret, na_frame = oc_vcap.read()

        if b_ret:
            # flips the camera so that image is upside down
            na_frame = cv.flip(na_frame, 0)
            oc_writer.write_next_frame(na_frame)
            cv.imshow('frame', na_frame)
            i_frame_cnt += 1

            if i_frame_cnt % 10 == 0:
                print("Captured/written %i frames out of %i" % (i_frame_cnt, i_nframes_max))

            # breaks once maximum frame number is reached
            if i_frame_cnt >= i_nframes_max: break

            if cv.waitKey(1) & 0xFF == ord('q'):  # TODO does not work with MacOS
               break
        else:
            raise RuntimeError("Unable to read frame from video capturing device")
#


def test_single_stream():
    f_fps_desired = 20.0
    i_nframes_max = 200
    oc_vcap = cv.VideoCapture(0)
    f_fps = oc_vcap.get(cv.CAP_PROP_FPS)
    i_frame_w = int(oc_vcap.get(cv.CAP_PROP_FRAME_WIDTH))
    i_frame_h = int(oc_vcap.get(cv.CAP_PROP_FRAME_HEIGHT))

    print("Camera's FPS: %f Hz" % f_fps)
    print("Camera's frame size: %i x %i" % (i_frame_w, i_frame_h))

    if f_fps < 5:
        print("Low/zero FPS returned. Trying to enforce...")
        oc_vcap.set(cv.CAP_PROP_FPS, f_fps_desired)
        f_fps = oc_vcap.get(cv.CAP_PROP_FPS)
        print("Camera's FPS: %f Hz" % f_fps)
        if (f_fps_desired - f_fps) < 0.1:
            print("Enforcing FPS succeed!")
        else:
            print("Enforcing FPS filed! Try anyway...")
            f_fps = f_fps_desired

    oc_writer = CMuPaVideoWriter(".", "msCam", f_fps, i_frame_w, i_frame_h, i_nframes_per_file=100)

    write_single_session(oc_vcap, oc_writer, i_nframes_max)
    s_new_rsess_path = oc_writer.start_new_session()
    print("Starting new recording session at:", s_new_rsess_path)
    write_single_session(oc_vcap, oc_writer, i_nframes_max * 2)

    oc_writer.close()
    oc_vcap.release()
    cv.destroyAllWindows()
#


def write_multi_session(oc_vcap, oc_writer_master, oc_writer_slave, i_nframes_max):
    i_frame_cnt = 0
    while(oc_vcap.isOpened()):
        b_ret, na_frame = oc_vcap.read()

        if b_ret:
            oc_writer_master.write_next_frame(na_frame)
            na_frame = cv.flip(na_frame, 0)
            oc_writer_slave.write_next_frame(na_frame)

            cv.imshow('frame', na_frame)
            i_frame_cnt += 1

            if i_frame_cnt % 10 == 0:
                print("Captured/written %i frames out of %i" % (i_frame_cnt, i_nframes_max))
            if i_frame_cnt >= i_nframes_max: break

            if cv.waitKey(1) & 0xFF == ord('q'):
               break
        else:
            raise RuntimeError("Unable to read frame from video capturing device")
#


def test_multi_stream():
    f_fps_desired = 20.0
    i_nframes_max = 200
    oc_vcap = cv.VideoCapture(0)
    f_fps = oc_vcap.get(cv.CAP_PROP_FPS)
    i_frame_w = int(oc_vcap.get(cv.CAP_PROP_FRAME_WIDTH))
    i_frame_h = int(oc_vcap.get(cv.CAP_PROP_FRAME_HEIGHT))

    print("Camera's FPS: %f Hz" % f_fps)
    print("Camera's frame size: %i x %i" % (i_frame_w, i_frame_h))

    if f_fps < 5:
        print("Low/zero FPS returned. Trying to enforce...")
        oc_vcap.set(cv.CAP_PROP_FPS, f_fps_desired)
        f_fps = oc_vcap.get(cv.CAP_PROP_FPS)
        print("Camera's FPS: %f Hz" % f_fps)
        if (f_fps_desired - f_fps) < 0.1:
            print("Enforcing FPS succeed!")
        else:
            print("Enforcing FPS filed! Try anyway...")
            f_fps = f_fps_desired

    oc_writer_master = CMuPaVideoWriter(".", "msCam", f_fps, i_frame_w, i_frame_h, i_nframes_per_file=100)
    oc_writer_slave = CMuPaVideoWriter(".", "behavCam", f_fps, i_frame_w, i_frame_h, i_nframes_per_file=100, master=oc_writer_master)

    write_multi_session(oc_vcap, oc_writer_master, oc_writer_slave, i_nframes_max)
    s_new_rsess_path = oc_writer_master.start_new_session()
    s_new_rsess_path_slave = oc_writer_slave.start_new_session()
    print("Starting new recording session at:", s_new_rsess_path)
    print("Slave stream must write into same:", s_new_rsess_path_slave)
    write_multi_session(oc_vcap, oc_writer_master, oc_writer_slave, i_nframes_max * 2)

    oc_writer_master.close()
    oc_writer_slave.close()
    oc_vcap.release()
    cv.destroyAllWindows()
#

if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.mupawrite import CMuPaVideoWriter
    test_single_stream()
    test_multi_stream()
#

