#!/usr/bin/env python3


import os
import sys
import time

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from PyQt5.QtMultimedia import QCameraInfo, QCamera
from PyQt5.QtMultimediaWidgets import QCameraViewfinder

import cv2 as cv
import numpy as np

from .widgets import CLabeledComboBox


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


class COpenCVframeCaptureThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, i_camera_idx, h_win, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.b_running = False
        self.oc_camera = cv.VideoCapture(i_camera_idx)
        self.i_frame_id = -1 # so valid frame numbers will start from zero

        b_status, self.na_frame = self.oc_camera.read()
        if not b_status:
            raise RuntimeError("Unable to read first frame")

        if self.na_frame.ndim != 3 or self.na_frame.shape[2] != 3:
            raise RuntimeError("Unexpected frame shape: %s" % repr(self.na_frame.shape))

        self.i_frame_h = self.na_frame.shape[0]
        self.i_frame_w = self.na_frame.shape[1]
        self.i_ncolor_channels = self.na_frame.shape[2]
        h_win.ioctlRequest.connect(self.__cb_on_ioctl_requested, Qt.QueuedConnection)

    def run(self):
        self.b_running = True
        while self.b_running:
            if self.isInterruptionRequested():
                self.b_running = False
                break
            b_status, self.na_frame[...] = self.oc_camera.read()
            if not b_status:
                raise RuntimeError("Unable to read next frame")
            self.i_frame_id += 1
            self.frameReady.emit(self.na_frame)
        self.oc_camera.release()

    def __cb_on_ioctl_requested(self, d_ioctl_data):
        raise NotImplementedError("Not implemented yet.")

    def read_prop_sync(self, i_cam_id, i_prop_id):
        return self.oc_camera.get(i_prop_id)

    def update_prop_sync(self, i_cam_id, i_prop_id, prop_new_val):
        prop_old = self.oc_camera.get(i_prop_id)
        self.oc_camera.set(i_prop_id, prop_new_val)
        prop_new = self.oc_camera.get(i_prop_id)
        return (prop_old, prop_new)

    def get_frame(self, i_cam_id):
        return self.na_frame
    #
#


class COpenCVmultiFrameCapThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(str)

    def __init__(self, l_do_capture, l_wins, oc_sink_list, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.t_do_capture = tuple(l_do_capture) # freeze it to prevent changes from outside
        self.b_running = False
        self.b_recording = False
        self.l_cams = []
        self.l_frames = []
        self.l_frame_hwc = [] # list of len() == 3 tuples of frame HEIGHT x WIDTH x COLORS
        self.i_frame_id = -1 # so valid frame numbers will start from zero
        self.oc_sink_list = oc_sink_list
        self.l_ts = []

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                self.l_cams.append(cv.VideoCapture(i_cam_idx))
            else:
                self.l_cams.append(None) # *** WATCH OUT ***

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                b_status, na_frame = self.l_cams[i_cam_idx].read()

                if not b_status:
                    raise RuntimeError("Unable to read first frame from camera number %i" % i_cam_idx)
                if na_frame.ndim != 3 or na_frame.shape[2] != 3:
                    raise RuntimeError("Unexpected frame shape: %s from camera number %i" % (repr(na_frame.shape), i_cam_idx))

                self.l_frames.append(na_frame.copy())
                self.l_frame_hwc.append((na_frame.shape[0], na_frame.shape[1], na_frame.shape[2]))
                self.l_ts.append(0.0)

            else:
                self.l_frames.append(None) # *** WATCH OUT ***
                self.l_frame_hwc.append((None, None, None)) # *** WATCH OUT ***
                self.l_ts.append(None) # *** WATCH OUT ***

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                l_wins[i_cam_idx].ioctlRequest.connect(self.__cb_on_ioctl_requested, Qt.QueuedConnection)

    def run(self):
        self.b_running = True
        while self.b_running:
            if self.isInterruptionRequested():
                self.b_recording = False
                self.b_running = False
                break

            # grab new frame from each capture-enabled camera
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap:
                    b_status = self.l_cams[i_cam_idx].grab()
                    if not b_status:
                        raise RuntimeError("Unable to grab next frame from camera number %i" % i_cam_idx)

            # retrieve and decode frame from each capture-enabled camera
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap:
                    b_status, self.l_frames[i_cam_idx][...] = self.l_cams[i_cam_idx].retrieve()
                    self.l_ts[i_cam_idx] = time.perf_counter()
                    if not b_status:
                        # seems like this happen inevitably during frame rate/size change events
                        raise RuntimeError("Unable to retrieve next frame from camera number %i" % i_cam_idx)

            # push acquired frames into a sink(s) (not necessary files)
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap and self.b_recording:
                    self.oc_sink_list.write_next_frame(i_cam_idx, self.l_frames[i_cam_idx])
                    self.oc_sink_list.write_time_stamp(i_cam_idx, self.l_ts[i_cam_idx])

            self.i_frame_id += 1
            self.frameReady.emit('frameReady') # argument doesn't matter

        # Both - 'Preview' and 'Recording' states are done here.
        # All preview windows will be destroyed and all video writers must be
        # closed right after an instance of this class is done it's work.
        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                self.l_cams[i_cam_idx].release()

    def __cb_on_ioctl_requested(self, d_ioctl_data):
        # print(d_ioctl_data)
        pass

    def __check_cam_or_die(self, i_cam_id):
        if i_cam_id < 0 or i_cam_id >= len(self.l_cams):
            raise ValueError("Unknown camera index: %i" % i_cam_id)
        if not self.t_do_capture[i_cam_id]:
            raise ValueError("Capture mode for camera number %i is not enabled" % i_cam_id)

    def read_prop_sync(self, i_cam_id, i_prop_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_cams[i_cam_id].get(i_prop_id)

    def update_prop_sync(self, i_cam_id, i_prop_id, prop_new_val):
        self.__check_cam_or_die(i_cam_id)
        prop_old = self.l_cams[i_cam_id].get(i_prop_id)
        self.l_cams[i_cam_id].set(i_prop_id, prop_new_val)
        prop_new = self.l_cams[i_cam_id].get(i_prop_id)
        return (prop_old, prop_new)

    def get_frame(self, i_cam_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_frames[i_cam_id]

    def start_recording(self, d_rec_info):
        s_data_root_dir = d_rec_info['DATA_ROOT_DIR']
        l_vstream_list  = d_rec_info['VSTREAM_LIST']
        if len(l_vstream_list) != len(self.l_cams):
            raise RuntimeError("Sanity check failed. This should never happen.")

        i_idx_master = -1
        for i_idx, d_vstream_info in enumerate(l_vstream_list):
            if d_vstream_info != None and d_vstream_info['IS_MASTER'] == 1:
                i_idx_master = i_idx
                break
        if i_idx_master == -1:
            raise RuntimeError("Sanity check failed. This should never happen.")

        self.b_recording = True
    #
#
