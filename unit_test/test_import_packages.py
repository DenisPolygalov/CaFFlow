#!/usr/bin/env python3

import unittest

class CTestImportPackages(unittest.TestCase):
    def test_import(self):
        self.assertTrue(self.is_import_OK())
    #
    def is_import_OK(self):
        try: import numpy
        except ImportError:
            print("\nThe NumPy package is missing. Please install it.")
            return False
        #
        try: import scipy
        except ImportError:
            print("\nThe SciPy package is missing. Please install it.")
            return False
        #
        try: import cv2
        except ImportError:
            print("\nERROR: The OpenCV package is missing. Please install it.")
            return False
        #
        try: import pandas
        except ImportError:
            print("\nERROR: The Pandas package is missing. Please install it.")
            return False
        #
        try: import skimage
        except ImportError:
            print("\nERROR: The scikit-image package is missing. Please install it.")
            return False
        #
        try: from skimage.external import tifffile
        except ImportError:
            print("\nERROR: scikit-image package missing TIFF files support.")
            return False
        #
        return True
    #
#

if __name__ == '__main__':
    unittest.main()
#
