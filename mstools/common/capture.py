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

    def get_cam_cap_prop(self, i_cam_id, i_prop_id):
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

