#!/usr/bin/env python3


import os
import sys
import configparser

# import PyQt5 # hint for pyinstaller
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtMultimedia import QCameraInfo

from common.widgets import CTableItemDelegate
from common.preview import CSillyCameraPreviewWindow
from common.preview import CSmartCameraPreviewWindow
from common.preview import CMiniScopePreviewWindow
from common.capture import COpenCVmultiFrameCapThread


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
        if len(self.l_caminfos) == 1:
            item2 = QtWidgets.QTableWidgetItem("ENABLED")
        else:
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

        if len(self.l_caminfos) == 1:
            item3.setCheckState(QtCore.Qt.Checked)

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

        if self.oc_frame_cap_thread is not None:
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

        if not any(item is True for item in l_do_capture):
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

        self.oc_frame_writer = CMuStreamVideoWriter(l_do_capture)
        self.oc_frame_cap_thread = COpenCVmultiFrameCapThread(l_do_capture, self.l_wins, self.oc_frame_writer)
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win is None: continue
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
            if oc_win is None:
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
            # Note that implementing on-the-fly frame SIZE change require storage container (na_frame) reallocation!
            # Implement COpenCVmultiFrameCapThread.__cb_on_ioctl_requested() method
            # Implement COpenCVframeCaptureThread.__cb_on_ioctl_requested() method
            # Also, it might be necessary to call CMuStreamVideoWriter.write_next_frame()
            # in a separated thread with FIFO frame data/timestamps buffer(s) in between.
            # Implement graceful recovery from failed grab()/retrieve() calls.
            # Estimate amount of dropped frames and implement correspondent counters.
            # Switching from 'Recording' state to 'Preview' state is not supported.
            # maybe add this later. Use start_new_session() method?
            # Implement 'settings_and_notes.dat' file generation. Run-time notes/events?
            # Implement storage of video source parameters such as excitation, gain etc.
            # upon clicking the "REC" button. Pass this information down to recorder sink.
            # TTL I/O, Ext. triggering (BNC connectors on Miniscope's acquisition box).
            # Setting excitation LED power (cv.CAP_PROP_HUE) to zero in stop_preview()
            # does not work in msCap.py but does work in msView.py. Low level .get()
            # method is being called in both cases. Hardware bug?

        if abs(l_FPS[0] - sum(l_FPS) / len(l_FPS)) > 0.1:
            QtWidgets.QMessageBox.warning(None, "Sanity check failed", \
                "Unequal frame rate values detected within enabled video sources.\nRecording aborted.")
            self.btn_record.setEnabled(True)
            return

        if self.oc_frame_cap_thread is None:
            raise RuntimeError("Unallocated thread detected!")

        d_rec_info = {}
        d_rec_info['DATA_ROOT_DIR'] = self.s_data_root_dir
        d_rec_info['VSTREAM_LIST'] = l_vstream_list
        self.oc_frame_writer.start_recording(d_rec_info)
        self.oc_frame_cap_thread.start_recording(d_rec_info)

    def __cb_on_btn_stop(self):
        self.__interrupt_threads_gracefully()
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win is None: continue
            oc_win.close()
            del oc_win
            self.l_wins[i_idx] = None
        self.l_wins.clear()
        self.btn_preview.setEnabled(True)
        self.oc_vsrc_table.setEnabled(True)
        self.btn_record.setEnabled(False)
        self.btn_stop.setEnabled(False)

    def __interrupt_threads_gracefully(self):
        if self.oc_frame_cap_thread is not None:
            self.oc_frame_cap_thread.requestInterruption()
            self.oc_frame_cap_thread.wait(10000)
            del self.oc_frame_cap_thread
            self.oc_frame_cap_thread = None
            self.oc_frame_writer.close()

    def fatal_error(self, s_msg):
        self.__interrupt_threads_gracefully()
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def closeEvent(self, event):
        self.__interrupt_threads_gracefully()
        for i_idx, oc_win in enumerate(self.l_wins):
            if oc_win is None: continue
            oc_win.close()
            del oc_win
            self.l_wins[i_idx] = None
        self.l_wins.clear()
    #
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.mupawrite import CMuStreamVideoWriter

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

