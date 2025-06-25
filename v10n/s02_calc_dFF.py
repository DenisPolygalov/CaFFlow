#!/usr/bin/env python3


import os
import sys
import configparser

import tifffile


"""
Copyright (C) 2018, 2019 Denis Polygalov,
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


def convert_tiff(s_fname_in, s_fname_out):
    na_data = tifffile.imread(s_fname_in)
    i_nframes, i_nrows, i_ncols  = na_data.shape
    with tifffile.TiffWriter(s_fname_out, bigtiff=False) as h_file:
        for i_frame_idx in range(i_nframes):
            h_file.write(na_data[i_frame_idx,...])
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.pipelines import register_frames_detect_rois
    from mendouscopy.pipelines import pickup_rois_extract_fluo
    from mendouscopy.npy2mat import npy2mat

    i_target_section = None
    # i_target_section = 0 # use this to process single section only

    s_work_dir = "output"
    check_dir(s_work_dir)

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
            s_dst_path_alt = s_dst_path_alt + "WHT" + s_fext
            convert_tiff(s_dst_path, s_dst_path_alt)
            s_dst_path = s_dst_path_alt

        print("INFO: input file: %s" % s_dst_path)

        s_input_dir = os.path.join(s_work_dir, s_section)
        t_input_files = (s_dst_path,) # notice the comma(!)

        # load local configuration file
        oc_rec_cfg = configparser.ConfigParser()
        oc_rec_cfg.read(s_ini_file)

        register_frames_detect_rois(
            s_input_dir,
            t_input_files,
            oc_rec_cfg,
            s_out_file_prefix,
            b_overwrite_output=True,
            i_max_nframes=None
        )

        pickup_rois_extract_fluo(
            s_input_dir,
            oc_rec_cfg,
            s_out_file_prefix,
            b_overwrite_output=True
        )
        npy2mat(s_input_dir)
#


