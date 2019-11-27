#!/usr/bin/env python3


import numpy as np
import cv2 as cv


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


class CTiledFrame(object):
    def __init__(self, na_input, i_nrows, i_ncols, b_copy_input=False):
        if na_input.shape[0] % i_nrows != 0: raise ValueError("FRACTIONAL HORIZONTAL PARTITION")
        if na_input.shape[1] % i_ncols != 0: raise ValueError("FRACTIONAL VERTICAL PARTITION")

        self.shape = (i_nrows, i_ncols)

        if b_copy_input:
            self._na_data = na_input.copy()
        else:
            self._na_data = na_input
        #
        self._i_nrows = i_nrows
        self._i_ncols = i_ncols
        self._Ridx = np.linspace(0, na_input.shape[0], (i_nrows + 1), dtype=np.int)
        self._Cidx = np.linspace(0, na_input.shape[1], (i_ncols + 1), dtype=np.int)
        
        if   len(na_input.shape) == 3: self._b_have_color_data = True
        elif len(na_input.shape) == 2: self._b_have_color_data = False
        else: raise ValueError("Unsupported shape of the input array: %s" % repr(na_input.shape))
        #
    #

    def __getitem__(self, t_addr):
        if type(t_addr) == type(...):
            return self._na_data # [...]

        i_row, i_col = t_addr[0], t_addr[1]

        if self._b_have_color_data:
            return self._na_data[ \
                self._Ridx[i_row]:self._Ridx[i_row + 1], \
                self._Cidx[i_col]:self._Cidx[i_col + 1], ...]
        else:
            return self._na_data[ \
                self._Ridx[i_row]:self._Ridx[i_row + 1], \
                self._Cidx[i_col]:self._Cidx[i_col + 1] ]
            #
        #
    #

    def __setitem__(self, t_addr, na_data):
        if type(t_addr) == type(...):
            self._na_data[...] = na_data[...]
            return

        i_row, i_col = t_addr[0], t_addr[1]

        if self._b_have_color_data:
            self._na_data[ \
                self._Ridx[i_row]:self._Ridx[i_row + 1], \
                self._Cidx[i_col]:self._Cidx[i_col + 1], ...] = na_data[...]
        else:
            self._na_data[ \
                self._Ridx[i_row]:self._Ridx[i_row + 1], \
                self._Cidx[i_col]:self._Cidx[i_col + 1] ] = na_data[...]
            #
        #
    #

    def __str__(self):
        l_out = []
        l_row = []
        for i_row in range(self._i_nrows):
            l_row.clear()
            for i_col in range(self._i_ncols):
                l_row.append(repr(self[i_row,i_col].shape))
                l_row.append(" | ")
            l_row.append('\n')
            s_data_row = "".join(l_row)
            l_out.append(s_data_row)
            s_dashes = (len(s_data_row)-2) * '-' + '\n'
            l_out.append(s_dashes)
        return "".join(l_out)
    #
#


