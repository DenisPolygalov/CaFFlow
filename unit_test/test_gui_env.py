#!/usr/bin/env python3


import unittest


class CTestImportPackages(unittest.TestCase):
    def test_import(self):
        self.assertTrue(self.is_import_OK())

    def is_import_OK(self):
        try:
            from PyQt5.Qt import QT_VERSION_STR
            print("\nINFO: PyQt package version: %s" % QT_VERSION_STR)
        except ImportError:
            print("\nERROR: PyQt5 package is missing. Please install it.")
            return False

        try:
            from PyQt5 import QtMultimedia
            if hasattr(QtMultimedia, 'QCameraInfo'):
                print("\nINFO: QCameraInfo class found in QtMultimedia module")
            else:
                raise ImportError("Your PyQt5 package does not support QCameraInfo class")

            if hasattr(QtMultimedia, 'QCamera'):
                print("\nINFO: QCamera class found in QtMultimedia module")
            else:
                raise ImportError("Your PyQt5 package does not support QCamera class")

        except ImportError:
            print("\nERROR: PyQt5 package is installed, but missing QtMultimedia support")
            return False

        return True
    #
#

if __name__ == '__main__':
    unittest.main()
#
