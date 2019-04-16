#!/usr/bin/env python3


import os
import sys


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


def main():
    f_fps_desired = 20.0
    i_nframes_max = 200
    s_fname_out = 'captured_lossless_video.avi'
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

    oc_fourcc = cv.VideoWriter_fourcc(*'FFV1')
    oc_video_writer = cv.VideoWriter(s_fname_out, oc_fourcc, f_fps, (i_frame_w, i_frame_h))
    print("If you see 'FFMPEG tag ... is not found' error message ABOVE, then your OS is missing FFMPEG encoding support.")

    i_frame_cnt = 0
    while(oc_vcap.isOpened()):
        b_ret, na_frame = oc_vcap.read()

        if b_ret:
            na_frame = cv.flip(na_frame, 0)
            oc_video_writer.write(na_frame)

            i_frame_cnt += 1
            if i_frame_cnt % 10 == 0:
                print("Captured/written %i frames out of %i" % (i_frame_cnt, i_nframes_max))
            if i_frame_cnt >= i_nframes_max: break

            cv.imshow('frame', na_frame)
            if cv.waitKey(1) & 0xFF == ord('q'):
               break
        else:
            break
    oc_video_writer.release()
    oc_vcap.release()
    cv.destroyAllWindows()

    # Test the output file presence and size.
    # The problem here is that in the case of OS-side missing/broken
    # FFMPEG codec no catch-able errors generated.

    if not os.path.isfile(s_fname_out):
        print("ERROR: output file is missing. Check your FFMPEG presence/configuration!")
        sys.exit(-1)

    stat_info = os.stat(s_fname_out)
    if stat_info.st_size < 1e6:
        print("ERROR: output file is present but too small. Check your FFMPEG presence/configuration!")
        sys.exit(-1)

    print("Trying to open the output file by using OpenCV and read it back...")
    oc_video_reader = cv.VideoCapture(s_fname_out)
    if not oc_video_reader.isOpened():
        print("ERROR: unable to open file!")
        sys.exit(-1)

    print("Written file's frame count:",  int(oc_video_reader.get(cv.CAP_PROP_FRAME_COUNT)))
    print("Written file's frame width:",  int(oc_video_reader.get(cv.CAP_PROP_FRAME_WIDTH)))
    print("Written file's frame height:", int(oc_video_reader.get(cv.CAP_PROP_FRAME_HEIGHT)))
    print("Written file's FPS:", float(oc_video_reader.get(cv.CAP_PROP_FPS)))
#


if __name__ == '__main__':
    import cv2 as cv
    import numpy as np
    main()
#

