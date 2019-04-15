#!/usr/bin/env python3


import os
import sys
import json
import time
import pprint

import PyQt5 # hint for pyinstaller
from PyQt5.QtWidgets import QApplication
from PyQt5.QtMultimedia import QCameraInfo, QCamera


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

# TODO FIXME change output format to json instead of print()-ing each line

def captureMode2str(mode):
    if mode == QCamera.CaptureStillImage:
        return "CaptureStillImage"
    elif mode == QCamera.CaptureViewfinder:
        return "CaptureViewfinder"
    elif mode == QCamera.CaptureVideo:
        return "CaptureVideo"
    else:
        return "UNKNOWN CAPTURE MODE"
#


def lockStatus2str(status):
    if status == QCamera.Unlocked:
        return "Unlocked"
    elif status == QCamera.Searching:
        return "Searching"
    elif status == QCamera.Locked:
        return "Locked"
    else:
        return "UNKNOWN LOCK STATUS"
#


def state2str(state):
    if state == QCamera.UnloadedState:
        return "UnloadedState"
    elif state == QCamera.LoadedState:
        return "LoadedState"
    elif state == QCamera.ActiveState:
        return "ActiveState"
    else:
        return "UNKNOWN STATE"
#


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


def lockType2str(status):
    # FIXME TODO not sure this way is the correct one
    l_locks = []
    if (status == QCamera.NoLock):
        l_locks.append("NoLock")
    if (status == QCamera.LockExposure):
        l_locks.append("LockExposure")
    if (status == QCamera.LockWhiteBalance):
        l_locks.append("LockWhiteBalance")
    if (status == QCamera.LockFocus):
        l_locks.append("LockFocus")
    return ",".join(l_locks)
#


def frameRateRange2str(l_frate_ranges):
    l_out = []
    for oc_range in l_frate_ranges:
        l_out.append("%.1f - %.1f" % (oc_range.minimumFrameRate, oc_range.maximumFrameRate))
    return ", ".join(l_out)
#


def frameResolution2str(l_resolutions):
    l_out = []
    for oc_res in l_resolutions:
        l_out.append("(%i, %i)" % (oc_res.width(), oc_res.height()))
    return "\n\t\t".join(l_out)
#


def camera_sync_load_and_start(oc_qcamera):
    cam_status = oc_qcamera.status()
    if cam_status != QCamera.UnloadedStatus:
        print("ERROR: unexpected camera status: %s" % status2str(cam_status))
        sys.exit(-1)
    # print("INFO: attempting to LOAD camera from %s..." % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.load()
    while True:
        cam_status = oc_qcamera.status()
        # print("INFO: current status: %s" % status2str(cam_status))
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to load camera")
                sys.exit(-1)
    # print("INFO: attempting to START camera from %s..." % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.start()
    while True:
        cam_status = oc_qcamera.status()
        # print("INFO: current status: %s" % status2str(cam_status))
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
    # print("INFO: attempting to STOP camera from %s..." % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.stop()
    while True:
        cam_status = oc_qcamera.status()
        # print("INFO: current status: %s" % status2str(cam_status))
        if cam_status == QCamera.LoadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to stop camera")
                sys.exit(-1)
    # print("INFO: attempting to (UN)load camera from %s..." % status2str(cam_status))
    i_sec_cnt = 0
    oc_qcamera.unload()
    while True:
        cam_status = oc_qcamera.status()
        # print("INFO: current status: %s" % status2str(cam_status))
        if cam_status == QCamera.UnloadedStatus: break
        else:
            time.sleep(1)
            i_sec_cnt += 1
            if i_sec_cnt >= 10:
                print("ERROR: unable to unload camera")
                sys.exit(-1)
#


