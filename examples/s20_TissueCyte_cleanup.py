#!/usr/bin/env python3


import os
import sys
import cv2 as cv
import numpy as np


"""
Copyright (C) 2019 Lilia Evgeniou, Denis Polygalov
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
This script demonstrate simple preprocessing stage
of data recorded by TissueCyte high throughput automated
whole organ imaging system:
https://www.tissuevision.com/tissuecyte
"""


def find_borders(na_contour):
    # find top, bottom, left, right boundaries
    # adds/subtracts a small amount to make more comfortable boundary
    # TODO check this
    i_top = min(na_contour, key=lambda x: x[0][0])[0][0] - 10
    i_bot = max(na_contour, key=lambda x: x[0][0])[0][0] + 10
    i_lef = min(na_contour, key=lambda x: x[0][1])[0][1] - 10
    i_rig = max(na_contour, key=lambda x: x[0][1])[0][1] + 10

    return np.array([i_top, i_bot, i_lef, i_rig])
#


def get_contour_mask(na_frame):
    # TODO clean up and do more optimization

    # convert to uint8; next functions does not support other types
    na_uint8 = cv.convertScaleAbs(na_frame)

    # remove noise
    na_noiseless = cv.medianBlur(na_uint8, 5)

    # make it binary using arbitrary threshold
    _, thresh = cv.threshold(na_noiseless, 150, 255, cv.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    opening = cv.morphologyEx(thresh, cv.MORPH_OPEN, kernel, iterations=2)
    na_goodregion = cv.dilate(opening, kernel, iterations=3)

    # re-threshold dilated image
    _, thresh = cv.threshold(na_goodregion, 127, 255, 0)

    # find contours of binary region
    _, l_contours, _ = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_NONE)

    # make an all-black image of same size as na_frame
    na_contour_image = na_frame.copy()
    na_contour_image.fill(0)

    # if no contours are found, return a black mask
    if len(l_contours) == 0:
        return na_contour_image, np.array([float("+inf"), float("-inf")]*2)

    # draw white mask on the black image
    for na_c in l_contours:
        # finds contour area
        f_c_area = cv.contourArea(na_c)

        # fills the contour and draws it
        cv.fillPoly(na_contour_image, pts=[na_c], color=255)
        # cv.drawContours(na_contour_image, c, -1, (255), 2, lineType=cv.LINE_4)
    #

    # makes a copy of na_contour_image which is then converted to uint8
    na_contour_image_copy = na_contour_image.copy()
    na_contour_image_uint8 = cv.convertScaleAbs(na_contour_image_copy)

    # finds largest contour again by finding contour of contour image
    # (to ignore overlapping contours inside big contour)
    _, thresh = cv.threshold(na_contour_image_uint8, 127, 255, 0)
    _, l_larger_contours, _ = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_NONE)

    na_largest_contour = max(l_larger_contours, key=lambda x: cv.contourArea(x))

    # finds points of convex hull of largest contour found previously
    na_hull = cv.convexHull(na_largest_contour)

    # finds top, bottom, left, right borders of hull
    na_borders = find_borders(na_hull)

    # adds this convex hull to the original contour image to make the final mask
    cv.fillPoly(na_contour_image, pts=[na_hull], color=255)

    # returns mask, and border
    return na_contour_image, na_borders
#


def main():
    """
    The input directory contain files named similar to following pattern:
    downsampled-McHugh_Lab_181_614_S000001_L01_ch01.tif
    downsampled-McHugh_Lab_181_614_S000001_L01_ch02.tif
    downsampled-McHugh_Lab_181_614_S000001_L01_ch03.tif
    downsampled-McHugh_Lab_181_614_S000001_L01_ch04.tif
    downsampled-McHugh_Lab_181_614_S000002_L01_ch01.tif
    downsampled-McHugh_Lab_181_614_S000002_L01_ch02.tif
    downsampled-McHugh_Lab_181_614_S000002_L01_ch03.tif
    downsampled-McHugh_Lab_181_614_S000002_L01_ch04.tif
    downsampled-McHugh_Lab_181_614_S000003_L01_ch01.tif
    downsampled-McHugh_Lab_181_614_S000003_L01_ch02.tif
    downsampled-McHugh_Lab_181_614_S000003_L01_ch03.tif
    downsampled-McHugh_Lab_181_614_S000003_L01_ch04.tif
    and so on.
    """
    s_input_dir = "D:\\data\\hongshen\\McHugh_lab_181_614_stitching\\downsampled"
    s_wcard_in  = "downsampled-McHugh_Lab_181_614_S000*_L01_ch03.tif"
    s_fname_out = "downsampled-McHugh_Lab_181_614_L01_ch03.tif"

    print("Input directory:\t%s" % s_input_dir)

    t_input_files = enum_video_files(s_input_dir, s_wcard_in, i_num_pos=2)

    print("Found %d input file(s)." % len(t_input_files))

    # create a multi-part movie object
    oc_movie = CMuPaMovieTiff(t_input_files)

    print("\nMovie information:")
    print(oc_movie.df_info)

    # create tiff writer object for output data storage
    oc_tiff_writer = CSingleTiffWriter(s_fname_out, b_delete_existing=True)

    # initial values of top, bottom, left and right borders for frame cropping
    i_min_top = 0
    i_max_bot = 0
    i_min_lef = 0
    i_max_rig = 0

    # the frame counter
    i_frame_id = 0

    # Stage 1:
    # read and process frames one by one until the end
    # calculate global values of the i_min_top, i_max_bot, i_min_lef, i_max_rig
    while(oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())

        _, na_borders = get_contour_mask(oc_movie.na_frame)
        i_top, i_bot, i_lef, i_rig = na_borders

        if i_frame_id == 0:
            i_min_top = oc_movie.na_frame.shape[0]
            i_min_lef = oc_movie.na_frame.shape[1]
        else:
            i_min_top = min(i_min_top, i_top)
            i_max_bot = max(i_max_bot, i_bot)
            i_min_lef = min(i_min_lef, i_lef)
            i_max_rig = max(i_max_rig, i_rig)

        i_frame_id += 1
        if i_frame_id >= len(t_input_files): break

    # reset the oc_movie object's state and the frame counter
    oc_movie = CMuPaMovieTiff(t_input_files)
    i_frame_id = 0

    # Stage 2:
    # read and process frames one by one until the end
    # crop each frame according to the i_min_top, i_max_bot, i_min_lef, i_max_rig
    # calculated above and erase pixels that does not belong to the contour mask
    while (oc_movie.read_next_frame()):
        print("%s" % oc_movie.get_frame_stat())

        na_mask_image, _ = get_contour_mask(oc_movie.na_frame)

        oc_movie.na_frame[np.where(na_mask_image == 0)] = 0

        # write new contour frame into tiff file
        oc_tiff_writer.write_next_frame(oc_movie.na_frame[i_min_lef:i_max_rig, i_min_top:i_max_bot])

        i_frame_id += 1
        if i_frame_id >= len(t_input_files): break

    # always close all tiff writers after usage!
    oc_tiff_writer.close()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.ioutils import enum_video_files
    from mendouscopy.mupamovie import CMuPaMovieTiff, CSingleTiffWriter
    main()
#