class CStitchedFrame(object):
    def __init__(self, na_input, i_nrows, i_ncols, b_copy_input=False, i_border_sz=0):
        if len(na_input.shape) != 2: raise ValueError("Unsupported shape of the input array: %s" % repr(na_input.shape))
        if i_border_sz % 2 == True: raise ValueError("Border size must be even integer. Yours is: %s" % repr(i_border_sz))
        if na_input.shape[0] % i_nrows != 0: raise ValueError("FRACTIONAL HORIZONTAL PARTITION")
        if na_input.shape[1] % i_ncols != 0: raise ValueError("FRACTIONAL VERTICAL PARTITION")

        if b_copy_input:
            self._na_input = na_input.copy()
        else:
            self._na_input = na_input

        self._na_out = np.zeros_like(self._na_input)
        self._i_nrows = i_nrows
        self._i_ncols = i_ncols
        self._i_last_row = i_nrows - 1
        self._i_last_col = i_ncols - 1
        self.i_border_sz = i_border_sz
        self._i_hb_sz = int(i_border_sz/2) # half of the border size
        self._Ridx = np.linspace(0, na_input.shape[0], (i_nrows + 1), dtype=np.int)
        self._Cidx = np.linspace(0, na_input.shape[1], (i_ncols + 1), dtype=np.int)
        self.t_base_tile_shape = (int(na_input.shape[0] / i_nrows), int(na_input.shape[1] / i_ncols))

        # main data exchange interface for this class
        self.shape = (self._i_nrows, self._i_ncols)
    #

    def get_output(self):
        return self._na_out

    def clean_output(self):
        self._na_out.fill(0)

    def __getitem__(self, args):
        if not isinstance(args, tuple):
            raise ValueError("Unsupported argument type: %s" % repr(type(args)))

        i_row, i_col = args[0], args[1]
        i_Rbeg = self._Ridx[i_row]
        i_Rend = self._Ridx[i_row + 1]
        i_Cbeg = self._Cidx[i_col]
        i_Cend = self._Cidx[i_col + 1]

        if i_row == 0:
            i_Rend += self._i_hb_sz
        elif i_row == self._i_last_row:
            i_Rbeg -= self._i_hb_sz
        else:
            i_Rbeg -= self._i_hb_sz
            i_Rend += self._i_hb_sz

        if i_col == 0:
            i_Cend += self._i_hb_sz
        elif i_col == self._i_last_col:
            i_Cbeg -= self._i_hb_sz
        else:
            i_Cbeg -= self._i_hb_sz
            i_Cend += self._i_hb_sz

        return self._na_input[i_Rbeg:i_Rend, i_Cbeg:i_Cend]
    #

    def __setitem__(self, args, na_data):
        if not isinstance(args, tuple):
            raise ValueError("Unsupported argument type: %s" % repr(type(args)))

        i_row, i_col = args[0], args[1]
        i_Rbeg = self._Ridx[i_row]
        i_Rend = self._Ridx[i_row + 1]
        i_Cbeg = self._Cidx[i_col]
        i_Cend = self._Cidx[i_col + 1]

        if i_row == 0:
            i_Rend += self._i_hb_sz
        elif i_row == self._i_last_row:
            i_Rbeg -= self._i_hb_sz
        else:
            i_Rbeg -= self._i_hb_sz
            i_Rend += self._i_hb_sz

        if i_col == 0:
            i_Cend += self._i_hb_sz
        elif i_col == self._i_last_col:
            i_Cbeg -= self._i_hb_sz
        else:
            i_Cbeg -= self._i_hb_sz
            i_Cend += self._i_hb_sz

        self._na_out[i_Rbeg:i_Rend, i_Cbeg:i_Cend] += na_data[...] # NOTICE the '+=' operator
    #

    def __str__(self):
        l_out = []
        l_row = []
        for i_row in range(self._i_nrows):
            l_row.clear()
            for i_col in range(self._i_ncols):
                l_row.append(repr(self[i_row,i_col].shape))
                l_row.append(" | ")
            l_row.append('\n')
            s_data_row = "".join(l_row)
            l_out.append(s_data_row)
            s_dashes = (len(s_data_row)-2) * '-' + '\n'
            l_out.append(s_dashes)
        return "CStitchedFrame:\n\tBase tile shape: %s\n\tInput: %s\n\tNTiles: %s\n\tBorder: %i\n%s" % (
            repr(self.t_base_tile_shape),
            repr(self._na_input.shape),
            repr(self.shape),
            self.i_border_sz,
            "".join(l_out)
        )
    #
#


class CBorderedFrame(object):
    """Simple frame (2D array of numbers) surrounded by a border.
    The border style can be any of following:

    cv.BORDER_CONSTANT
    iiiiii|abcdefgh|iiiiiii with some specified i

    cv.BORDER_REPLICATE
    aaaaaa|abcdefgh|hhhhhhh

    cv.BORDER_REFLECT
    fedcba|abcdefgh|hgfedcb

    cv.BORDER_WRAP
    cdefgh|abcdefgh|abcdefg

    cv.BORDER_REFLECT_101
    gfedcb|abcdefgh|gfedcba

    cv.BORDER_TRANSPARENT
    uvwxyz|absdefgh|ijklmno

    cv.BORDER_REFLECT101
    same as BORDER_REFLECT_101

    cv.BORDER_DEFAULT
    same as BORDER_REFLECT_101
    """
    def __init__(self, na_input, i_border_sz, cv_border_type):
        if len(na_input.shape) != 2:
            raise ValueError("Unsupported shape of input frame")

        self.i_bsz = i_border_sz
        self._border_type = cv_border_type
        self.i_orig_h, self.i_orig_w = na_input.shape

        self._na_data = cv.copyMakeBorder(na_input, self.i_bsz, self.i_bsz, self.i_bsz, self.i_bsz, self._border_type)
        self.i_new_h, self.i_new_w = self._na_data.shape
        self.t_inner_slice = (slice(self.i_bsz, self.i_new_h - self.i_bsz), slice(self.i_bsz, self.i_new_w - self.i_bsz))

    def __getitem__(self, args):
        if isinstance(args, str):
            if args == 'inner':
                return self._na_data[self.t_inner_slice]
            elif args == 'outer':
                return self._na_data
            else:
                raise ValueError("Unsupported argument value: %s" % repr(args))
        else:
            raise ValueError("Unsupported argument type: %s" % repr(type(args)))
        #

    def __setitem__(self, args, na_data):
        if isinstance(args, str):
            if args == 'new':
                self._na_data[...] = cv.copyMakeBorder(na_data, self.i_bsz, self.i_bsz, self.i_bsz, self.i_bsz, self._border_type)
                if self.i_new_h != self._na_data.shape[0] or self.i_new_w != self._na_data.shape[1]:
                    raise ValueError("Inconsistent input shape detected")
            else:
                raise ValueError("Unsupported argument value: %s" % repr(args))
        else:
            raise ValueError("Unsupported argument type: %s" % repr(type(args)))
        #
    #
#


