#!/usr/bin/env python3

import os
import sys
import platform
import datetime

import cv2 as cv
import numpy as np
import scipy.io as sio

from PyQt5 import QtWidgets

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
The SamTraker.py is a Semi-automatic mouse Tracker, - standalone
hybrid type (CLI + GUI) appliction for tracking single subject
in a recorded video stream. Output tracking data saved
as Matlab '*_tracking_data.mat' file.
"""


# TODO
# Add automatically generated timestamp to output mat file name?
# Add post-processing stage. Calculate distance traveled here?
# Add 'Subject ID' as user input? https://doc.qt.io/qt-5/qinputdialog.html
# Add pixel2cm constant input calculated based on first ROI selection?
# Allow user to terminate tracking WITH DATA SAVED during/after tracking failure handling?
# Save first accepted frame and first ROI drawn by user?


def process_video_file(s_fname_in, s_out_dir, s_out_fname_base, max_nframes=None):
    s_fname_out_mat = os.path.join(s_out_dir, s_out_fname_base + "_tracking_data.mat")
    if os.path.isfile(s_fname_out_mat):
        print("ERROR: output file already exist")
        sys.exit(-1)

    # the video source (movie) object
    oc_movie = CMuPaMovieCV((s_fname_in,))

    d_param = {}
    d_param['tracker_type'] = "KCF"
    d_param['aim_color'] = (60, 255, 255)
    d_param['aim_thickness'] = 2

    # extract video file parameters needed for detector
    d_param['frame_rate'] = oc_movie.df_info.loc[0, 'frame_rate']
    d_param['frames'] = oc_movie.df_info.loc[0, 'frames']

    i_frame_id = 0 # the frame counter
    t_ROI = None # current(!) ROI
    i_key_code = -1
    i_esc_key_code = 27
    oc_tracker = None # the video tracker instance
    na_tmp_img = None

    while(oc_movie.read_next_frame()):
        if not isinstance(na_tmp_img, np.ndarray):
            na_tmp_img = oc_movie.na_frame.copy()
        else:
            na_tmp_img[...] = oc_movie.na_frame[...]

        # yellow color frame-sized rectangle is used as indicator of first frame selection request
        cv.rectangle(na_tmp_img, (0,0), (na_tmp_img.shape[1], na_tmp_img.shape[0]), (0,255,255), 5)

        # Show current frame to user and ask for decision
        cv.imshow(s_out_fname_base, na_tmp_img)
        print("USER_INPUT_REQUEST: current frame #%i (a)ccept? (n)ext? (Esc)ape?" % i_frame_id)

        i_key_code = get_user_key_or_die(['a','n'])

        if i_key_code == ord('a'):
            break
        elif i_key_code == ord('n'):
            i_frame_id += 1
            continue
        else:
            raise ValueError("this should never happen")

    print("INFO: accepted frame #%i" % i_frame_id)

    b_is_frame_ready = True
    while b_is_frame_ready:
        if i_frame_id % 100 == 0: print("INFO: process frame #%i HINT: press 'r' to reset and assign new ROI" % (i_frame_id))

        if oc_tracker is None:
            d_param['initial_frame_number'] = i_frame_id
            print("USER_INPUT_REQUEST: select object to be tracked")
            d_param['initial_ROI'] = selectROI_or_die(s_out_fname_base, oc_movie.na_frame)
            print("INFO: selected ROI for the frame #%i: %s" % (i_frame_id, d_param['initial_ROI']))
            oc_tracker = CSingleSubjectTracker(
                oc_movie.na_frame.shape[0], # frame height
                oc_movie.na_frame.shape[1], # frame width
                oc_movie.na_frame.dtype,
                d_param
            )

        oc_tracker.process_frame(oc_movie.na_frame)
        cv.imshow(s_out_fname_base, oc_tracker.na_out)

        if not oc_tracker.is_tracking_succeed():
            print("WARNING: tracking failed at frame #%i" % i_frame_id)
            print("USER_INPUT_REQUEST: current frame #%i (a)ccept? (n)ext? (Esc)ape?" % i_frame_id)

            i_key_code = get_user_key_or_die(['a','n'])

            if i_key_code == ord('a'):
                print("USER_INPUT_REQUEST: accepted frame #%i. Select next ROI" % i_frame_id)
                t_ROI = selectROI_or_die(s_out_fname_base, oc_movie.na_frame)
                print("INFO: selected new ROI for the frame #%i: %s" % (i_frame_id, t_ROI))
                oc_tracker.restart_tracking(oc_movie.na_frame, t_ROI)
                b_is_frame_ready = oc_movie.read_next_frame() # WATCH OUT for number of calls
                i_frame_id += 1
                continue

            elif i_key_code == ord('n'):
                oc_tracker.skip_frame()
                b_is_frame_ready = oc_movie.read_next_frame() # WATCH OUT for number of calls
                i_frame_id += 1
                continue

            else: raise ValueError("this should never happen")

        # Wait for key press for 1ms
        i_key_code = cv.waitKey(1)
        i_key_code = i_key_code & 0xFF

        if i_key_code == ord('r'):
            print("USER_INPUT_REQUEST: ROI reset requested at frame #%i. Select new ROI" % i_frame_id)
            t_ROI = selectROI_or_die(s_out_fname_base, oc_movie.na_frame)
            print("INFO: selected new ROI for the frame #%i: %s" % (i_frame_id, t_ROI))
            oc_tracker.restart_tracking(oc_movie.na_frame, t_ROI)

        # Exit unconditionally if ESC key was pressed
        if i_key_code == i_esc_key_code: break

        b_is_frame_ready = oc_movie.read_next_frame() # WATCH OUT for number of calls
        i_frame_id += 1

        if max_nframes is not None and i_frame_id >= max_nframes: break
    #

    if i_key_code == i_esc_key_code:
        print("ERROR: interrupted by user. Tracking data is NOT saved!")
        sys.exit(-1)

    # seal output data into numpy arrays
    oc_tracker.finalize_tracking()
    # add extra parameters to be saved
    oc_tracker.d_STRACK['input_file_name'] = s_fname_in
    oc_tracker.d_STRACK['output_file_name'] = s_fname_out_mat
    oc_tracker.d_STRACK['hostname'] = platform.node()
    oc_tracker.d_STRACK['username'] = os.getlogin()
    oc_tracker.d_STRACK['datetime'] = str(datetime.datetime.now())
    # save output data into the mat file
    sio.savemat(s_fname_out_mat, oc_tracker.d_STRACK)
#


def get_user_key_or_die(l_key_choices):
    """
    Ask user to press one of keys listed in the l_key_choices
    or interrupt the whole script if 'q' or 'Esc' pressed.
    """
    while True:
        # Wait for key press indefinitely
        i_key_code = cv.waitKey(-1)
        i_key_code = i_key_code & 0xFF

        if i_key_code == 27 or i_key_code == ord('q'):
            print("ERROR: interrupted by user. No data saved.")
            sys.exit(-1)

        for _, ch in enumerate(l_key_choices):
            if i_key_code == ord(ch): return i_key_code

        print("ERROR: unknown key pressed")
        continue
    #
#


def selectROI_or_die(s_window_name, na_frame):
    """
    Ask user to draw the ROI on the frame.
    Providing acceptable ROI is obligatory for this script.
    """
    t_ROI = None
    while True:
        t_ROI = cv.selectROI(s_window_name, na_frame, False)
        if t_ROI[0] == 0 and all(i_elem == t_ROI[0] for i_elem in t_ROI):
            print("WARNING: selection was canceled or wrong")
        else:
            break
    if tuple is not type(t_ROI) or len(t_ROI) != 4:
        print("ERROR: something went seriously wrong. Exiting...")
        sys.exit(-1)
    return t_ROI
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)

    from mendouscopy.mupamovie import CMuPaMovieCV
    from mendouscopy.behavior import CSingleSubjectTracker

    i_max_nframes = None
    s_start_dir = os.path.expanduser('~')
    oc_app = QtWidgets.QApplication(sys.argv)
    s_file_filter = "Video Files(*.avi *.mp4 *.wmv *.mov *.mpg *.m4v *.mkv *.ts *.mjpg);; All Files(*.*)"

    while True:
        s_fname_in, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Select input video file", directory=s_start_dir, filter=s_file_filter)

        if not os.path.isfile(s_fname_in):
            print("ERROR: input file is not accessible")
            sys.exit(-1)

        s_out_dir, s_fname = os.path.split(s_fname_in)
        if not os.path.isdir(s_out_dir):
            print("ERROR: output directory is not accessible")
            sys.exit(-1)

        s_out_fname_base, _ = os.path.splitext(s_fname)
        process_video_file(s_fname_in, s_out_dir, s_out_fname_base, max_nframes=i_max_nframes)
        cv.destroyAllWindows()

        oc_reply = QtWidgets.QMessageBox.question(
            None, 'Continue or Quit?',
            'Processing complete.\nDo you want to process another file?',
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )

        if oc_reply == QtWidgets.QMessageBox.Yes:
            s_start_dir = s_out_dir
            continue
        else:
            break
    print()
#

