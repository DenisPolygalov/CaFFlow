#!/usr/bin/env python3


import os
import sys
import glob
import numpy as np
import scipy.io as sio


"""
Copyright (C) 2019 Denis Polygalov,
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


def process_ROI_data(l_ROI_data, s_key_in):
    l_out = []
    for d_ROI_data in l_ROI_data:
        l_out.append(d_ROI_data[s_key_in])
    return l_out
#


def process_npy_file(s_input_npy_file, s_output_mat_file):
    d_data_in = np.load(s_input_npy_file, allow_pickle=True).item()
    d_data_out = {}

    print("npy2mat:", os.path.basename(s_input_npy_file))
    for s_key in d_data_in:
        print("\t", s_key, type(d_data_in[s_key]))
        if isinstance(d_data_in[s_key], np.ndarray):
            d_data_out[s_key] = d_data_in[s_key]
        elif isinstance(d_data_in[s_key], list) and len(d_data_in[s_key]) > 0:
            if  isinstance(d_data_in[s_key][0], int) or \
                isinstance(d_data_in[s_key][0], float) or \
                isinstance(d_data_in[s_key][0], np.ndarray):
                    d_data_out[s_key] = np.array(d_data_in[s_key], dtype=object)
            else:
                if s_key == "ROI_data":
                    s_key_out = "ROI_mask_pix_idx"
                    l_val_out = process_ROI_data(d_data_in[s_key], "mask_pix_idx")
                    d_data_out[s_key_out] = np.array(l_val_out, dtype=object)
                    print("\t\t", s_key_out, type(d_data_out[s_key_out]))
                    if len(d_data_in[s_key]) > 0 and "mask_weights" in d_data_in[s_key][0]:
                        s_key_out = "ROI_mask_weights"
                        l_val_out = process_ROI_data(d_data_in[s_key], "mask_weights")
                        d_data_out[s_key_out] = np.array(l_val_out)
                        print("\t\t", s_key_out, type(d_data_out[s_key_out]))
                else:
                    print("WARNING: skip sub-key:", s_key, type(d_data_in[s_key][0]))
        else:
            print("WARNING: skip key:", s_key, type(d_data_in[s_key]))
    sio.savemat(s_output_mat_file, d_data_out)
#


def npy2mat(s_input_dir, b_overwrite_output=True):
    l_file_wcards = [
        "*_fluo.npy",
        "*_roi_data.npy",
        "*_reg_data.npy"
    ]
    i_file_cnt = 0
    if not os.path.isdir(s_input_dir):
        raise ValueError("Requested input path is not a directory")
    for s_file_wcard in l_file_wcards:
        l_file_list = glob.glob(os.path.join(s_input_dir, s_file_wcard))
        for s_input_file in l_file_list:
            s_output_file = os.path.splitext(s_input_file)[0] + ".mat"
            if not b_overwrite_output:
                print("WARNING: skip existing output file")
                continue
            process_npy_file(s_input_file, s_output_file)
            i_file_cnt += 1
    print("npy2mat: End of work. Processed %i file(s)." % i_file_cnt)
#


if __name__ == '__main__':
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print("ERROR: not enough/wrong input arguments")
        print("Usage: %s dir_containing_npy_files" % os.path.split(sys.argv[0])[-1])
        sys.exit(-1)
    npy2mat(sys.argv[1])
#

