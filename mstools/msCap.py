#!/usr/bin/env python3


import os
import sys
import time

import PyQt5 # hint for pyinstaller
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtMultimedia import QCameraInfo, QCamera

import cv2 as cv

from common.widgets import CLabeledComboBox
from common.widgets import CLabeledSpinSlider
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


def camera_sync_load_and_start(oc_qcamera):
    cam_status = oc_qcamera.status()
    if cam_status != QCamera.UnloadedStatus:
        print("ERROR: unexpected camera status: %s" % status2str(cam_status))
        sys.exit(-1)
    i_sec_cnt = 0
    oc_qcamera.load()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to load camera")
                sys.exit(-1)
    i_sec_cnt = 0
    oc_qcamera.start()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.ActiveStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to start camera")
                sys.exit(-1)
#


def camera_sync_stop_and_unload(oc_qcamera):
    cam_status = oc_qcamera.status()
    if cam_status != QCamera.ActiveStatus:
        print("ERROR: unexpected camera status: %s" % status2str(cam_status))
        sys.exit(-1)
    i_sec_cnt = 0
    oc_qcamera.stop()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to stop camera")
                sys.exit(-1)
    i_sec_cnt = 0
    oc_qcamera.unload()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.UnloadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to unload camera")
                sys.exit(-1)
#


class COpenCVmultiFrameCapThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(str)

    def __init__(self, l_do_capture, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.t_do_capture = tuple(l_do_capture) # freeze it to prevent changes from outside
        self.b_running = False
        self.l_cams = []
        self.l_frames = []
        self.l_frame_hwc = [] # list of len() == 3 tuples of frame HEIGHT x WIDTH x COLORS
        self.i_frame_id = -1 # so valid frame numbers will start from zero

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

            else:
                self.l_frames.append(None) # *** WATCH OUT ***
                self.l_frame_hwc.append((None, None, None)) # *** WATCH OUT ***

    def run(self):
        self.b_running = True
        while self.b_running:
            if self.isInterruptionRequested():
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
                    if not b_status:
                        raise RuntimeError("Unable to retrieve next frame from camera number %i" % i_cam_idx)

            self.i_frame_id += 1
            self.frameReady.emit('frameReady') # argument doesn't matter

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                self.l_cams[i_cam_idx].release()

    def __check_cam_or_die(self, i_cam_id):
        if i_cam_id < 0 or i_cam_id >= len(self.l_cams):
            raise ValueError("Unknown camera index: %i" % i_cam_id)
        if not self.t_do_capture[i_cam_id]:
            raise ValueError("Capture mode for camera number %i is not enabled" % i_cam_id)

    def get_cam_cap_prop(self, i_cam_id, i_prop_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_cams[i_cam_id].get(i_prop_id)

    def update_cam_cap_prop(self, i_cam_id, i_prop_id, prop_new_val):
        self.__check_cam_or_die(i_cam_id)
        prop_old = self.l_cams[i_cam_id].get(i_prop_id)
        self.l_cams[i_cam_id].set(i_prop_id, prop_new_val)
        prop_new = self.l_cams[i_cam_id].get(i_prop_id)
        return (prop_old, prop_new)

    def get_frame(self, i_cam_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_frames[i_cam_id]
    #
#


class CTableItemDelegate(QtWidgets.QItemDelegate):
    def createEditor(self, parent, option, index):
        comboBox = QtWidgets.QComboBox(parent)
        comboBox.addItem("disabled")
        comboBox.addItem("ENABLED")
        comboBox.activated.connect(self.emitCommitData)
        return comboBox

    def setEditorData(self, editor, index):
        comboBox = editor
        if not comboBox:
            return

        pos = comboBox.findText(index.model().data(index), Qt.MatchExactly)
        comboBox.setCurrentIndex(pos)

    def setModelData(self, editor, model, index):
        comboBox = editor
        if not comboBox:
            return

        model.setData(index, comboBox.currentText())

    def emitCommitData(self):
        self.commitData.emit(self.sender())
#


class CMainWindow(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)
        self.oc_frame_cap_thread = None
        self.l_wins = []

        # check if we have any cameras before doing anything else
        self.l_caminfos = QCameraInfo.availableCameras()
        if len(self.l_caminfos) == 0:
            self.fatal_error("No cameras found!")

        self.oc_vsrc_table = QtWidgets.QTableWidget()
        self.oc_vsrc_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.oc_vsrc_table.setItemDelegate(CTableItemDelegate(self))
        self.oc_vsrc_table.horizontalHeader().setDefaultSectionSize(90)
        self.oc_vsrc_table.setColumnCount(2)
        self.oc_vsrc_table.setHorizontalHeaderLabels(("Video Source", "Status"))
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.oc_vsrc_table.verticalHeader().hide()

        for i_idx, oc_cam_info in enumerate(self.l_caminfos):
            self.__add_row(oc_cam_info.description())
        self.oc_vsrc_table.resizeColumnsToContents()

        self.btn_preview = QtWidgets.QPushButton("PREVIEW")
        self.btn_preview.clicked.connect(self.__cb_on_btn_preview)

        self.btn_record = QtWidgets.QPushButton("REC")
        self.btn_record.clicked.connect(self.__cb_on_btn_record)
        self.btn_record.setEnabled(False)

        self.btn_stop = QtWidgets.QPushButton("STOP")
        self.btn_stop.clicked.connect(self.__cb_on_btn_stop)
        self.btn_stop.setEnabled(False)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.oc_vsrc_table, 0, 0, 1, 3)
        layout.addWidget(self.btn_preview, 1, 0, 1, 1)
        layout.addWidget(self.btn_record, 1, 1, 1, 1)
        layout.addWidget(self.btn_stop, 1, 2, 1, 1)

        self.setLayout(layout)
        self.setMinimumWidth(500)
        self.setWindowTitle("Video Source Manager")

    def __add_row(self, s_vsrc_name):
        i_nrows = self.oc_vsrc_table.rowCount()
        self.oc_vsrc_table.setRowCount(i_nrows + 1)
        item0 = QtWidgets.QTableWidgetItem(s_vsrc_name)
        item1 = QtWidgets.QTableWidgetItem("disabled")
        self.oc_vsrc_table.setItem(i_nrows, 0, item0)
        self.oc_vsrc_table.setItem(i_nrows, 1, item1)
        self.oc_vsrc_table.openPersistentEditor(item1)

    def __cb_on_btn_preview(self):
        i_ncols = self.oc_vsrc_table.columnCount()
        if i_ncols < 2:
            raise ValueError("Sanity check failed: %i" % i_ncols)

        if self.oc_frame_cap_thread != None:
            raise RuntimeError("Preallocated thread detected!")

        l_do_capture = []
        for i_row_id in range(self.oc_vsrc_table.rowCount()):
            item1 = self.oc_vsrc_table.item(i_row_id, 1)
            if item1.text() == "ENABLED":
                l_do_capture.append(True)
            else:
                l_do_capture.append(False)

        if not any(item == True for item in l_do_capture):
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "No video source enabled.\nSet the 'Status' to 'ENABLE' for at least one video source.")
            return

        self.btn_preview.setEnabled(False)

        for i_idx, oc_cam_info in enumerate(self.l_caminfos):
            if l_do_capture[i_idx]:
                s_cam_descr = oc_cam_info.description()

                # >>> window type selection depend on the present hardware <<<
                if (s_cam_descr.find("MINISCOPE") >= 0) or (s_cam_descr.find("C310") >= 0):
                    self.l_wins.append(CMiniScopePreviewWindow())

                elif s_cam_descr.find("Tape Recorder") >= 0:
                    self.l_wins.append(CSillyCameraPreviewWindow())

                else:
                    # TODO FIXME shall we move this into the CSmartCameraPreviewWindow's constructor?
                    oc_cam = QCamera(oc_cam_info)
                    camera_sync_load_and_start(oc_cam)
                    l_resolutions = oc_cam.supportedViewfinderResolutions()
                    l_frate_ranges = oc_cam.supportedViewfinderFrameRateRanges()
                    camera_sync_stop_and_unload(oc_cam)
                    del oc_cam

                    if len(l_frate_ranges) == 0 or len(l_resolutions) == 0:
                        raise RuntimeError("The camera (%s) does not support frame rate/resolution information retrieval" % s_cam_descr)
                    self.l_wins.append(CSmartCameraPreviewWindow(l_frate_ranges, l_resolutions))
                # ------------------------------------------------------------
            else:
                self.l_wins.append(None)

        self.oc_frame_cap_thread = COpenCVmultiFrameCapThread(l_do_capture)
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None: continue
            oc_win.show()
            oc_win.start_preview(i_idx, self.l_caminfos[i_idx], self.oc_frame_cap_thread)

        self.oc_frame_cap_thread.start()
        self.btn_record.setEnabled(True)
        self.btn_stop.setEnabled(True)
    #

    def __cb_on_btn_record(self):
        self.btn_record.setEnabled(False)
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None: continue
            print("Start recording from source: %s" % self.l_caminfos[i_idx].description())

    def __cb_on_btn_stop(self):
        self.__interrupt_threads_gracefully()
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None: continue
            oc_win.close()
            del oc_win
            self.l_wins[i_idx] = None
        self.l_wins.clear()
        self.btn_preview.setEnabled(True)
        self.btn_record.setEnabled(False)
        self.btn_stop.setEnabled(False)

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
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None: continue
            oc_win.close()
            del oc_win
            self.l_wins[i_idx] = None
        self.l_wins.clear()
    #
#


class CSillyCameraPreviewWindow(COpenCVPreviewWindow):
    def __init__(self, *args, **kwargs):
        super(CSillyCameraPreviewWindow, self).__init__(*args, **kwargs)

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)
        # Get camera properties such as FPS and/or frame size here
        # by using self.get_cap_prop(cv.CAP_PROP_FPS) etc.
