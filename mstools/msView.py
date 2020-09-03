#!/usr/bin/env python3


import os
import sys
import configparser

# import PyQt5 # hint for pyinstaller
from PyQt5 import QtWidgets
from PyQt5.QtMultimedia import QCameraInfo

from common.preview import CQCameraPreviewWindow
# from common.preview import COpenCVPreviewWindow
from common.preview import CSillyCameraPreviewWindow
# from common.preview import CSmartCameraPreviewWindow
from common.preview import CMiniScopePreviewWindow
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


class CMainWindow(QtWidgets.QWidget):
    def __init__(self, oc_global_cfg, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)

        self.oc_global_cfg = oc_global_cfg
        self.f_initial_frame_rate = float(self.oc_global_cfg['general']['initial_frame_rate'])

        self.oc_frame_cap_thread = None
        self.win_preview = None

        # check if we have any cameras before doing anything else
        self.l_cameras = QCameraInfo.availableCameras()
        if len(self.l_cameras) == 0:
            self.fatal_error("No cameras found!")

        self.lbl_video_source = QtWidgets.QLabel("Select video source:")

        self.cbox_cam_selector = QtWidgets.QComboBox()
        self.cbox_cam_selector.addItems([ "[ %i ] %s" % (i_idx, oc_cam.description()) for i_idx, oc_cam in enumerate(self.l_cameras)])

        self.btn_preview = QtWidgets.QPushButton("Preview")
        self.btn_preview.clicked.connect(self.__cb_on_btn_preview)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.lbl_video_source, 0, 0, 1, 1)
        layout.addWidget(self.cbox_cam_selector, 1, 0, 1, 1)
        layout.addWidget(self.btn_preview, 1, 1, 1, 1)

        self.setLayout(layout)
        self.setMinimumWidth(350)
        self.setWindowTitle("Video Source Selector")

    def __cb_on_btn_preview(self):
        self.btn_preview.setEnabled(False)
        self.cbox_cam_selector.setEnabled(False)

        if self.win_preview is not None:
            self.win_preview.close()
            del self.win_preview
            self.win_preview = None

        i_idx = self.cbox_cam_selector.currentIndex()
        d_param = {}
        d_param['description'] = self.l_cameras[i_idx].description()
        d_param['emulation_mode'] = False
        d_param['is_master'] = True
        d_param['initial_frame_rate'] = self.f_initial_frame_rate

        # >>> window type selection depend on the present hardware <<<
        if d_param['description'].find("MINISCOPE") >= 0:
            self.win_preview = CMiniScopePreviewWindow(d_param, b_enable_close_button=True)
            self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        #elif d_param['description'].find("C310") >= 0:
            #d_param['emulation_mode'] = True
            #self.win_preview = CMiniScopePreviewWindow(d_param, b_enable_close_button=True)
            #self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        elif d_param['description'].find("Tape Recorder") >= 0:
            self.win_preview = CSillyCameraPreviewWindow(d_param, b_enable_close_button=True)
            self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        else:
            # There are multiple options available for various video sources:

            # 1. Preview window based on QCamera class from PyQt5
            self.win_preview = CQCameraPreviewWindow()
            # WARNING: do not create self.oc_frame_cap_thread object
            # for the CQCameraPreviewWindow() type of window!
            # Check self.oc_frame_cap_thread == None all the way below!
            # To my knowledge QCamera does not provide low level access to video frames.

            # 2. Generic OpenCV based preview window
            # self.win_preview = COpenCVPreviewWindow(d_param, b_enable_close_button=True)
            # self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

            # 3. For type of cameras that does not support parameter retrieval
            # self.win_preview = CSillyCameraPreviewWindow(d_param, b_enable_close_button=True)
            # self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

            # 4. Same as above but provide QCameraInfo and able to change frame rate/resolution
            # self.win_preview = CSmartCameraPreviewWindow(d_param, self.l_cameras[i_idx], b_enable_close_button=True)
            # self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)
        # ------------------------------------------------------------

        self.win_preview.closeSignal.connect(self.__cb_on_preview_closed)
        self.win_preview.show()
        self.win_preview.start_preview(i_idx, self.l_cameras[i_idx], self.oc_frame_cap_thread)
        if self.oc_frame_cap_thread is not None:
            self.oc_frame_cap_thread.start()

    def __cb_on_preview_closed(self):
        self.__interrupt_threads_gracefully()
        self.btn_preview.setEnabled(True)
        self.cbox_cam_selector.setEnabled(True)
    #

    def __interrupt_threads_gracefully(self):
        if self.oc_frame_cap_thread is not None:
            self.oc_frame_cap_thread.requestInterruption()
            self.oc_frame_cap_thread.wait(10000)
            del self.oc_frame_cap_thread
            self.oc_frame_cap_thread = None

    def fatal_error(self, s_msg):
        self.__interrupt_threads_gracefully()
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def closeEvent(self, event):
        self.__interrupt_threads_gracefully()
        if self.win_preview is not None:
            self.win_preview.close()
#


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    s_config_fname = "mstools.ini" # TODO hard-coded for now.
    if not os.path.isfile(s_config_fname):
        raise OSError("Not a regular file: %s" % s_config_fname)
    if not os.access(s_config_fname, os.R_OK):
        raise OSError("Access denied for file: %s" % s_config_fname)

    # load global configuration file
    oc_global_cfg = configparser.ConfigParser()
    oc_global_cfg.read(s_config_fname)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("msView")

    oc_main_win = CMainWindow(oc_global_cfg)
    oc_main_win.show()
    sys.exit(app.exec_())
#

