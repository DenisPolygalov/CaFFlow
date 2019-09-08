#!/usr/bin/env python3


import os
import sys
import time
import configparser

import PyQt5 # hint for pyinstaller
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtMultimedia import QCameraInfo, QCamera

import cv2 as cv

from common.widgets import CTableItemDelegate
from common.preview import COpenCVPreviewWindow
from common.preview import CSillyCameraPreviewWindow
from common.preview import CSmartCameraPreviewWindow
from common.preview import CMiniScopePreviewWindow


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


class COpenCVmultiFrameCapThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(str)

    def __init__(self, l_do_capture, l_wins, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.t_do_capture = tuple(l_do_capture) # freeze it to prevent changes from outside
        self.b_running = False
        self.b_recording = False
        self.l_cams = []
        self.l_frames = []
        self.l_frame_hwc = [] # list of len() == 3 tuples of frame HEIGHT x WIDTH x COLORS
        self.i_frame_id = -1 # so valid frame numbers will start from zero
        self.l_video_writers = []
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

            # write acquired frames into files
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap and self.b_recording:
                    self.l_video_writers[i_cam_idx].write_next_frame(self.l_frames[i_cam_idx])
                    self.l_video_writers[i_cam_idx].write_time_stamp(i_cam_idx, self.l_ts[i_cam_idx])

            self.i_frame_id += 1
            self.frameReady.emit('frameReady') # argument doesn't matter

        # Both - 'Preview' and 'Recording' states are done here.
        # All preview windows will be destroyed and all video writers
        # must be closed here if and only if the 'Recording' was going on.
        # Switching from 'Recording' state to 'Preview' state is not supported.
        # TODO: maybe add this later. Use start_new_session() method?
        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                self.l_cams[i_cam_idx].release()
                if self.b_recording:
                    self.l_video_writers[i_cam_idx].close()

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

        oc_master_writer = CMuPaVideoWriter(
            s_data_root_dir,
            l_vstream_list[i_idx_master]['OUTPUT_FILE_PREFIX'],
            l_vstream_list[i_idx_master]['FPS'],
            l_vstream_list[i_idx_master]['FRAME_WIDTH'],
            l_vstream_list[i_idx_master]['FRAME_HEIGHT']
        )

        for i_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                if i_idx == i_idx_master:
                    self.l_video_writers.append(oc_master_writer)
                    continue
                self.l_video_writers.append(
                    CMuPaVideoWriter(
                        s_data_root_dir,
                        l_vstream_list[i_idx]['OUTPUT_FILE_PREFIX'],
                        l_vstream_list[i_idx]['FPS'],
                        l_vstream_list[i_idx]['FRAME_WIDTH'],
                        l_vstream_list[i_idx]['FRAME_HEIGHT'],
                        master=oc_master_writer
                    )
                )
            else:
                self.l_video_writers.append(None) # *** WATCH OUT ***
        self.b_recording = True
    #
#


class CMainWindow(QtWidgets.QWidget):
    def __init__(self, oc_global_cfg, *args, **kwargs):
        super(CMainWindow, self).__init__(*args, **kwargs)
        self.oc_global_cfg = oc_global_cfg

        self.s_data_root_dir = self.oc_global_cfg['general']['data_root_dir']
        self.s_data_root_dir = self.s_data_root_dir.strip()
        self.f_initial_frame_rate = float(self.oc_global_cfg['general']['initial_frame_rate'])

        self.oc_frame_cap_thread = None
        self.l_wins = []
        self.b_behavCamFound = False

        if not os.path.isdir(self.s_data_root_dir):
            os.mkdir(self.s_data_root_dir)
        if not os.path.isdir(self.s_data_root_dir):
            raise OSError("Not a directory: %s" % self.s_data_root_dir)
        if not os.access(self.s_data_root_dir, os.R_OK):
            raise OSError("Access denied for directory: %s" % self.s_data_root_dir)

        # check if we have any cameras before doing anything else
        self.l_caminfos = QCameraInfo.availableCameras()
        if len(self.l_caminfos) == 0:
            self.fatal_error("No cameras found!")

        self.oc_vsrc_table = QtWidgets.QTableWidget()
        self.oc_vsrc_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.oc_vsrc_table.horizontalHeader().setDefaultSectionSize(90)
        self.oc_vsrc_table.setColumnCount(4)
        self.oc_vsrc_table.setItemDelegateForColumn(2, CTableItemDelegate(self))
        self.oc_vsrc_table.setHorizontalHeaderLabels(("Video Source", "Output File Prefix", "Status", "Master"))
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.oc_vsrc_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.oc_vsrc_table.verticalHeader().hide()

        for i_idx, oc_cam_info in enumerate(self.l_caminfos):
            self.__add_new_row_to_vsrc_table(oc_cam_info.description())
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

    def __add_new_row_to_vsrc_table(self, s_vsrc_name):
        i_nrows = self.oc_vsrc_table.rowCount()
        self.oc_vsrc_table.setRowCount(i_nrows + 1)

        item0 = QtWidgets.QTableWidgetItem(s_vsrc_name)
        item0.setFlags(item0.flags() & ~QtCore.Qt.ItemIsEditable)
        item1 = QtWidgets.QTableWidgetItem()
        item2 = QtWidgets.QTableWidgetItem("disabled")
        item3 = QtWidgets.QTableWidgetItem()
        item3.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)

        if s_vsrc_name.find("MINISCOPE") >= 0 or s_vsrc_name.find("C310") >= 0:
            item1.setText("msCam")
            item3.setCheckState(QtCore.Qt.Checked)
        elif not self.b_behavCamFound:
            self.b_behavCamFound = True
            item1.setText("behavCam")
            item3.setCheckState(QtCore.Qt.Unchecked)
        else:
            item1.setText("viCam%s" % self.__int2ABC(i_nrows + 1))
            item3.setCheckState(QtCore.Qt.Unchecked)

        self.oc_vsrc_table.setItem(i_nrows, 0, item0)
        self.oc_vsrc_table.setItem(i_nrows, 1, item1)
        self.oc_vsrc_table.setItem(i_nrows, 2, item2)
        self.oc_vsrc_table.openPersistentEditor(item2)
        self.oc_vsrc_table.setItem(i_nrows, 3, item3)

    def __int2ABC(self, i_idx):
        # convert 12433 (integer) into 'ABDCC' (string)
        l_out = []
        for _, ch in enumerate(str(i_idx)):
            l_out.append(chr(int(ch)+64))
        return "".join(l_out)

    def __cb_on_btn_preview(self):
        i_ncols = self.oc_vsrc_table.columnCount()
        if i_ncols < 2:
            raise ValueError("Sanity check failed: %i" % i_ncols)

        if self.oc_frame_cap_thread != None:
            raise RuntimeError("Preallocated thread detected!")

        l_do_capture = []
        l_is_master = []
        for i_row_id in range(self.oc_vsrc_table.rowCount()):
            item2 = self.oc_vsrc_table.item(i_row_id, 2)
            if item2.text() == "ENABLED":
                l_do_capture.append(True)
            else:
                l_do_capture.append(False)

            item3 = self.oc_vsrc_table.item(i_row_id, 3)
            if item3.checkState() == QtCore.Qt.Checked:
                l_is_master.append(True)
            else:
                l_is_master.append(False)

        if self.oc_vsrc_table.rowCount() == 1:
            item3 = self.oc_vsrc_table.item(0, 3)
            item3.setCheckState(QtCore.Qt.Checked)
            l_is_master[0] = True

        if not any(item == True for item in l_do_capture):
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "No video source enabled.\nSet the 'Status' to 'ENABLE' for at least one video source.")
            return

        if sum(l_is_master) > 1:
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "Multiple video sources set as master.\nCheck the 'Master' for only single video source.")
            return

        if len(l_is_master) > 1 and sum(l_is_master) == 0:
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "Multiple video sources without master.\nCheck the 'Master' for at least one video source.")
            return

        for i_idx, b_is_master in enumerate(l_is_master):
            if b_is_master and not l_do_capture[i_idx]:
                QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "The Master video source is not enabled.\nSet the 'Status' of the Master video source to 'ENABLE'.")
                return

        self.btn_preview.setEnabled(False)
        self.oc_vsrc_table.setEnabled(False)

        for i_idx, oc_cam_info in enumerate(self.l_caminfos):
            if l_do_capture[i_idx]:
                d_param = {}
                d_param['description'] = oc_cam_info.description()
                d_param['emulation_mode'] = False
                d_param['is_master'] = l_is_master[i_idx]
                d_param['initial_frame_rate'] = self.f_initial_frame_rate

                # >>> window type selection depend on the present hardware <<<
                if d_param['description'].find("MINISCOPE") >= 0:
                    self.l_wins.append(CMiniScopePreviewWindow(d_param))

                elif d_param['description'].find("C310") >= 0:
                    d_param['emulation_mode'] = True
                    self.l_wins.append(CMiniScopePreviewWindow(d_param))

                elif d_param['description'].find("Tape Recorder") >= 0:
                    self.l_wins.append(CSillyCameraPreviewWindow(d_param))

                else:
                    self.l_wins.append(CSmartCameraPreviewWindow(d_param, oc_cam_info))
                # ------------------------------------------------------------
            else:
                self.l_wins.append(None)

        self.oc_frame_cap_thread = COpenCVmultiFrameCapThread(l_do_capture, self.l_wins)
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
        l_FPS = []
        l_vstream_list = []
        # WARNING: the len(self.l_wins) is ALWAYS equal to the number of cameras
        # For 'disabled' cameras however, the self.l_wins contain None values.
        # Here we use the same approach to fill the l_vstream_list
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None:
                l_vstream_list.append(None) # *** WATCH OUT ***
                continue
            d_vstream_info = oc_win.get_vstream_info()
            # WARNING: here we modify the dictionary returned by the get_vstream_info()
            # method above by ADDING additional key/value pairs.
            d_vstream_info['OUTPUT_FILE_PREFIX'] = self.oc_vsrc_table.item(i_idx, 1).text()
            l_FPS.append(d_vstream_info['FPS'])
            l_vstream_list.append(d_vstream_info)
            # TODO:
            # Warn user to change the frame rate values to all equal
            # or synchronize all cameras to the 'maser' one here if possible.
            # Do not allow runtime changes of the frame rate / frame size?
            # Add 'initial_frame_width' and 'initial_frame_height' handling in mstools.ini
            # Implement COpenCVmultiFrameCapThread.__cb_on_ioctl_requested() method
            # Also, it might be necessary to call CMuPaVideoWriter.write_next_frame()
            # in a separated thread with FIFO frame data/timestamps buffer(s) in between.
            # Implement graceful recovery from failed grab()/retrieve() calls.
            # Estimate amount of dropped frames and implement correspondent counters.
            # Move COpenCVmultiFrameCapThread into the 'common.capture'?
            # Maybe not a good idea because COpenCVmultiFrameCapThread uses parts
            # imported from mendouscopy, such as CMuPaVideoWriter. Decouple frame source
            # from the frame sink?
            # Implement 'settings_and_notes.dat' file generation. Run-time notes/events?
            # TTL I/O, Ext. triggering (BNC connectors on Miniscope's acquisition box).

        if abs(l_FPS[0] - sum(l_FPS) / len(l_FPS)) > 0.1:
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "Unequal frame rate values detected within enabled video sources.\nRecording aborted.")
            self.btn_record.setEnabled(True)
            return

        if self.oc_frame_cap_thread == None:
            raise RuntimeError("Unallocated thread detected!")

        d_rec_info = {}
        d_rec_info['DATA_ROOT_DIR'] = self.s_data_root_dir
        d_rec_info['VSTREAM_LIST'] = l_vstream_list
        self.oc_frame_cap_thread.start_recording(d_rec_info)

    def __cb_on_btn_stop(self):
        self.__interrupt_threads_gracefully()
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win == None: continue
            oc_win.close()
            del oc_win
            self.l_wins[i_idx] = None
        self.l_wins.clear()
        self.btn_preview.setEnabled(True)
        self.oc_vsrc_table.setEnabled(True)
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


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.mupawrite import CMuPaVideoWriter

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
    app.setApplicationName("msCap")

    oc_main_win = CMainWindow(oc_global_cfg)
    oc_main_win.show()
    sys.exit(app.exec_())
#

