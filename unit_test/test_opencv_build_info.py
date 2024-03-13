#!/usr/bin/env pyhton3


import os
import unittest


class CTestOpenCVBuildInfo(unittest.TestCase):
    def test_opencv_buildinfo(self):
        self.assertTrue(self.print_opencv_build_info())

    def print_opencv_build_info(self):
        try:
            import cv2 as cv
            print(cv.getBuildInformation())
            return True
        except:
            return False
#

if __name__ == '__main__':
    os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
    unittest.main()
#
