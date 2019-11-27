#!/usr/bin/env python3


import os
import sys
import configparser


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


def plot_result(s_input_dir, s_fname_prefix):
    s_fluo_data_in_fname = os.path.join(s_input_dir, s_fname_prefix + "fluo.npy")
    d_fluo_data = np.load(s_fluo_data_in_fname, allow_pickle=True).item()

    print("Input data file:\t%s" % s_fluo_data_in_fname)
    for s_key in d_fluo_data.keys():
        DVAR(d_fluo_data[s_key], s_var_name=s_key)

    f_vert_shift = 0
    i_nrois_collected = len(d_fluo_data['ROI_data'])
    na_fluo_dFF = d_fluo_data['dFF']

    plt.subplot(121)
    plt.imshow(d_fluo_data['ROI_mask'])

    plt.subplot(122)
    for ii in range(i_nrois_collected):
        plt.plot(na_fluo_dFF[...,ii] + f_vert_shift)
        f_vert_shift += np.abs(na_fluo_dFF[...,ii].max() - na_fluo_dFF[...,ii].min())
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from mendouscopy.pipelines import register_frames_detect_rois
    from mendouscopy.pipelines import pickup_rois_extract_fluo
    import numpy as np
    import matplotlib.pyplot as plt

    # load global configuration file
    oc_global_cfg = configparser.ConfigParser()
    oc_global_cfg.read('examples.ini')

    # extract path to example recording session and it's configuration file
    s_input_dir = "."
    t_input_files = ("CW2003_H14_M57_S54_msCam1_frame0to99.tiff",) # notice comma(!)
    s_out_fname_prefix = "ms_"

    # load local configuration file
    oc_rec_cfg = configparser.ConfigParser()
    oc_rec_cfg.read("CW2003_H14_M57_S54_msCam1_frame0to99.ini")

    register_frames_detect_rois(
        s_input_dir,
        t_input_files,
        oc_rec_cfg,
        s_out_fname_prefix,
        b_overwrite_output=True,
        i_max_nframes=None
    )

    pickup_rois_extract_fluo(
        s_input_dir,
        oc_rec_cfg,
        s_out_fname_prefix,
        b_overwrite_output=True
    )

    plot_result(s_input_dir, s_out_fname_prefix)
#
