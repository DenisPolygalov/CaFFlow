#!/usr/bin/env python3


import os
import sys
import time

import PyQt5 # hint for pyinstaller
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtMultimedia import QCameraInfo

import cv2 as cv

from common.widgets import CLabeledComboBox
from common.widgets import CLabeledSpinSlider
from common.preview import CQCameraPreviewWindow
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


class CMainWindow(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)

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

        if self.win_preview != None:
            self.win_preview.close()
            del self.win_preview
            self.win_preview = None

        i_idx = self.cbox_cam_selector.currentIndex()
        s_cam_descr = self.l_cameras[i_idx].description()

        # >>> window type selection depend on the present hardware <<<
        if s_cam_descr.find("MINISCOPE") >= 0:
            self.win_preview = CMiniScopePreviewWindow()
            self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        elif s_cam_descr.find("C310") >= 0:
            self.win_preview = CMiniScopePreviewWindow(b_emulation_mode=True)
            self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        elif s_cam_descr.find("Tape Recorder") >= 0:
            self.win_preview = COpenCVPreviewWindow()
            self.oc_frame_cap_thread = COpenCVframeCaptureThread(i_idx, self.win_preview)

        else:
            self.win_preview = CQCameraPreviewWindow()
            # WARNING: do not create self.oc_frame_cap_thread object
            # for the CQCameraPreviewWindow() type of window!
            # Check self.oc_frame_cap_thread == None all the way below!
        # ------------------------------------------------------------

        self.win_preview.closeSignal.connect(self.__cb_on_preview_closed)
        self.win_preview.show()
        self.win_preview.start_preview(i_idx, self.l_cameras[i_idx], self.oc_frame_cap_thread)
        if self.oc_frame_cap_thread != None:
            self.oc_frame_cap_thread.start()

    def __cb_on_preview_closed(self):
        self.__interrupt_threads_gracefully()
        self.btn_preview.setEnabled(True)
        self.cbox_cam_selector.setEnabled(True)
    #

    def __interrupt_threads_gracefully(self):
        if self.oc_frame_cap_thread != None:
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
        if self.win_preview != None:
            self.win_preview.close()
#


class CMiniScopePreviewWindow(COpenCVPreviewWindow):
    def __init__(self, b_emulation_mode=False, *args, **kwargs):
        super(CMiniScopePreviewWindow, self).__init__(*args, b_enable_close_button=True, **kwargs)

        self._DEVICE_ID = 0x12
        self._RECORD_START = 0x01
        self._RECORD_END = 0x02
        self._TRIG_RECORD_EXT = 0x02
        self._SET_CMOS_SETTINGS = 0x03
        self._INIT_FRATE_VAL = 20 # in Hz
        self._INIT_FRATE_IDX = 3 # (20 Hz)
        self.t_frate_names = ("5 Hz", "10 Hz", "15 Hz", "20 Hz", "30 Hz", "60 Hz")
        self.t_frate_values = (0x11, 0x12, 0x13, 0x14, 0x15, 0x16)
        self._INIT_EXPOSURE = 255
        self._INIT_GAIN = 16
        self._INIT_EXCITATION = 0

        self.b_emulation_mode = b_emulation_mode
        if self.b_emulation_mode:
            self.setWindowTitle("Miniscope (EMULATION)")
        else:
            self.setWindowTitle("Miniscope")

        self.toolbar = QtWidgets.QToolBar("Preview")

        self.btn_set_cmos = QtWidgets.QPushButton("RESET")
        self.btn_set_cmos.clicked.connect(self.__cb_on_set_CMOS_btn_clicked)
        self.btn_set_cmos.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.toolbar.addWidget(self.btn_set_cmos)
        self.toolbar.addSeparator()

        self.cbox_frame_rate = CLabeledComboBox("Frame Rate:")
        self.cbox_frame_rate.cbox.addItems(self.t_frate_names)
        self.cbox_frame_rate.cbox.setCurrentIndex(self._INIT_FRATE_IDX)
        self.cbox_frame_rate.cbox.currentIndexChanged.connect(self.__cb_on_frame_rate_cbox_index_changed)
        self.toolbar.addWidget(self.cbox_frame_rate)
        self.toolbar.addSeparator()

        self.sld_exposure = CLabeledSpinSlider("Exposure:", (1, 255), 1, cb_action=self.__cb_on_exposure_changed)
        self.toolbar.addWidget(self.sld_exposure)
        self.toolbar.addSeparator()
        
        self.sld_gain = CLabeledSpinSlider("Gain:", (16, 64), 1, cb_action=self.__cb_on_gain_changed)
        self.toolbar.addWidget(self.sld_gain)
        self.toolbar.addSeparator()
        
        self.sld_excitation = CLabeledSpinSlider("Excitation:", (0, 100), 1, cb_action=self.__cb_on_excitation_changed)
        self.toolbar.addWidget(self.sld_excitation)
        self.toolbar.addSeparator()

        # top side tool-bar
        self.addToolBar(self.toolbar)

    def __reset_UI(self):
        self.update_cap_prop(cv.CAP_PROP_SATURATION, self._SET_CMOS_SETTINGS)
        self.cbox_frame_rate.cbox.setCurrentIndex(self._INIT_FRATE_IDX)
        self.sld_exposure.slider.setSliderPosition(self._INIT_EXPOSURE)
        self.sld_gain.slider.setSliderPosition(self._INIT_GAIN)
        self.sld_excitation.slider.setSliderPosition(self._INIT_EXCITATION)
        # TODO add here (re)initialization code for other GUI elements
        # DO NOT call self.update_cap_prop() here. Such calls must be
        # implemented in the correspondent event handlers (i.e. self.__cb_on_*)

    def __cb_on_set_CMOS_btn_clicked(self, event):
        if not self.is_started(): return
        self.__reset_UI()

    def __cb_on_frame_rate_cbox_index_changed(self, event):
        if not self.is_started(): return
        self.update_cap_prop(cv.CAP_PROP_SATURATION, self.t_frate_values[self.cbox_frame_rate.cbox.currentIndex()])

    def __cb_on_exposure_changed(self, i_new_value):
        self.update_cap_prop(cv.CAP_PROP_BRIGHTNESS, i_new_value)

    def __cb_on_gain_changed(self, i_new_value):
        # Gains between 32 and 64 must be even for MT9V032
        if i_new_value >= 32 and (i_new_value % 2 == 1):
            self.update_cap_prop(cv.CAP_PROP_GAIN, i_new_value + 1)
        else:
            self.update_cap_prop(cv.CAP_PROP_GAIN, i_new_value)

    def __cb_on_excitation_changed(self, i_new_value):
        i_val = int(i_new_value*(0x0FFF)/100)|0x3000
        self.update_cap_prop(cv.CAP_PROP_HUE, (i_val>>4) & 0x00FF)

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)

        if self.b_emulation_mode:
            f_cam_fps = self.get_cap_prop(cv.CAP_PROP_FPS)
            if abs(f_cam_fps - self._INIT_FRATE_VAL) > 0.5:
                self.update_cap_prop(cv.CAP_PROP_FPS, self._INIT_FRATE_VAL)

        self.__reset_UI()
    #
#


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("msView")

    oc_main_win = CMainWindow()
    oc_main_win.show()
    sys.exit(app.exec_())
#

