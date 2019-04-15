#!/usr/bin/env python3


import os
import sys

import PyQt5 # hint for pyinstaller
from PyQt5 import QtWidgets
from PyQt5.QtMultimedia import QCameraInfo, QCamera
from PyQt5.QtMultimediaWidgets import QCameraViewfinder


"""
Copyright (C) 2019 Denis Polygalov,
Laboratory for Circuit and Behavioral Physiology,
RIKEN Center for Brain Science, Saitama, Japan.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, a copy is available at
http://www.fsf.org/
"""


class CMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)
        self.oc_camera = None
        self.l_cameras = QCameraInfo.availableCameras()
        if len(self.l_cameras) == 0:
            self.fatal_error("No cameras found!")

        # Top tool-bar
        self.oc_toolbar = QtWidgets.QToolBar("Video source selector")
        self.oc_toolbar.setMovable(False)

        lbl = QtWidgets.QLabel("Select video source:")
        self.oc_toolbar.addWidget(lbl)

        camera_selector = QtWidgets.QComboBox()
        camera_selector.addItems([ "[ %i ] %s" % (i_idx, oc_cam.description()) for i_idx, oc_cam in enumerate(self.l_cameras)])
        camera_selector.currentIndexChanged.connect( self.start_preview )

        self.oc_toolbar.addWidget(camera_selector)
        self.oc_toolbar.layout().setSpacing(5)
        self.oc_toolbar.layout().setContentsMargins(5, 5, 5, 5)
        self.addToolBar(self.oc_toolbar)

        # Central part (video frame)
        self.oc_viewfinder = QCameraViewfinder()
        self.setCentralWidget(self.oc_viewfinder)

        # Bottom status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

        self.setWindowTitle("CamView")
        self.start_preview(0)

    def fatal_error(self, s_msg):
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def start_preview(self, i_cam_idx):
        if self.oc_camera != None:
            self.oc_camera.stop()
            del self.oc_camera
        self.oc_camera = QCamera(self.l_cameras[i_cam_idx])
        self.oc_camera.setViewfinder(self.oc_viewfinder)
        self.oc_camera.setCaptureMode(QCamera.CaptureVideo)
        self.oc_camera.error.connect(lambda: self.show_error(self.oc_camera.errorString()))
        self.oc_camera.start()

    def stop_preview(self):
        if self.oc_camera == None:
            return # this is correct logic, no error here
        self.oc_camera.stop()
        self.oc_camera.unload()
        self.oc_camera = None

    def show_error(self, s):
        err = QtWidgets.QErrorMessage(self)
        err.showMessage(s)

    def closeEvent(self, event):
        self.stop_preview()
    #


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CamView")

    oc_main_win = CMainWindow()
    oc_main_win.show()
    sys.exit(app.exec_())
#