def main():
    app = QApplication(sys.argv) # must be called in order to be able to use all the stuff below(!)
    l_cameras = QCameraInfo.availableCameras()
    if len(l_cameras) == 0:
        print("ERROR: no cameras found")
        sys.exit(-1)
    else:
        print("INFO: found %i camera(s)" % len(l_cameras))
        print()

    for i_idx, oc_caminfo in enumerate(l_cameras):
        # QCameraInfo - derived properties
        print("Camera #%i:" % i_idx)
        print("\t deviceName: %s" % oc_caminfo.deviceName())
        print("\t description: %s" % oc_caminfo.description())
        print("\t isNull: %s" % oc_caminfo.isNull())
        print("\t orientation: %s" % oc_caminfo.orientation())
        print("\t position: %s" % oc_caminfo.position())

        # QCamera - derived properties
        oc_camera = QCamera(i_idx)
        camera_sync_load_and_start(oc_camera)

        oc_camera_exposure = oc_camera.exposure()
        print("\t captureMode: %s" % captureMode2str(oc_camera.captureMode()))
        print("\t exposure:")
        print("\t\t isAvailabe: %s" % oc_camera_exposure.isAvailable())
        if oc_camera_exposure.isAvailable():
            print("\t\t aperture: %s" % oc_camera_exposure.aperture())
            # TODO test this, add more entries

        oc_camera_focus = oc_camera.focus()
        print("\t focus:")
        print("\t\t isAvailabe: %s" % oc_camera_focus.isAvailable())
        if oc_camera_focus.isAvailable():
            print("\t\t aperture: %f" % oc_camera_focus.digitalZoom())
            # TODO test this, add more entries

        oc_cam_img_proc = oc_camera.imageProcessing()
        print("\t imageProcessing:")
        print("\t\t isAvailabe: %s" % oc_cam_img_proc.isAvailable())
        if oc_cam_img_proc.isAvailable():
            print("\t\t brightness: %f" % oc_cam_img_proc.brightness())
            print("\t\t contrast: %f" % oc_cam_img_proc.contrast())
            print("\t\t denoisingLevel: %f" % oc_cam_img_proc.denoisingLevel())
            print("\t\t manualWhiteBalance: %f" % oc_cam_img_proc.manualWhiteBalance())
            print("\t\t saturation: %f" % oc_cam_img_proc.saturation())
            print("\t\t sharpeningLevel: %f" % oc_cam_img_proc.sharpeningLevel())

        print("\t isVideoCaptureSupported: %s" % oc_camera.isCaptureModeSupported(QCamera.CaptureVideo))
        print("\t lockStatus: %s" % lockStatus2str(oc_camera.lockStatus()))
        print("\t requestedLocks: %s" % lockType2str(oc_camera.requestedLocks()))
        print("\t state: %s" % state2str(oc_camera.state()))
        print("\t status: %s" % status2str(oc_camera.status()))
        print("\t supportedLocks: %s" % lockType2str(oc_camera.supportedLocks()))
        print("\t supportedViewfinderFrameRateRanges: %s" % frameRateRange2str(oc_camera.supportedViewfinderFrameRateRanges()))
        print("\t supportedViewfinderPixelFormats: %s" % repr(oc_camera.supportedViewfinderPixelFormats()))
        print("\t supportedViewfinderResolutions: \n\t\t%s" % frameResolution2str(oc_camera.supportedViewfinderResolutions()))
        print("\t len(supportedViewfinderSettings): %s" % len(oc_camera.supportedViewfinderSettings()))

        # QCameraViewfinderSettings - derived properties
        oc_vf_settings = oc_camera.viewfinderSettings()
        if oc_vf_settings.isNull():
            print("\t viewfinderSettings: not supported")
            camera_sync_stop_and_unload(oc_camera)
            print()
            continue
        print("\t maximumFrameRate: %f" % oc_vf_settings.maximumFrameRate())
        print("\t minimumFrameRate: %f" % oc_vf_settings.minimumFrameRate())
        print("\t resolution: %s" % frameResolution2str([oc_vf_settings.resolution()]))
        # TODO the rest of methods...
        camera_sync_stop_and_unload(oc_camera)
        print()
    #
#


if __name__ == '__main__':
    s_qt_plugin_path = os.path.join(os.getcwd(), 'PyQt5', 'Qt', 'plugins')
    if os.path.isdir(s_qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = s_qt_plugin_path
        print("INFO: QT_PLUGIN_PATH is set to ", os.environ['QT_PLUGIN_PATH'])
    else:
        print("INFO: QT_PLUGIN_PATH was not altered")
    main()
    os.system("PAUSE")
#

