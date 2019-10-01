#!/usr/bin/env python3


import os
import sys


"""
Copyright (C) 2018 Denis Polygalov,
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


"""
This script demonstrate effect of so called 'edge-preserving' spatial
filter used to enhance features of the frame we interested in.
"""


def main():
    na_img = tifffile.imread("CW2003_H14_M57_S54_msCam1_frame0.tiff").astype(np.float32)
    oc_pc1wiper = CPrinCompWiper(na_img.shape[0], na_img.shape[1])
    oc_filter = CFastGuidedFilter(3)

    oc_pc1wiper.process_frame(na_img)
    na_no_pc1_img = oc_pc1wiper.na_out.copy()

    oc_filter.process_frame(cv2.normalize(oc_pc1wiper.na_out, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F))

    plt.figure(1)
    plt.subplot(121)
    plt.imshow(na_no_pc1_img)
    plt.subplot(122)
    plt.imshow(oc_filter.na_out)
    plt.tight_layout()

    plt.show()
    sys.exit()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.filtering import CPrinCompWiper
    from mendouscopy.filtering import CFastGuidedFilter
    import cv2
    import numpy as np
    import matplotlib.pyplot as plt
    from skimage.external import tifffile
    main()
#

