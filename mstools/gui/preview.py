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


class CQCameraPreviewWindow(QtWidgets.QMainWindow):
    sig_closing_myself = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(CQCameraPreviewWindow, self).__init__(*args, **kwargs)

        self._MIN_WIN_WIDTH = 640
        self.oc_camera_info = None
        self.oc_camera = None
        self.i_camera_idx = -1
        self.b_guard = False
        self.toolbar = QtWidgets.QToolBar("Preview")

        self.cbox_resolution = CLabeledComboBox("Resolution:")
        self.cbox_resolution.cbox.currentIndexChanged.connect(self.__cb_on_resolution_cbox_index_changed)
        self.toolbar.addWidget(self.cbox_resolution)
        self.toolbar.addSeparator()

        self.cbox_frame_rate = CLabeledComboBox("Frame Rate:")
        self.cbox_frame_rate.cbox.currentIndexChanged.connect(self.__cb_on_frame_rate_cbox_index_changed)
        self.toolbar.addWidget(self.cbox_frame_rate)
        self.addToolBar(self.toolbar)
        self.toolbar.addSeparator()

        self.oc_view_finder = QCameraViewfinder()
        self.setCentralWidget(self.oc_view_finder)

    def __cb_on_resolution_cbox_index_changed(self, i_idx):
        if self.oc_camera == None:
            self.fatal_error("Unallocated camera object detected")
        if self.b_guard: return
        l_res = self.cbox_resolution.cbox.itemText(i_idx).split(" x ")
        oc_vf_settings = self.oc_camera.viewfinderSettings()
        if oc_vf_settings.isNull():
            self.fatal_error("Unable to retrieve camera settings")
        i_w, i_h = int(l_res[0]), int(l_res[1])
        oc_vf_settings.setResolution(i_w, i_h)
        self.oc_camera.setViewfinderSettings(oc_vf_settings)
        self.oc_view_finder.setFixedSize(i_w, i_h)
        if i_w >= self._MIN_WIN_WIDTH:
            self.adjustSize()
            self.setFixedSize(self.sizeHint())

    def __cb_on_frame_rate_cbox_index_changed(self, i_idx):
        if self.oc_camera == None:
            self.fatal_error("Unallocated camera object detected")
        if self.b_guard: return
        f_res = float(self.cbox_frame_rate.cbox.itemText(i_idx))
        oc_vf_settings = self.oc_camera.viewfinderSettings()
        if oc_vf_settings.isNull():
            self.fatal_error("Unable to retrieve camera settings")
        oc_vf_settings.setMinimumFrameRate(f_res)
        oc_vf_settings.setMaximumFrameRate(f_res)
        self.oc_camera.setViewfinderSettings(oc_vf_settings)

    def __camera_sync_start(self):
        i_sec_cnt = 0
        self.oc_camera.start()
        while True:
            cam_status = self.oc_camera.status()
            if cam_status == QCamera.ActiveStatus: break
            else:
                time.sleep(1)
                i_sec_cnt += 1
                if i_sec_cnt >= 10: self.fatal_error("Unable to start the camera")

    def __update_UI(self):
        # retrieve all supported resolutions and populate the resolution combo box
        l_resolutions = self.oc_camera.supportedViewfinderResolutions()
        if len(l_resolutions) > 0:
            l_res = []
            for oc_res in l_resolutions:
                l_res.append("%i x %i" % (oc_res.width(), oc_res.height()))
            self.cbox_resolution.cbox.clear()
            self.cbox_resolution.cbox.addItems(l_res)

        oc_vf_settings = self.oc_camera.viewfinderSettings()
        if oc_vf_settings.isNull():
            self.fatal_error("Unable to retrieve camera settings")

        # set current item index in the resolution combo box
        # according to the current resolution of our camera
        oc_curr_res = oc_vf_settings.resolution()
        s_res_hash = "%i x %i" % (oc_curr_res.width(), oc_curr_res.height())
        for i_idx in range(self.cbox_resolution.cbox.count()):
            if self.cbox_resolution.cbox.itemText(i_idx) == s_res_hash:
                self.cbox_resolution.cbox.setCurrentIndex(i_idx)

        # retrieve all supported frame rates and populate the frame rate combo box
        l_frates = self.oc_camera.supportedViewfinderFrameRateRanges()
        if len(l_frates) > 0:
            l_res = []
            for oc_frate in l_frates:
                l_res.append("%f" % oc_frate.minimumFrameRate)
            self.cbox_frame_rate.cbox.clear()
            self.cbox_frame_rate.cbox.addItems(l_res)

        # set current item index in the frame rate combo box
        # according to the current frame rate of our camera
        i_curr_frate = int(oc_vf_settings.minimumFrameRate())
        for i_idx in range(self.cbox_frame_rate.cbox.count()):
            if int(float(self.cbox_frame_rate.cbox.itemText(i_idx))) == i_curr_frate:
                self.cbox_frame_rate.cbox.setCurrentIndex(i_idx)

    def fatal_error(self, s_msg):
        if self.oc_camera != None: self.oc_camera.stop()
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def start_preview(self, i_camera_idx, oc_camera_info):
        if self.oc_camera != None:
            self.fatal_error("Preallocated camera object detected")

        self.i_camera_idx = i_camera_idx
        self.oc_camera_info = oc_camera_info
        self.oc_camera = QCamera(self.oc_camera_info)

        self.oc_camera.setViewfinder(self.oc_view_finder)
        self.oc_camera.setCaptureMode(QCamera.CaptureVideo)
        self.oc_camera.error.connect(lambda: self.show_error_message(self.oc_camera.errorString()))

        self.b_guard = True
        self.__camera_sync_start()
        self.__update_UI()
        self.b_guard = False

        self.setWindowTitle(self.oc_camera_info.description())
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def stop_preview(self):
        if self.oc_camera == None:
            return # this is correct logic, no error here
        self.oc_camera.stop()
        self.oc_camera.unload()
        self.oc_camera = None
        self.oc_camera_info = None

    def is_save_state_needed(self):
        return False

    def save_state(self):
        pass

    def show_error_message(self, s_msg):
        err = QtWidgets.QErrorMessage(self)
        err.showMessage(s_msg)

    def closeEvent(self, event):
        if self.is_save_state_needed():
            self.save_state()
        self.stop_preview()
        self.sig_closing_myself.emit()
    #
