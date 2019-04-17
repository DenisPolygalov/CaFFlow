#!/usr/bin/env python3

import os
import sys


import PyQt5 # hint for pyinstaller
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtMultimedia import QCameraInfo

import cv2 as cv
from gui.preview import COpenCVPreviewWindow


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
    def __init__(self, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)
        self.i_frame_id = -1

        self.l_cameras = QCameraInfo.availableCameras()
        if len(self.l_cameras) == 0:
            raise RuntimeError("No cameras found!")

        self.start_preview(0, self.l_cameras[0])

    def frameReady(self, na_frame):
        self.update()
        self.i_frame_id += 1
        print(self.i_frame_id, na_frame.shape, na_frame.dtype, na_frame.min(), na_frame.max(), na_frame.mean())
    #
#


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CamViewOpenCV")

    oc_main_win = CMainWindow()
    oc_main_win.show()
    sys.exit(app.exec_())
#