#


class CSmartCameraPreviewWindow(COpenCVPreviewWindow):
    def __init__(self, l_frate_ranges, l_resolutions, *args, **kwargs):
        super(CSmartCameraPreviewWindow, self).__init__(*args, **kwargs)
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

    def __cb_on_resolution_cbox_index_changed(self, i_idx):
        print("resolution", i_idx)
        # TODO use self.update_cap_prop() to change GUI settings here

    def __cb_on_frame_rate_cbox_index_changed(self, i_idx):
        print("frame_rate", i_idx)
        # TODO use self.update_cap_prop() to change GUI settings here

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)
        # Get camera properties such as FPS and/or frame size here
        # by using self.get_cap_prop(cv.CAP_PROP_FPS) etc.
    #
#

class CMiniScopePreviewWindow(COpenCVPreviewWindow):
    def __init__(self, *args, **kwargs):
        super(CMiniScopePreviewWindow, self).__init__(*args, **kwargs)

        self._DEVICE_ID = 0x12
        self._RECORD_START = 0x01
        self._RECORD_END = 0x02
        self._TRIG_RECORD_EXT = 0x02
        self._SET_CMOS_SETTINGS = 0x03
        self._INIT_FRATE_IDX = 3 # (20 Hz)
        self.t_frate_names = ("5 Hz", "10 Hz", "15 Hz", "20 Hz", "30 Hz", "60 Hz")
        self.t_frate_values = (0x11, 0x12, 0x13, 0x14, 0x15, 0x16)
        self._INIT_EXPOSURE = 255
        self._INIT_GAIN = 16
        self._INIT_EXCITATION = 0
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
        self.__reset_UI()
    #
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.mupawrite import CMuPaVideoWriter

    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("msCap")

    oc_main_win = CMainWindow()
    oc_main_win.show()
    sys.exit(app.exec_())
#