#

# FIXME this is software rendering.
# TODO Add OpenGL version of this.
# Note that using QtWidgets.QOpenGLWidget here is NOT simple.
class CNdarrayPreviewWidget(QtWidgets.QWidget):
    def __init__(self, na_frame, *args, **kwargs):
        super(CNdarrayPreviewWidget, self).__init__(*args, **kwargs)

        if na_frame.ndim != 3 or na_frame.shape[2] != 3:
            raise ValueError("Unexpected frame shape: %s" % repr(na_frame.shape))

        self.i_frame_h = na_frame.shape[0]
        self.i_frame_w = na_frame.shape[1]
        self.i_ncolor_channels = na_frame.shape[2]
        self.oc_qimage = QtGui.QImage(
            na_frame.data,
            self.i_frame_w,
            self.i_frame_h,
            na_frame.strides[0],
            QtGui.QImage.Format_RGB888
        )
        self.setFixedSize(self.i_frame_w, self.i_frame_h)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.drawImage(event.rect(), self.oc_qimage)
    #
#


class COpenCVframeCaptureThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, i_camera_idx, *args, **kwargs):
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
    #
#


class COpenCVPreviewWindow(QtWidgets.QMainWindow):
    sig_closing_myself = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(COpenCVPreviewWindow, self).__init__(*args, **kwargs)

        self.oc_view_finder = None
        self.oc_frame_cap_thread = None
        self.oc_camera_info = None
        self.i_camera_idx = -1

        # bottom status bar
        self.sbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.sbar)

    def __cb_on_frameReady(self, na_frame):
        # print(na_frame.shape, na_frame.max())
        self.update()
    #

    def fatal_error(self, s_msg):
        if self.oc_frame_cap_thread != None:
            self.oc_frame_cap_thread.requestInterruption()
            self.oc_frame_cap_thread.wait(10000)
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def start_preview(self, i_camera_idx, oc_camera_info, i_timeout_ms=17):
        if self.oc_frame_cap_thread != None:
            self.fatal_error("Preallocated camera object detected")

        self.i_camera_idx = i_camera_idx
        self.oc_camera_info = oc_camera_info

        self.oc_frame_cap_thread = COpenCVframeCaptureThread(self.i_camera_idx)
        self.oc_frame_cap_thread.frameReady.connect(self.__cb_on_frameReady, Qt.QueuedConnection)

        self.oc_view_finder = CNdarrayPreviewWidget(self.oc_frame_cap_thread.na_frame)
        self.setCentralWidget(self.oc_view_finder)

        self.oc_frame_cap_thread.start()

    def stop_preview(self):
        if self.oc_frame_cap_thread == None:
            return # this is correct logic, no error here

        self.oc_frame_cap_thread.requestInterruption()
        self.oc_frame_cap_thread.wait(10000)
        self.oc_frame_cap_thread = None
        self.oc_camera_info = None
        self.i_camera_idx = -1

    def is_save_state_needed(self):
        return False

    def save_state(self):
        pass

    def closeEvent(self, event):
        if self.is_save_state_needed():
            self.save_state()
        self.stop_preview()
        self.sig_closing_myself.emit()
    #
#

