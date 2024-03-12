#!/usr/bin/env pyhton3


import os
import sys


class CTestOpenCVBackends(unittest.TestCase):
    def test_opencv_videoio_info(self):
        print()
        print('Installed OpenCV version:', cv.__version__)
        if cv.__version__.startswith('3'):
            print('This script can only work with OpenCV version >= 4.x')
            return
        print()

        l_backends = cv.videoio_registry.getBackends()
        for i_backend_id in l_backends:
            s_name = cv.videoio_registry.getBackendName(i_backend_id)
            print('OpenCV BackEnd: name=%s id=%i' % (s_name, i_backend_id))
        print()

        l_camera_backends = cv.videoio_registry.getCameraBackends()
        for i_backend_id in l_camera_backends:
            s_name = cv.videoio_registry.getBackendName(i_backend_id)
            b_isBuiltIn = cv.videoio_registry.isBackendBuiltIn(i_backend_id)
            print('OpenCV camera BackEnd: name=%s id=%i isBuiltIn=%s' % (s_name, i_backend_id, str(b_isBuiltIn)))
        print()

        l_stream_backends = cv.videoio_registry.getStreamBackends()
        for i_backend_id in l_stream_backends:
            s_name = cv.videoio_registry.getBackendName(i_backend_id)
            b_isBuiltIn = cv.videoio_registry.isBackendBuiltIn(i_backend_id)
            print('OpenCV stream BackEnd: name=%s id=%i isBuiltIn=%s' % (s_name, i_backend_id, str(b_isBuiltIn)))
        print()

        l_writer_backends = cv.videoio_registry.getWriterBackends()
        for i_backend_id in l_writer_backends:
            s_name = cv.videoio_registry.getBackendName(i_backend_id)
            b_isBuiltIn = cv.videoio_registry.isBackendBuiltIn(i_backend_id)
            print('OpenCV writer BackEnd: name=%s id=%i isBuiltIn=%s' % (s_name, i_backend_id, str(b_isBuiltIn)))
        print()

    def test_video_capture(self, index=0, apiPreference=cv.CAP_MSMF):
        # hint: default value is cv.CAP_ANY
        cap = cv.VideoCapture(index, apiPreference=apiPreference)
    #
#

if __name__ == '__main__':
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
    # Related environment variables:
    # change backend priority: OPENCV_VIDEOIO_PRIORITY_<backend>=9999
    # disable backend: OPENCV_VIDEOIO_PRIORITY_<backend>=0
    # specify list of backends with high priority (>100000):
    # OPENCV_VIDEOIO_PRIORITY_LIST=FFMPEG,GSTREAMER
    import cv2 as cv
    unittest.main()
#
