#!/usr/bin/env python3


import unittest


class CTestImportPackages(unittest.TestCase):
    def test_import(self):
        self.assertTrue(self.is_import_OK())

    def is_import_OK(self):
        try:
            import numpy as np
            print("\nINFO: NumPy package version: %s" % np.version.full_version)
        except ImportError:
            print("\nERROR: NumPy package is missing. Please install it.")
            return False

        try:
            import scipy as sp
            print("\nINFO: SciPy package version: %s" % sp.version.full_version)
        except ImportError:
            print("\nThe SciPy package is missing. Please install it.")
            return False

        try:
            import cv2 as cv
            print("\nINFO: OpenCV package version: %s" % cv.__version__)
        except ImportError:
            print("\nERROR: OpenCV package is missing. Please install it.")
            return False

        try:
            import pandas as pd
            print("\nINFO: Pandas package version: %s" % pd.__version__)
        except ImportError:
            print("\nERROR: The Pandas package is missing. Please install it.")
            return False

        try:
            import tifffile
            print("\nINFO: tifffile package version: %s" % tifffile.__version__)
        except ImportError:
            print("\nERROR: The tifffile package is missing. Please install it.")
            return False

        return True
    #
#

if __name__ == '__main__':
    unittest.main()
#
