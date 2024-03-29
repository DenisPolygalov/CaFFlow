#!/usr/bin/env python3


import time

from PyQt5 import QtCore
from PyQt5.QtCore import Qt

import cv2 as cv
import numpy as np


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


class COpenCVframeCaptureThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, d_param, h_win, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.i_camera_idx = d_param['camera_index']
        self.b_running = False
        if cv.__version__.startswith('3'):
            self.oc_camera = cv.VideoCapture(self.i_camera_idx + cv.CAP_DSHOW)
        else:
            self.oc_camera = cv.VideoCapture(self.i_camera_idx, apiPreference=cv.CAP_MSMF)
        self.i_frame_id = -1 # so valid frame numbers will start from zero
        self.i_frame_drop_cnt = 0
        self.MAX_FRAME_DROPS = 100
        self.FRAME_READ_DELAY_uS = 100000
        print("DEBUG: COpenCVframeCaptureThread(): cam_idx=%i" % self.i_camera_idx)

        i_frame_w = int(self.oc_camera.get(cv.CAP_PROP_FRAME_WIDTH))
        i_frame_h = int(self.oc_camera.get(cv.CAP_PROP_FRAME_HEIGHT))
        print("DEBUG: COpenCVframeCaptureThread(): current frame size: %i x %i" % (i_frame_w, i_frame_h))

        if d_param['is_smart']:
            if d_param['initial_frame_width']  != i_frame_w or d_param['initial_frame_height'] != i_frame_h:
                print("DEBUG: COpenCVframeCaptureThread(): frame size mismatch! Trying to switch...")
                self.oc_camera.set(cv.CAP_PROP_FRAME_WIDTH, d_param['initial_frame_width'])
                self.oc_camera.set(cv.CAP_PROP_FRAME_HEIGHT, d_param['initial_frame_height'])

        b_status, self.na_frame = self.oc_camera.read()
        if not b_status:
            raise RuntimeError("Unable to read first frame")

        if self.na_frame.ndim != 3 or self.na_frame.shape[2] != 3:
            raise RuntimeError("Unexpected frame shape: %s" % repr(self.na_frame.shape))

        self.i_frame_h = self.na_frame.shape[0]
        self.i_frame_w = self.na_frame.shape[1]
        self.i_ncolor_channels = self.na_frame.shape[2]
        h_win.ioctlRequest.connect(self.__cb_on_ioctl_requested, Qt.QueuedConnection)

    def run(self):
        print("DEBUG: COpenCVframeCaptureThread: THREAD STARTED!")
        self.b_running = True
        while self.b_running:
            if self.isInterruptionRequested():
                self.b_running = False
                break
            b_status, tmp_image = self.oc_camera.read()
            if not b_status:
                self.i_frame_drop_cnt += 1
                print("DEBUG: frame read() failed: %i time(s)" % self.i_frame_drop_cnt)
                self.usleep(self.FRAME_READ_DELAY_uS)
                if self.i_frame_drop_cnt >= self.MAX_FRAME_DROPS:
                    raise RuntimeError("Unable to read next frame")
                continue
            self.na_frame[...] = tmp_image[...]
            self.i_frame_id += 1
            self.frameReady.emit(self.na_frame)
        print("DEBUG: COpenCVframeCaptureThread: THREAD STOPPED!")
        self.oc_camera.release()
        del self.oc_camera
        self.oc_camera = None

    def __cb_on_ioctl_requested(self, d_ioctl_data):
        print("DEBUG: COpenCVframeCaptureThread->ioctl_requested():", d_ioctl_data)
        self.oc_camera.set(d_ioctl_data['prop_id'], d_ioctl_data['prop_new_val'])

    def read_prop_sync(self, i_cam_id, i_prop_id):
        return self.oc_camera.get(i_prop_id)

    def update_prop_sync(self, i_cam_id, i_prop_id, prop_new_val):
        print("DEBUG: COpenCVframeCaptureThread.update_prop_sync():", i_cam_id, i_prop_id, prop_new_val)
        prop_old = self.oc_camera.get(i_prop_id)
        self.oc_camera.set(i_prop_id, prop_new_val)
        prop_new = self.oc_camera.get(i_prop_id)
        return (prop_old, prop_new)

    def get_frame(self, i_cam_id):
        return self.na_frame
    #
#


