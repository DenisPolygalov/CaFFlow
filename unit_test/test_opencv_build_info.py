#!/usr/bin/env pyhton3


import os
import unittest


class CTestOpenCVBuildInfo(unittest.TestCase):
    def test_opencv_buildinfo(self):
        print(cv.getBuildInformation())
    #
#

if __name__ == '__main__':
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
    import cv2 as cv
    unittest.main()
#
