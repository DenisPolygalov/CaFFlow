#!/usr/bin/env pyhton3


import os
import unittest


class CTestOpenCVVideoCapture(unittest.TestCase):
    def test_video_capture(self):
        self.assertTrue(self.get_default_video_capture_device())

    def get_default_video_capture_device(self):
        try:
            import cv2 as cv
        except ImportError:
            return False
        print('OpenCV Version:', cv.__version__)
        if cv.__version__.startswith('3'):
            print('This script can only work with OpenCV version >= 4.x')
            return False
        print()
        cap = None
        # hint: use apiPreference=cv.CAP_MSMF on Windows
        cap = cv.VideoCapture(0, apiPreference=cv.CAP_ANY)
        if cap == None:
            return False
        return cap.isOpened()
    #
#

if __name__ == '__main__':
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
    unittest.main()
#
