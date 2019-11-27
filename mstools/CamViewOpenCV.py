#!/usr/bin/env python3

import os
import sys
import time


import PyQt5 # hint for pyinstaller
from PyQt5 import QtWidgets
from PyQt5.QtMultimedia import QCameraInfo

import cv2 as cv
from common.preview import COpenCVPreviewWindow
from common.capture import COpenCVframeCaptureThread


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


class CMainWindow(COpenCVPreviewWindow):
    def __init__(self, d_param, *args, **kwargs):
        super(CMainWindow, self).__init__(d_param, *args, **kwargs)
        self.i_frame_id = -1
        self.f_ts_prev = time.perf_counter()

    def frameReady(self, na_frame):
        f_ts_curr = time.perf_counter()
        s_FPS = "%.1f" % (1.0/(f_ts_curr - self.f_ts_prev))
        self.f_ts_prev = f_ts_curr
        self.update()
        self.i_frame_id += 1
        print(self.i_frame_id, s_FPS, na_frame.shape, na_frame.dtype, na_frame.min(), na_frame.max(), na_frame.mean(), )
    #
#


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CamViewOpenCV")

    l_cameras = QCameraInfo.availableCameras()
    if len(l_cameras) == 0:
        raise RuntimeError("No cameras found!")

    i_camera_idx = 0
    d_param = {}
    d_param['is_master'] = True

    oc_main_win = CMainWindow(d_param, b_enable_close_button=True)
    oc_frame_cap_thread = COpenCVframeCaptureThread(i_camera_idx, oc_main_win)
    oc_main_win.start_preview(i_camera_idx, l_cameras[i_camera_idx], oc_frame_cap_thread)
    oc_frame_cap_thread.start()
    oc_main_win.show()
    app.exec_()
    oc_frame_cap_thread.requestInterruption()
    oc_frame_cap_thread.wait(10000)
#