class COpenCVmultiFrameCapThread(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(str)

    def __init__(self, l_do_capture, l_wins, l_cap_params, oc_sink_list, *args, **kwargs):
        QtCore.QThread.__init__(self, *args, **kwargs)
        self.t_do_capture = tuple(l_do_capture) # freeze it to prevent changes from outside
        self.b_running = False
        self.b_recording = False
        self.l_cams = []
        self.l_frames = []
        self.l_frame_hwc = [] # list of len() == 3 tuples of frame HEIGHT x WIDTH x COLORS
        self.i_frame_id = -1 # so valid frame numbers will start from zero
        self.oc_sink_list = oc_sink_list
        self.l_ts = []
        self.i_grab_fail_cnt = 0
        self.i_retr_fail_cnt = 0
        self.l_grab_status = []
        self.l_retr_status = []
        self.MAX_FRAME_DROPS = 100
        self.FRAME_READ_DELAY_uS = 100000
        self.t_vstream_list = tuple()

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                print("DEBUG: COpenCVmultiFrameCapThread(): cam_idx=%i" % i_cam_idx)
                if cv.__version__.startswith('3'):
                    self.l_cams.append(cv.VideoCapture(i_cam_idx + cv.CAP_DSHOW))
                else:
                    self.l_cams.append(cv.VideoCapture(i_cam_idx, apiPreference=cv.CAP_MSMF))
            else:
                print("DEBUG: COpenCVmultiFrameCapThread(): cam_idx=%i [SKIP]" % i_cam_idx)
                self.l_cams.append(None) # *** WATCH OUT ***

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if not b_do_cap: continue
            d_param = l_cap_params[i_cam_idx]
            if not d_param['is_smart']: continue
            print("DEBUG: COpenCVmultiFrameCapThread(): cam_idx=%i declared to be smart" % i_cam_idx)

            i_frame_w = int(self.l_cams[i_cam_idx].get(cv.CAP_PROP_FRAME_WIDTH))
            i_frame_h = int(self.l_cams[i_cam_idx].get(cv.CAP_PROP_FRAME_HEIGHT))
            print("DEBUG: COpenCVmultiFrameCapThread(): cam_idx=%i current frame size: %i x %i" % (i_cam_idx, i_frame_w, i_frame_h))

            if d_param['initial_frame_width']  != i_frame_w or d_param['initial_frame_height'] != i_frame_h:
                print("DEBUG: COpenCVframeCaptureThread(): frame size mismatch! Trying to switch...")
                self.l_cams[i_cam_idx].set(cv.CAP_PROP_FRAME_WIDTH, d_param['initial_frame_width'])
                self.l_cams[i_cam_idx].set(cv.CAP_PROP_FRAME_HEIGHT, d_param['initial_frame_height'])
                time.sleep(2)

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                b_status, na_frame = self.l_cams[i_cam_idx].read()

                if not b_status:
                    raise RuntimeError("Unable to read first frame from camera number %i" % i_cam_idx)
                if na_frame.ndim != 3 or na_frame.shape[2] != 3:
                    raise RuntimeError("Unexpected frame shape: %s from camera number %i" % (repr(na_frame.shape), i_cam_idx))

                self.l_frames.append(na_frame.copy())
                self.l_frame_hwc.append((na_frame.shape[0], na_frame.shape[1], na_frame.shape[2]))
                self.l_ts.append(time.time_ns()//1000)
                self.l_grab_status.append(b_status)
                self.l_retr_status.append(b_status)

            else:
                self.l_frames.append(None) # *** WATCH OUT ***
                self.l_frame_hwc.append((None, None, None)) # *** WATCH OUT ***
                self.l_ts.append(None) # *** WATCH OUT ***
                self.l_grab_status.append(None) # *** WATCH OUT ***
                self.l_retr_status.append(None) # *** WATCH OUT ***

        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                l_wins[i_cam_idx].ioctlRequest.connect(self.__cb_on_ioctl_requested, Qt.QueuedConnection)

    def run(self):
        print("DEBUG: COpenCVmultiFrameCapThread: THREAD STARTED!")
        self.b_running = True
        while self.b_running:
            if self.isInterruptionRequested():
                self.b_recording = False
                self.b_running = False
                break

            # grab new frame from each capture-enabled camera
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap:
                    self.l_grab_status[i_cam_idx] = self.l_cams[i_cam_idx].grab()

            # retrieve and decode frame from each capture-enabled camera
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap:
                    self.l_retr_status[i_cam_idx], tmp_image = self.l_cams[i_cam_idx].retrieve()
                    if self.l_retr_status[i_cam_idx]:
                        self.l_ts[i_cam_idx] = time.time_ns()//1000
                        self.l_frames[i_cam_idx][...] = tmp_image[...]

            # check for grab() and/or retrieve() failures
            b_do_sleep = False
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap:
                    if not self.l_grab_status[i_cam_idx]:
                        self.i_grab_fail_cnt += 1
                        print("DEBUG: frame grab() failed: %i time(s) for camera number %i" % (self.i_grab_fail_cnt, i_cam_idx))
                        b_do_sleep = True
                    if not self.l_retr_status[i_cam_idx]:
                        self.i_retr_fail_cnt += 1
                        print("DEBUG: frame retrieve() failed: %i time(s) for camera number %i" % (self.i_retr_fail_cnt, i_cam_idx))
                        b_do_sleep = True

            if b_do_sleep:
                print("DEBUG: sleeping for %i usec zzZ..." % self.FRAME_READ_DELAY_uS)
                self.usleep(self.FRAME_READ_DELAY_uS)
                if self.i_grab_fail_cnt >= self.MAX_FRAME_DROPS or \
                   self.i_retr_fail_cnt >= self.MAX_FRAME_DROPS:
                    raise RuntimeError("Unable to get next frame from camera number %i" % i_cam_idx)
                continue

            if self.i_grab_fail_cnt > 0 or self.i_retr_fail_cnt > 0 and not b_do_sleep:
                print("DEBUG: frame capture recovered. Reset grab/retrieve counters!")
                self.i_grab_fail_cnt = 0
                self.i_retr_fail_cnt = 0

            # push acquired frames into a sink(s) (not necessary files)
            for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
                if b_do_cap and self.b_recording:
                    self.oc_sink_list.write_next_frame(i_cam_idx, self.l_frames[i_cam_idx])
                    self.oc_sink_list.write_time_stamp(i_cam_idx, self.l_ts[i_cam_idx])

            self.i_frame_id += 1
            self.frameReady.emit('frameReady') # argument doesn't matter

        print("DEBUG: COpenCVmultiFrameCapThread: THREAD STOPPED!")
        for i_idx, d_vstream_info in enumerate(self.t_vstream_list):
            if d_vstream_info is not None and d_vstream_info['DESCRIPTION'] == 'MINISCOPE':
                print("DEBUG: COpenCVmultiFrameCapThread.run(): cam_idx=%i" % i_idx)
                self.update_prop_sync(i_idx, cv.CAP_PROP_SATURATION, 0x02) # RECORD_END command

        # Both - 'Preview' and 'Recording' states are done here.
        # All preview windows will be destroyed and all video writers must be
        # closed right after an instance of this class is done it's work.
        for i_cam_idx, b_do_cap in enumerate(self.t_do_capture):
            if b_do_cap:
                print("DEBUG: COpenCVmultiFrameCapThread -> release() cam_idx=%i" % i_cam_idx)
                self.l_cams[i_cam_idx].release()
            else:
                print("DEBUG: COpenCVmultiFrameCapThread -> release() cam_idx=%i [SKIP]" % i_cam_idx)

    def __cb_on_ioctl_requested(self, d_ioctl_data):
        print("DEBUG: COpenCVmultiFrameCapThread->ioctl_requested():", d_ioctl_data)
        self.l_cams[d_ioctl_data['camera_idx']].set(d_ioctl_data['prop_id'], d_ioctl_data['prop_new_val'])

    def __check_cam_or_die(self, i_cam_id):
        if i_cam_id < 0 or i_cam_id >= len(self.l_cams):
            raise ValueError("Unknown camera index: %i" % i_cam_id)
        if not self.t_do_capture[i_cam_id]:
            raise ValueError("Capture mode for camera number %i is not enabled" % i_cam_id)

    def read_prop_sync(self, i_cam_id, i_prop_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_cams[i_cam_id].get(i_prop_id)

    def update_prop_sync(self, i_cam_id, i_prop_id, prop_new_val):
        print("DEBUG: COpenCVmultiFrameCapThread.update_prop_sync():", i_cam_id, i_prop_id, prop_new_val)
        self.__check_cam_or_die(i_cam_id)
        prop_old = self.l_cams[i_cam_id].get(i_prop_id)
        self.l_cams[i_cam_id].set(i_prop_id, prop_new_val)
        prop_new = self.l_cams[i_cam_id].get(i_prop_id)
        return (prop_old, prop_new)

    def get_frame(self, i_cam_id):
        self.__check_cam_or_die(i_cam_id)
        return self.l_frames[i_cam_id]

    def start_recording(self, d_rec_info):
        # s_data_root_dir = d_rec_info['DATA_ROOT_DIR']
        l_vstream_list  = d_rec_info['VSTREAM_LIST']
        if len(l_vstream_list) != len(self.l_cams):
            raise RuntimeError("Sanity check failed. This should never happen.")

        self.t_vstream_list = tuple(l_vstream_list)

        i_idx_master = -1
        for i_idx, d_vstream_info in enumerate(self.t_vstream_list):
            if d_vstream_info is not None and d_vstream_info['IS_MASTER'] == 1:
                i_idx_master = i_idx
                break
        if i_idx_master == -1:
            raise RuntimeError("Sanity check failed. This should never happen.")

        for i_idx, d_vstream_info in enumerate(self.t_vstream_list):
            if d_vstream_info is not None and d_vstream_info['DESCRIPTION'] == 'MINISCOPE':
                print("DEBUG: COpenCVmultiFrameCapThread.start_recording(): cam_idx=%i" % i_idx)
                self.update_prop_sync(i_idx, cv.CAP_PROP_SATURATION, 0x01) # RECORD_START command

        self.b_recording = True
    #
#
