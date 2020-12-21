#!/usr/bin/env python3


import os
import sys
import configparser

import cv2 as cv
import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import tifffile


"""
Copyright (C) 2018-2020 Denis Polygalov,
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


def check_dir(s_dst_dir):
    if not os.path.isdir(s_dst_dir):
        os.mkdir(s_dst_dir)
    if not os.path.isdir(s_dst_dir):
        raise IOError("Unable to create output directory: %s" % s_dst_dir)
#


def plot_result(s_input_dir, s_fname_prefix):
    s_fluo_data_in_fname = os.path.join(s_input_dir, s_fname_prefix + "fluo.npy")
    d_fluo_data = np.load(s_fluo_data_in_fname, allow_pickle=True).item()
    s_out_fname = os.path.join(s_input_dir, s_fname_prefix + "ROI_and_dFF.png")
    s_out_fname_iproj_max = os.path.join(s_input_dir, s_fname_prefix + "IPROJ_max.tiff")
    s_out_fname_iproj_std = os.path.join(s_input_dir, s_fname_prefix + "IPROJ_std.tiff")

    print("Input data file:\t%s" % s_fluo_data_in_fname)
    for s_key in d_fluo_data.keys():
        DVAR(d_fluo_data[s_key], s_var_name=s_key)

    na_img_16U = cv.normalize(d_fluo_data['IPROJ_max'], None, alpha=0, beta=(2**16-1), norm_type=cv.NORM_MINMAX, dtype=cv.CV_16U)
    with tifffile.TiffWriter(s_out_fname_iproj_max, bigtiff=False) as h_file:
        h_file.save(na_img_16U)

    na_img_16U = cv.normalize(d_fluo_data['IPROJ_std'], None, alpha=0, beta=(2**16-1), norm_type=cv.NORM_MINMAX, dtype=cv.CV_16U)
    with tifffile.TiffWriter(s_out_fname_iproj_std, bigtiff=False) as h_file:
        h_file.save(na_img_16U)

    # create data viewer
    # we have to keep reference to this object
    # otherwise it won't work
    h_viewer = CPerROIDataViewer(d_fluo_data)
    # so use this kind of artificial solution
    # in order to avoid complains about unused variable:
    h_viewer.connect()
    plt.savefig(s_out_fname, dpi=300, bbox_inches='tight')
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from gui.view import CPerROIDataViewer

    i_target_section = None
    # i_target_section = 0 # use this to process single section only

    s_work_dir = "output"
    check_dir(s_work_dir)
    check_dir("output_expected")

    # load global configuration file
    oc_global_cfg = configparser.ConfigParser()
    oc_global_cfg.read('v10n.ini')
    l_sections = oc_global_cfg.sections()

    for i_section_idx, s_section in enumerate(l_sections):
        print()
        if i_target_section is not None and i_section_idx != i_target_section:
            print("INFO: skip section: [%s]" % s_section)
            continue

        print("INFO: process section: [%s]" % s_section)
        check_dir(os.path.join(s_work_dir, s_section))

        s_out_file_prefix = oc_global_cfg[s_section]['out_file_prefix']
        s_dst_file = oc_global_cfg[s_section]['dst_file']
        s_ini_file = oc_global_cfg[s_section]['ini_file']
        s_dst_path = os.path.join(s_work_dir, s_section, s_dst_file)

        if not os.path.isfile(s_dst_path):
            raise RuntimeError("Unable to access input file: %s" % s_dst_path)
        if not os.path.isfile(s_ini_file):
            raise RuntimeError("Unable to access ini file for CaFFlow: %s" % s_ini_file)

        if s_section == "CaImAn_demoMovie":
            s_dst_path_alt, s_fext = os.path.splitext(s_dst_path)
            s_dst_path = s_dst_path_alt + "WHT" + s_fext

        print("INFO: input file: %s" % s_dst_path)

        s_input_dir = os.path.join(s_work_dir, s_section)
        plot_result(s_input_dir, s_out_file_prefix)
#


