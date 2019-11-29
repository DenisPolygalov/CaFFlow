#!/usr/bin/env python3


import sys
import time

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from PyQt5.QtMultimedia import QCamera
from PyQt5.QtMultimediaWidgets import QCameraViewfinder

import cv2 as cv

from .widgets import CLabeledComboBox
from .widgets import CLabeledSpinSlider


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


def status2str(status):
    if status == QCamera.ActiveStatus:
        return "ActiveStatus"
    elif status == QCamera.StartingStatus:
        return "StartingStatus"
    elif status == QCamera.StandbyStatus:
        return "StandbyStatus"
    elif status == QCamera.LoadedStatus:
        return "LoadedStatus"
    elif status == QCamera.LoadingStatus:
        return "LoadingStatus"
    elif status == QCamera.UnloadingStatus:
        return "UnloadingStatus"
    elif status == QCamera.StoppingStatus:
        return "StoppingStatus"
    elif status == QCamera.UnloadedStatus:
        return "UnloadedStatus"
    elif status == QCamera.UnavailableStatus:
        return "UnavailableStatus"
    else:
        return "UNKNOWN STATUS"
#


# These two functions are to be used privately, in this file only,
# e.g. called from within various *CameraPreviewWindow() classes.
def _camera_sync_load_and_start(oc_qcamera):
    cam_status = oc_qcamera.status()
    if cam_status != QCamera.UnloadedStatus:
        raise RuntimeError("ERROR: unexpected camera status: %s" % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.load()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                raise RuntimeError("ERROR: unable to load camera")
    i_sec_cnt = 0
    oc_qcamera.start()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.ActiveStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                raise RuntimeError("ERROR: unable to start camera")
#


def _camera_sync_stop_and_unload(oc_qcamera):
    cam_status = oc_qcamera.status()
    if cam_status != QCamera.ActiveStatus:
        raise RuntimeError("ERROR: unexpected camera status: %s" % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.stop()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                raise RuntimeError("ERROR: unable to stop camera")
    i_sec_cnt = 0
    oc_qcamera.unload()
    while True:
        cam_status = oc_qcamera.status()
        if cam_status == QCamera.UnloadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                raise RuntimeError("ERROR: unable to unload camera")
#


class CQCameraPreviewWindow(QtWidgets.QMainWindow):
    closeSignal = QtCore.pyqtSignal()
    ioctlRequest = QtCore.pyqtSignal(dict)

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
        if self.oc_camera is None:
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
        if self.oc_camera is None:
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
        if self.oc_camera is not None: self.oc_camera.stop()
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        if self.oc_camera is not None:
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
        if self.oc_camera is None:
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
        self.closeSignal.emit()
    #
#

# TODO this is software rendering. Add OpenGL version of this.
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


class COpenCVPreviewWindow(QtWidgets.QMainWindow):
    closeSignal = QtCore.pyqtSignal()
    ioctlRequest = QtCore.pyqtSignal(dict)

    def __init__(self, d_param, b_enable_close_button=False, *args, **kwargs):
        super(COpenCVPreviewWindow, self).__init__(*args, **kwargs)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, b_enable_close_button)

        self.i_camera_idx = -1
        self.oc_camera_info = None
        self.__frame_cap_thread = None
        self.__oc_canvas = None
        self.b_is_master = d_param['is_master']

        # bottom status bar
        self.sbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.sbar)

    def frameReady(self, na_frame):
        if self.windowState() != Qt.WindowMinimized:
            self.update()
    #

    def fatal_error(self, s_msg):
        if self.__frame_cap_thread is not None:
            self.__frame_cap_thread.requestInterruption()
            self.__frame_cap_thread.wait(10000)
        QtWidgets.QMessageBox.critical(None, "Fatal Error", "%s\nThe application will exit now." % s_msg)
        sys.exit(-1)

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        if self.__frame_cap_thread is not None:
            self.fatal_error("Preallocated camera object detected")

        self.i_camera_idx = i_camera_idx
        self.oc_camera_info = oc_camera_info
        self.__frame_cap_thread = oc_frame_cap_thread
        self.__frame_cap_thread.frameReady.connect(self.frameReady, Qt.QueuedConnection)

        self.__oc_canvas = CNdarrayPreviewWidget(self.__frame_cap_thread.get_frame(self.i_camera_idx))
        self.setCentralWidget(self.__oc_canvas)

    def get_cap_prop(self, i_prop_id):
        if self.__frame_cap_thread is None:
            raise ValueError("Unallocated camera object detected")
        return self.__frame_cap_thread.read_prop_sync(self.i_camera_idx, i_prop_id)

    def get_vstream_info(self):
        d_vstream_info = {}
        d_vstream_info['FPS'] = self.get_cap_prop(cv.CAP_PROP_FPS)
        d_vstream_info['FRAME_WIDTH'] = self.get_cap_prop(cv.CAP_PROP_FRAME_WIDTH)
        d_vstream_info['FRAME_HEIGHT'] = self.get_cap_prop(cv.CAP_PROP_FRAME_HEIGHT)
        if self.b_is_master:
            d_vstream_info['IS_MASTER'] = 1
        else:
            d_vstream_info['IS_MASTER'] = 0
        return d_vstream_info

    def update_cap_prop(self, i_prop_id, prop_new_val, b_async_call=False):
        if self.__frame_cap_thread is None:
            raise ValueError("Unallocated camera object detected")

        if self.i_camera_idx < 0:
            raise RuntimeError("Inappropriate method usage. Call start_preview() first.")

        if b_async_call:
            d_ioctl_data = {}
            d_ioctl_data['camera_idx'] = self.i_camera_idx
            d_ioctl_data['prop_id'] = i_prop_id
            d_ioctl_data['prop_new_val'] = prop_new_val
            self.ioctlRequest.emit(d_ioctl_data)
        else:
            prop_old, prop_new = self.__frame_cap_thread.update_prop_sync(self.i_camera_idx, i_prop_id, prop_new_val)
            self.sbar.showMessage("%s -> %s" % (repr(prop_old), repr(prop_new)), 3000)

    def stop_preview(self):
        if self.__frame_cap_thread is None:
            return # this is correct logic, no error here

        self.__frame_cap_thread.frameReady.disconnect(self.frameReady)
        self.__frame_cap_thread = None
        self.oc_camera_info = None
        self.i_camera_idx = -1

    def is_started(self):
        if self.__frame_cap_thread is None:
            return False
        return True

    def is_save_state_needed(self):
        return False

    def save_state(self):
        pass

    def closeEvent(self, event):
        if self.is_save_state_needed():
            self.save_state()
        self.stop_preview()
        self.closeSignal.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F1:
            sys.stdout.write("CAP_PROP_FRAME_WIDTH: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_FRAME_WIDTH)))
            sys.stdout.write("CAP_PROP_FRAME_HEIGHT: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_FRAME_HEIGHT)))
            sys.stdout.write("CAP_PROP_FPS: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_FPS)))
            sys.stdout.write("CAP_PROP_SATURATION: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_SATURATION)))
            sys.stdout.write("CAP_PROP_BRIGHTNESS: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_BRIGHTNESS)))
            sys.stdout.write("CAP_PROP_GAIN: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_GAIN)))
            sys.stdout.write("CAP_PROP_HUE: %s\n" % repr(self.get_cap_prop(cv.CAP_PROP_HUE)))
            sys.stdout.write("\n")
        super(COpenCVPreviewWindow, self).keyPressEvent(event)
    #
#


class CSillyCameraPreviewWindow(COpenCVPreviewWindow):
    def __init__(self, d_param, *args, **kwargs):
        super(CSillyCameraPreviewWindow, self).__init__(d_param, *args, **kwargs)
        self.f_initial_frame_rate = d_param['initial_frame_rate'] # in Hz

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)
        # Get/Set INITIAL camera properties such as FPS and/or frame size here
        # by using self.get_cap_prop(cv.CAP_PROP_FPS) etc.
        f_cam_fps = self.get_cap_prop(cv.CAP_PROP_FPS)
        if abs(f_cam_fps - self.f_initial_frame_rate) > 0.5:
            self.update_cap_prop(cv.CAP_PROP_FPS, self.f_initial_frame_rate)
    #
#


class CSmartCameraPreviewWindow(COpenCVPreviewWindow):
    def __init__(self, d_param, oc_cam_info, *args, **kwargs):
        super(CSmartCameraPreviewWindow, self).__init__(d_param, *args, **kwargs)
        self.f_initial_frame_rate = d_param['initial_frame_rate'] # in Hz
        s_cam_descr = oc_cam_info.description()

        oc_cam = QCamera(oc_cam_info)

        _camera_sync_load_and_start(oc_cam)
        l_resolutions = oc_cam.supportedViewfinderResolutions()
        l_frate_ranges = oc_cam.supportedViewfinderFrameRateRanges()
        _camera_sync_stop_and_unload(oc_cam)

        del oc_cam

        if len(l_frate_ranges) == 0 or len(l_resolutions) == 0:
            raise RuntimeError("The camera (%s) does not support frame rate/resolution information retrieval" % s_cam_descr)

        self.b_startup_guard = False
        self.toolbar = QtWidgets.QToolBar("Preview")

        l_items = []
        for oc_res in l_resolutions:
            l_items.append("%i x %i" % (oc_res.width(), oc_res.height()))
        self.cbox_resolution = CLabeledComboBox("Resolution:")
        self.cbox_resolution.cbox.addItems(l_items)
        self.cbox_resolution.cbox.currentIndexChanged.connect(self.__cb_on_resolution_cbox_index_changed)

        self.toolbar.addWidget(self.cbox_resolution)
        self.toolbar.addSeparator()

        l_items = []
        for oc_frate in l_frate_ranges:
            l_items.append("%f" % oc_frate.minimumFrameRate)
        self.cbox_frame_rate = CLabeledComboBox("Frame Rate:")
        self.cbox_frame_rate.cbox.addItems(l_items)
        self.cbox_frame_rate.cbox.currentIndexChanged.connect(self.__cb_on_frame_rate_cbox_index_changed)

        self.toolbar.addWidget(self.cbox_frame_rate)
        self.toolbar.addSeparator()
        self.addToolBar(self.toolbar)

    def __cb_on_resolution_cbox_index_changed(self, i_idx):
        if not self.is_started(): return
        if self.b_startup_guard: return
        l_res = self.cbox_resolution.cbox.itemText(i_idx).split(" x ")
        i_w, i_h = int(l_res[0]), int(l_res[1])
        self.update_cap_prop(cv.CAP_PROP_FRAME_WIDTH,  i_w, b_async_call=True)
        self.update_cap_prop(cv.CAP_PROP_FRAME_HEIGHT, i_h, b_async_call=True)

    def __cb_on_frame_rate_cbox_index_changed(self, i_idx):
        if not self.is_started(): return
        if self.b_startup_guard: return
        f_cam_fps = float(self.cbox_frame_rate.cbox.itemText(i_idx))
        self.update_cap_prop(cv.CAP_PROP_FPS, f_cam_fps, b_async_call=True)

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)

        self.b_startup_guard = True

        # Get/Set INITIAL camera properties such as FPS and/or frame size here
        # by using self.get_cap_prop(cv.CAP_PROP_FPS) etc.
        f_cam_fps = self.get_cap_prop(cv.CAP_PROP_FPS)
        if abs(f_cam_fps - self.f_initial_frame_rate) > 0.5:
            self.update_cap_prop(cv.CAP_PROP_FPS, self.f_initial_frame_rate)

        i_curr_frate = int(self.get_cap_prop(cv.CAP_PROP_FPS))
        for i_idx in range(self.cbox_frame_rate.cbox.count()):
            if int(float(self.cbox_frame_rate.cbox.itemText(i_idx))) == i_curr_frate:
                self.cbox_frame_rate.cbox.setCurrentIndex(i_idx)

        i_frame_w = int(self.get_cap_prop(cv.CAP_PROP_FRAME_WIDTH))
        i_frame_h = int(self.get_cap_prop(cv.CAP_PROP_FRAME_HEIGHT))
        s_res_hash = "%i x %i" % (i_frame_w, i_frame_h)
        for i_idx in range(self.cbox_resolution.cbox.count()):
            if self.cbox_resolution.cbox.itemText(i_idx) == s_res_hash:
                self.cbox_resolution.cbox.setCurrentIndex(i_idx)

        self.b_startup_guard = False
    #
#


class CMiniScopePreviewWindow(COpenCVPreviewWindow):
    def __init__(self, d_param, *args, **kwargs):
        super(CMiniScopePreviewWindow, self).__init__(d_param, *args, **kwargs)
        self.f_initial_frame_rate = d_param['initial_frame_rate'] # in Hz

        self._DEVICE_ID = 0x12
        self._RECORD_START = 0x01
        self._RECORD_END = 0x02
        self._TRIG_RECORD_EXT = 0x02
        self._SET_CMOS_SETTINGS = 0x03
        self.t_frate_names = ("5 Hz", "10 Hz", "15 Hz", "20 Hz", "30 Hz", "60 Hz")
        self.t_frate_values = (0x11, 0x12, 0x13, 0x14, 0x15, 0x16)
        self.t_frate_val_Hz = (5, 10, 15, 20, 30, 60)
        self._INIT_EXPOSURE = 255
        self._INIT_GAIN = 16
        self._INIT_EXCITATION = 0

        b_is_FPS_supported = False
        for i_init_frate_idx, i_FPS in enumerate(self.t_frate_val_Hz):
            if i_FPS == int(self.f_initial_frame_rate):
                self.i_init_frate_idx = i_init_frate_idx
                b_is_FPS_supported = True
                break
        if not b_is_FPS_supported:
            raise RuntimeError("Requested frame rate value (%s) is not supported by Miniscope hardware" % repr(self.f_initial_frame_rate))

        self.b_emulation_mode = d_param['emulation_mode']
        if self.b_emulation_mode:
            self.setWindowTitle("Miniscope (EMULATION)")
        else:
            self.setWindowTitle("Miniscope")

        self.toolbar = QtWidgets.QToolBar("Preview")

        self.cbox_frame_rate = CLabeledComboBox("Frame Rate:")
        self.cbox_frame_rate.cbox.addItems(self.t_frate_names)
        self.cbox_frame_rate.cbox.setCurrentIndex(self.i_init_frate_idx)
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
        self.cbox_frame_rate.cbox.setCurrentIndex(self.i_init_frate_idx)
        self.sld_exposure.slider.setSliderPosition(self._INIT_EXPOSURE)
        self.sld_gain.slider.setSliderPosition(self._INIT_GAIN)
        self.sld_excitation.slider.setSliderPosition(self._INIT_EXCITATION)
        # TODO add here (re)initialization code for other GUI elements
        # WARNING: DO NOT call self.update_cap_prop() here. Such calls must be
        # implemented in the correspondent event handlers (i.e. self.__cb_on_*)

    def __cb_on_frame_rate_cbox_index_changed(self, event):
        if not self.is_started(): return
        self.update_cap_prop(cv.CAP_PROP_SATURATION, self.t_frate_values[self.cbox_frame_rate.cbox.currentIndex()])

    def __cb_on_exposure_changed(self, i_new_value):
        if not self.is_started(): return
        self.update_cap_prop(cv.CAP_PROP_BRIGHTNESS, i_new_value)

    def __cb_on_gain_changed(self, i_new_value):
        if not self.is_started(): return
        # Gains between 32 and 64 must be even for MT9V032
        if i_new_value >= 32 and (i_new_value % 2 == 1):
            self.update_cap_prop(cv.CAP_PROP_GAIN, i_new_value + 1)
        else:
            self.update_cap_prop(cv.CAP_PROP_GAIN, i_new_value)

    def __cb_on_excitation_changed(self, i_new_value):
        if not self.is_started(): return
        i_val = int(i_new_value*(0x0FFF)/100)|0x3000
        self.update_cap_prop(cv.CAP_PROP_HUE, (i_val>>4) & 0x00FF)

    def __reset_HW(self):
        # reset CMOS
        self.update_cap_prop(cv.CAP_PROP_SATURATION, self._SET_CMOS_SETTINGS)
        # reset excitation (HUE)
        i_val = int(self._INIT_EXCITATION*(0x0FFF)/100)|0x3000
        self.update_cap_prop(cv.CAP_PROP_HUE, (i_val>>4) & 0x00FF)
        # reset the gain
        if self._INIT_GAIN >= 32 and (self._INIT_GAIN % 2 == 1):
            self.update_cap_prop(cv.CAP_PROP_GAIN, self._INIT_GAIN + 1)
        else:
            self.update_cap_prop(cv.CAP_PROP_GAIN, self._INIT_GAIN)
        # reset exposure (BRIGHTNESS)
        self.update_cap_prop(cv.CAP_PROP_BRIGHTNESS, self._INIT_EXPOSURE)
        # reset frame rate (SATURATION)
        self.update_cap_prop(cv.CAP_PROP_SATURATION, self.t_frate_values[self.i_init_frate_idx])

    def get_vstream_info(self):
        d_vstream_info = super().get_vstream_info()
        d_vstream_info['FPS'] = self.t_frate_val_Hz[self.cbox_frame_rate.cbox.currentIndex()]
        return d_vstream_info

    def start_preview(self, i_camera_idx, oc_camera_info, oc_frame_cap_thread):
        super().start_preview(i_camera_idx, oc_camera_info, oc_frame_cap_thread)
        self.__reset_UI()
        self.__reset_HW()

        # Seems like Miniscope need the initial FPS to be set too,
        # in a way not consistent with it's further changes!
        f_cam_fps = self.get_cap_prop(cv.CAP_PROP_FPS)
        if abs(f_cam_fps - self.f_initial_frame_rate) > 0.5:
            self.update_cap_prop(cv.CAP_PROP_FPS, self.f_initial_frame_rate)

    def stop_preview(self):
        # reset excitation LED power (HUE) to zero
        if self.is_started():
            self.update_cap_prop(cv.CAP_PROP_HUE, 0)
        super().stop_preview()
    #
#

