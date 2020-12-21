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
This script demonstrate who to remove an arbitrary Principal Component (PC)
from the input frame. Note that the PC numbering is started from zero(!)
and the first one (e.g. #0) is being removed by default.
"""


def main():
    na_img = tifffile.imread("CW2003_H14_M57_S54_msCam1_frame0.tiff").astype(np.float32)
    print("Input image shape:", na_img.shape) # (480, 752)
    oc_pc1wiper = CPrinCompWiper(na_img.shape[0], na_img.shape[1])
    oc_pc1wiper.process_frame(na_img)

    na_img_rotated = np.rot90(na_img)
    print("Input image shape:", na_img_rotated.shape) # (752, 480)
    oc_pc1wiper_rotated = CPrinCompWiper(na_img_rotated.shape[0], na_img_rotated.shape[1])
    oc_pc1wiper_rotated.process_frame(na_img_rotated)

    na_img_square = na_img[:,0:na_img.shape[0]]
    print("Input image shape:", na_img_square.shape) # (480, 480)
    oc_pc1wiper_square = CPrinCompWiper(na_img_square.shape[0], na_img_square.shape[1])
    oc_pc1wiper_square.process_frame(na_img_square)

    plt.figure(1)
    plt.subplot(211)
    plt.imshow(na_img)
    plt.subplot(212)
    plt.imshow(oc_pc1wiper.na_out)
    plt.tight_layout()

    plt.figure(2)
    plt.subplot(121)
    plt.imshow(na_img_rotated)
    plt.subplot(122)
    plt.imshow(oc_pc1wiper_rotated.na_out)
    plt.tight_layout()

    plt.figure(3)
    plt.subplot(121)
    plt.imshow(na_img_square)
    plt.subplot(122)
    plt.imshow(oc_pc1wiper_square.na_out)
    plt.tight_layout()

    plt.show()
    sys.exit()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.filtering import CPrinCompWiper
    import numpy as np
    import matplotlib.pyplot as plt
    import tifffile
    main()
#

