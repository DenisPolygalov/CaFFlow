#!/usr/bin/env python3


import os
import sys
import configparser

import numpy as np
import matplotlib.pyplot as plt


"""
Copyright (C) 2018-2021 Denis Polygalov,
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


def plot_result(s_input_dir, s_input_ini_file, s_fname_prefix):
    # s_roi_fluo_fname = os.path.join(s_input_dir, s_fname_prefix + "roi_fluo.tiff")
    # oc_fluo_movie = CMuPaMovieTiff((s_roi_fluo_fname,))

    # s_roi_mask_fname = os.path.join(s_input_dir, s_fname_prefix + "roi_mask.tiff")
    # oc_mask_movie = CMuPaMovieTiff((s_roi_mask_fname,))

    s_register_fname = os.path.join(s_input_dir, s_fname_prefix + "register.tiff")
    oc_register_movie = CMuPaMovieTiff((s_register_fname,))

    s_fluo_data_fname = os.path.join(s_input_dir, s_fname_prefix + "fluo.npy")
    d_fluo_data = np.load(s_fluo_data_fname, allow_pickle=True).item()

    for s_key in d_fluo_data.keys():
        DVAR(d_fluo_data[s_key], s_var_name=s_key)

    oc_iproj = None
    i_frame_id = 0
    while(oc_register_movie.read_next_frame()):
        if i_frame_id % 100 == 0: print("%s" % oc_register_movie.get_frame_stat())

        if i_frame_id == 0:
            oc_iproj = CROISpecificIntensityProjector(
                oc_register_movie.na_frame.shape[0], # frame height
                oc_register_movie.na_frame.shape[1], # frame width
                d_fluo_data
            )
        oc_iproj.process_frame(oc_register_movie.na_frame)
        i_frame_id += 1
        # if i_frame_id >= 30: break
    oc_iproj.finalize_projection()

    oc_cmap = plt.cm.jet.copy()
    oc_cmap.set_bad(color='black')
    fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(14,5))
    ax[0].imshow(oc_iproj.d_IPROJ['IPROJ_ROI_fluo_raw'],  cmap=oc_cmap)
    ax[1].imshow(oc_iproj.d_IPROJ['IPROJ_ROI_fluo_max'],  cmap=oc_cmap)
    ax[2].imshow(oc_iproj.d_IPROJ['IPROJ_ROI_fluo_norm'], cmap=oc_cmap)

    ax[0].set_title("ROI fluo (raw)")
    ax[1].set_title("ROI fluo (at dF/F peak)")
    ax[2].set_title("ROI fluo (norm by peak)")

    s_out_fname = os.path.join(s_input_dir, s_fname_prefix + "IPROJ_ROI_fluo.png")
    plt.savefig(s_out_fname, dpi=300, bbox_inches='tight')
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from gui.view import CPerROIDataViewer
    from mendouscopy.mupamovie import CMuPaMovieTiff
    from mendouscopy.iproj import CIntensityProjector
    from mendouscopy.iproj import CROISpecificIntensityProjector

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

        print("INFO: input file: %s" % s_ini_file)
        print("INFO: input file: %s" % s_dst_path)

        s_input_dir = os.path.join(s_work_dir, s_section)
        plot_result(s_input_dir, s_ini_file, s_out_file_prefix)
#


