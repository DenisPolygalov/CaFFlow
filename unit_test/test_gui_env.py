#!/usr/bin/env python3


import unittest


class CTestImportPackages(unittest.TestCase):
    def test_import(self):
        self.assertTrue(self.is_import_OK())

    def is_import_OK(self):
        try: import numpy
        except ImportError:
            print("\nERROR: NumPy package is missing. Please install it.")
            return False

        try: import cv2
        except ImportError:
            print("\nERROR: OpenCV package is missing. Please install it.")
            return False

        try: import PyQt5
        except ImportError:
            print("\nERROR: PyQt5 package is missing. Please install it.")
            return False

        try: from PyQt5.QtMultimedia import QCameraInfo, QCamera
        except ImportError:
            print("\nERROR: PyQt5 package is installed, but missing QtMultimedia support")
            return False

        return True
    #
#

if __name__ == '__main__':
    unittest.main()
#
