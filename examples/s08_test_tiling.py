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


def test_draw_border():
    na_image = np.zeros([8,8], dtype=np.uint32)
    print(na_image)
    print()

    draw_border(na_image, border_width=1, border_value=3)
    print(na_image)
    print()

    na_image.fill(0)

    draw_border(na_image, border_width=2, border_value=7)
    print(na_image)

    sys.exit()
#


def test_bordering_synthetic_data():
    na_img = np.arange(64).reshape(8,8)
    DVAR(na_img)

    oc_brd_reflect = CBorderedFrame(na_img, 3, cv.BORDER_REFLECT_101)
    oc_brd_warp    = CBorderedFrame(na_img, 3, cv.BORDER_WRAP)

    DVAR(oc_brd_reflect['inner'], s_var_name='inner_part_of_bordered_image')
    DVAR(oc_brd_reflect['outer'], s_var_name='outer_part_of_bordered_image')

    plt.figure(figsize=(8,8)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(na_img)
    plt.title('original image')

    plt.subplot(222)
    plt.imshow(oc_brd_reflect['outer'])
    plt.title('bordered, reflect')

    plt.subplot(223)
    plt.imshow(oc_brd_warp['outer'])
    plt.title('bordered, warp')

    plt.subplot(224)
    plt.imshow(oc_brd_reflect['inner'])
    plt.title('bordered, inner')

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_bordering_real_data(s_in_fname):
    # load single grayscale(!) image from file
    na_img = tifffile.imread(s_in_fname).astype(np.float32)

    # draw a border inside of the input image
    draw_border(na_img, border_width=1)
    DVAR(na_img)
    print(na_img[0:4, 0:4])

    oc_bordered_img = CBorderedFrame(na_img, 100, cv.BORDER_WRAP)
    DVAR(oc_bordered_img['inner'], s_var_name='inner_part_of_bordered_image')
    DVAR(oc_bordered_img['outer'], s_var_name='outer_part_of_bordered_image')

    na_outer_copy = oc_bordered_img['outer'].copy()
    # wipe out the inner part for example...
    na_outer_copy[oc_bordered_img.t_inner_slice] = 0

    plt.figure(figsize=(8,6)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(oc_bordered_img['inner'])

    plt.subplot(222)
    plt.imshow(oc_bordered_img['outer'])

    plt.subplot(223)
    oc_bordered_img['new'] = np.flipud(na_img)
    plt.imshow(oc_bordered_img['outer'])

    plt.subplot(224)
    plt.imshow(na_outer_copy)

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_tiling_synthetic_data():
    # input image size:
    i_nrows, i_ncols = 512, 512

    # number of tiles to split the input image:
    i_nrow_tiles, i_ncol_tiles = 8, 8

    # the input image
    na_img = np.zeros(i_nrows * i_ncols, dtype=np.int).reshape(i_nrows, i_ncols)

    # the tiled image
    oc_tiled_img = CTiledFrame(na_img, i_nrow_tiles, i_ncol_tiles)
    print(oc_tiled_img)

    for ix, iy in np.ndindex(oc_tiled_img.shape):
        oc_tiled_img[ix, iy] += (ix * iy)

    plt.figure(figsize=(8,8)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(oc_tiled_img[...])
    plt.title('oc_tiled_img[...]')

    na_img_copy = oc_tiled_img[...].copy()
    oc_tiled_img_copy = CTiledFrame(na_img_copy, i_nrow_tiles, i_ncol_tiles)

    na_ix_rand = np.random.randint(i_nrow_tiles, size=i_nrow_tiles)
    na_iy_rand = np.random.randint(i_ncol_tiles, size=i_ncol_tiles)

    # reassign tiles randomly (may contain repetitions!)
    for ix, iy in np.ndindex(oc_tiled_img.shape):
        oc_tiled_img[ix, iy] = oc_tiled_img_copy[na_ix_rand[ix], na_iy_rand[iy]]

    plt.subplot(222)
    plt.imshow(oc_tiled_img[...])
    plt.title('oc_tiled_img shuffled')

    plt.subplot(223)
    plt.imshow(oc_tiled_img_copy[...])
    plt.title('oc_tiled_img_copy[...]')

    oc_tiled_img_copy[...] = oc_tiled_img[...]

    plt.subplot(224)
    plt.imshow(oc_tiled_img_copy[...])
    plt.title('oc_tiled_img_copy shuffled')

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_tiling_real_data(s_in_fname):
    # load single grayscale(!) image from file
    na_img = tifffile.imread(s_in_fname).astype(np.float32)

    # number of tiles to split the input image:
    i_nrow_tiles, i_ncol_tiles = 16, 8

    plt.figure(figsize=(11,4)) # figure size (W,H) in inches
    plt.subplot(121)
    plt.imshow(na_img)

    # the tiled image
    oc_tiled_img = CTiledFrame(na_img, i_nrow_tiles, i_ncol_tiles)
    print(oc_tiled_img)

    na_img_copy = oc_tiled_img[...].copy()
    oc_tiled_img_copy = CTiledFrame(na_img_copy, i_nrow_tiles, i_ncol_tiles)

    na_ix_rand = np.arange(i_nrow_tiles)
    np.random.shuffle(na_ix_rand)

    na_iy_rand = np.arange(i_ncol_tiles)
    np.random.shuffle(na_iy_rand)

    # shuffle tiles randomly
    for ix, iy in np.ndindex(oc_tiled_img.shape):
        oc_tiled_img[ix, iy] = oc_tiled_img_copy[na_ix_rand[ix], na_iy_rand[iy]]

    plt.subplot(122)
    plt.imshow(oc_tiled_img[...])

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_stitching_synthetic_data():
    # input image size:
    i_nrows, i_ncols = 480, 752

    # number of tiles to split the input image:
    i_nrow_tiles, i_ncol_tiles = 8, 8
    i_patch_overlap_width = 16

    # the input image
    na_img = np.zeros(i_nrows * i_ncols, dtype=np.int).reshape(i_nrows, i_ncols)

    # this tiled image is used only for generation of testing data 
    oc_tiled_img = CTiledFrame(na_img, i_nrow_tiles, i_ncol_tiles)
    for ix, iy in np.ndindex(oc_tiled_img.shape):
        oc_tiled_img[ix, iy] += (ix * iy)

    plt.figure(figsize=(8,8)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(na_img)
    plt.title('na_img')

    oc_stitched_img = CStitchedFrame(na_img, i_nrow_tiles, i_ncol_tiles, i_border_sz=i_patch_overlap_width)
    # stitch input image with itself in two steps
    # 1. first assign each patch
    for ix, iy in np.ndindex(oc_stitched_img.shape):
        oc_stitched_img[ix, iy] = oc_stitched_img[ix, iy]
    print(oc_stitched_img)

    # show the result of assignment
    plt.subplot(222)
    plt.imshow(oc_stitched_img.get_output())
    plt.title('oc_stitched_img.get_output()')

    # prepare 'lining' matrix which contain values 1, 2 and 4.
    na_lining_img = np.ones_like(na_img)
    oc_lining = CStitchedFrame(na_lining_img, i_nrow_tiles, i_ncol_tiles, i_border_sz=i_patch_overlap_width)
    for ix, iy in np.ndindex(oc_lining.shape):
        oc_lining[ix, iy] = oc_lining[ix, iy]

    # show the lining matrix
    plt.subplot(223)
    plt.imshow(oc_lining.get_output())
    plt.title('oc_lining.get_output()')

    # Do the stitching.
    # Optimized version of this method is implemented in the CStiBordFrame class
    na_out = oc_stitched_img.get_output() / oc_lining.get_output()

    # Show the result of stitching
    plt.subplot(224)
    plt.imshow(na_out)
    plt.title('na_out')

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_stibord_synthetic_data():
    # input image size:
    i_nrows, i_ncols = 480, 752

    # number of patches to split the input image:
    i_nrow_tiles, i_ncol_tiles = 8, 8

    # amount of overlap between patches
    i_border_sz = 16

    # the input image
    na_img = np.zeros(i_nrows * i_ncols, dtype=np.float32).reshape(i_nrows, i_ncols)

    # this tiled image is used only for generation of testing data
    oc_tiled_img = CTiledFrame(na_img, i_nrow_tiles, i_ncol_tiles)
    for ix, iy in np.ndindex(oc_tiled_img.shape):
        oc_tiled_img[ix, iy] += (ix * iy)

    plt.figure(figsize=(8,8)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(na_img)
    plt.title('na_img')

    oc_stibord_image = CStiBordFrame(na_img, i_nrow_tiles, i_ncol_tiles, i_border_sz, cv.BORDER_REPLICATE)

    # you have to clean the object if it was already used before
    # oc_stibord_image.clean()

    for ix, iy in np.ndindex(oc_stibord_image.shape):
        oc_stibord_image[ix, iy] = oc_stibord_image[ix, iy]
    print(oc_stibord_image)

    # show the result of assignment
    plt.subplot(222)
    plt.imshow(oc_stibord_image['outer'])
    plt.title("oc_stibord_image['outer']")

    plt.subplot(223)
    plt.imshow(oc_stibord_image.na_lining)
    plt.title('oc_stibord_image.na_lining')

    oc_stibord_image.stitch()

    plt.subplot(224)
    plt.imshow(oc_stibord_image['inner'])
    plt.title("oc_stibord_image['inner']")

    plt.tight_layout()
    plt.show()

    sys.exit()
#


def test_stibord_real_data(s_in_fname):
    oc_movie = CMuPaMovieTiff((s_in_fname,))
    oc_movie.read_next_frame()
    na_frame = oc_movie.na_frame.astype(np.float32)
    DVAR(na_frame)
    oc_stibord_image = CStiBordFrame(na_frame, 8, 8, 16, cv.BORDER_REFLECT_101)
    print(oc_stibord_image)
    for ix, iy in np.ndindex(oc_stibord_image.shape):
        # oc_stibord_image[ix, iy] = oc_stibord_image[ix, iy]
        oc_stibord_image[ix, iy] = np.flipud(oc_stibord_image[ix, iy])
    plt.figure(figsize=(8,8)) # figure size (W,H) in inches
    plt.subplot(221)
    plt.imshow(na_frame)
    plt.subplot(222)
    plt.imshow(oc_stibord_image['inner'])
    oc_stibord_image.stitch()
    plt.subplot(223)
    plt.imshow(oc_stibord_image['inner'])
    plt.subplot(224)
    plt.imshow(na_frame - oc_stibord_image['inner'])
    plt.tight_layout()
    plt.show()
    sys.exit()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from mendouscopy.mupamovie import CMuPaMovieTiff
    from mendouscopy.tiling import CBorderedFrame
    from mendouscopy.tiling import CStitchedFrame
    from mendouscopy.tiling import CStiBordFrame
    from mendouscopy.tiling import CTiledFrame
    from mendouscopy.tiling import draw_border
    import cv2 as cv
    import numpy as np
    import matplotlib.pyplot as plt
    from skimage.external import tifffile

    # Each of the functions below have sys.exit() at it's end.
    # Enjoy one by one.

    # test_draw_border()
    # test_bordering_synthetic_data()
    # test_bordering_real_data("CW2003_H14_M57_S54_msCam1_frame0.tiff")
    # test_tiling_synthetic_data()
    # test_tiling_real_data("CW2003_H14_M57_S54_msCam1_frame0.tiff")
    # test_stitching_synthetic_data()
    # test_stibord_synthetic_data()
    test_stibord_real_data("x16_frame0to99.tiff")
#