class CStiBordFrame(object):
    """Combination of a stitched frame surrounded by border.
    Amount of overlap between tiles is always equal to the border's width.
    """
    def __init__(self, na_input, i_nrows, i_ncols, i_border_sz, cv_border_type, b_copy_input=False):
        self.shape = (i_nrows, i_ncols)
        self.i_border_sz = i_border_sz
        self.t_base_tile_shape = (int(na_input.shape[0] / i_nrows), int(na_input.shape[1] / i_ncols))
        self.oc_bordered_frame = CBorderedFrame(na_input, self.i_border_sz, cv_border_type)
        self.oc_stitched_frame = CStitchedFrame(
            self.oc_bordered_frame['outer'],
            i_nrows, i_ncols,
            b_copy_input=b_copy_input,
            i_border_sz=self.i_border_sz
        )
        self.na_lining = np.ones_like(self.oc_bordered_frame['outer'], dtype=na_input.dtype)
        oc_tilining = CStitchedFrame(self.na_lining, i_nrows, i_ncols, i_border_sz=self.i_border_sz)
        for ix, iy in np.ndindex(oc_tilining.shape):
            oc_tilining[ix, iy] = oc_tilining[ix, iy]
        # This is correct!
        # Data will be copied from oc_tilining._na_out into the self.na_lining
        self.na_lining[...] = oc_tilining.get_output()
        # tuple of length 2.
        # Each member of the tuple is a vector of indices
        # of the self.na_lining corresponding to elements bigger than 1
        self.t_lining_idx = np.where(self.na_lining > 1)
    #

    def stitch(self):
        na_stitched_data = self.oc_stitched_frame.get_output()
        na_stitched_data[self.t_lining_idx] /= self.na_lining[self.t_lining_idx]

    def clean(self):
        self.oc_stitched_frame.clean_output()

    def __getitem__(self, args):
        if isinstance(args, str):
            na_stitched_output = self.oc_stitched_frame.get_output()
            if args == 'inner':
                return na_stitched_output[self.oc_bordered_frame.t_inner_slice]
            elif args == 'outer':
                return na_stitched_output
            else:
                raise ValueError("Unsupported argument value: %s" % repr(args))
        elif isinstance(args, tuple):
            i_row, i_col = args[0], args[1]
            return self.oc_stitched_frame[i_row, i_col]
        else:
            raise ValueError("Unsupported argument type: %s" % repr(type(args)))
    #

    def __setitem__(self, args, na_data):
        if isinstance(args, str) and args == 'new':
            self.oc_bordered_frame['new'] = na_data
            return
        elif isinstance(args, tuple):
            i_row, i_col = args[0], args[1]
            self.oc_stitched_frame[i_row, i_col] = na_data[...]
            return
        else:
            raise ValueError("Unsupported argument: %s %s" % (repr(args), repr(type(args))))
    #

    def __str__(self):
        return "\nCStiBordFrame:\n\tBase tile shape: %s\n\tInput: %s\n\tNTiles: %s\n\tBorder: %s\n\tBordered: %s\n%s" % (
            repr(self.t_base_tile_shape),
            repr(self.oc_bordered_frame['inner'].shape),
            repr(self.shape),
            repr(self.i_border_sz),
            repr(self.oc_bordered_frame['outer'].shape),
            self.oc_stitched_frame.__str__()
        )
    #
#


def draw_border(na_frame, border_width=1, border_value=None):
    if len(na_frame.shape) != 2:
        raise ValueError("Unsupported shape of input frame: %s" % repr(na_frame.shape))

    border_width = int(border_width)
    if border_width < 1:
        raise ValueError("Border width must be >= 1")

    if border_value == None:
        border_value = na_frame.max(axis=None)

    na_frame[:, 0:border_width] = border_value
    na_frame[:, -border_width:] = border_value
    na_frame[0:border_width, :] = border_value
    na_frame[-border_width:, :] = border_value
    return na_frame
#


if __name__ == '__main__':

    # input image size:
    i_nrows, i_ncols = 8, 8

    # number of tiles to split the input image:
    i_nrow_tiles, i_ncol_tiles = 2, 2

    # the input image
    na_img = np.arange(i_nrows * i_ncols, dtype=np.int).reshape(i_nrows, i_ncols)

    print("Input array (frame):")
    print(na_img)
    print()

    # the tiled image:
    oc_timg = CTiledFrame(na_img, i_nrow_tiles, i_ncol_tiles)

    print("Representation of the tiled input frame:")
    print(oc_timg)

    for ix, iy in np.ndindex(oc_timg.shape):
        print("Tile (%i, %i) content:" % (ix, iy))
        print(oc_timg[ix, iy])
        print()

    print("Modify (x2) content of each tile inplace:")
    for ix, iy in np.ndindex(oc_timg.shape):
        oc_timg[ix, iy] *= 2

    for ix, iy in np.ndindex(oc_timg.shape):
        print( oc_timg[ix, iy] )
        print()

    print("Assign new values (ones) to the whole frame:")
    na_ones = np.ones(i_nrows * i_ncols, dtype=np.int).reshape(i_nrows, i_ncols)
    oc_timg[...] = na_ones

    for ix, iy in np.ndindex(oc_timg.shape):
        print( oc_timg[ix, iy] )
        print()
    #
#
