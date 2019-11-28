#!/usr/bin/env python3


import os
import sys
import configparser

import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.patches as patches


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


class CSimpleDataViewer(object):
    def __init__(self, d_fluo_data):
        self.l_lines_all = []
        self.l_lines_picked = []
        self.l_edges = []
        self.f_rect_sz = 15
        self.f_rect_hsz = self.f_rect_sz/2
        self.oc_fig, self.na_axes = plt.subplots(1,2,figsize=(15, 10))

        self.na_ROI_mask = d_fluo_data['ROI_mask']

        self.na_ROI_mask_f32 = self.na_ROI_mask.copy().astype(np.float32)
        self.na_ROI_mask_f32[np.where(self.na_ROI_mask_f32 == 0)] = np.nan

        na_dFF = d_fluo_data['dFF']
        self.i_nframes, self.i_nROIs = na_dFF.shape

        self.na_ROIxy = np.zeros([self.i_nROIs,2], dtype=np.float32)
        for ii in range(self.i_nROIs):
            self.na_ROIxy[ii,0] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][0] - self.f_rect_hsz
            self.na_ROIxy[ii,1] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][1] - self.f_rect_hsz

        self.na_axes[0].imshow(self.na_ROI_mask_f32, cmap=cm.jet)
        self.na_axes[0].set_aspect('equal', 'box')
        t_xy = (self.na_ROIxy[0,1], self.na_ROIxy[0,0])
        self.oc_rect = patches.Rectangle(t_xy, self.f_rect_sz, self.f_rect_sz, linewidth=2, edgecolor='k', facecolor='none')
        self.na_axes[0].add_patch(self.oc_rect)

        f_vert_shift = 0.0
        self.l_edges.append(f_vert_shift)

        for ii in range(self.i_nROIs):
            l_tmp = self.na_axes[1].plot(na_dFF[...,ii] + f_vert_shift, 'b', pickradius=5)
            self.l_lines_all.append(l_tmp[0])
            f_vert_shift += np.abs(na_dFF[...,ii].max() - na_dFF[...,ii].min())
            self.l_edges.append(f_vert_shift)
        self.na_axes[1].get_yaxis().set_visible(False)

        self.connect()
        plt.tight_layout()
    #
    def connect(self):
        # Return value is a connection id that can be used with mpl_disconnect()
        self.i_conn_id = self.oc_fig.canvas.mpl_connect('button_press_event', self.__cb_on_click)
    #
    def select_ROI(self, i_ROI_idx):
        if i_ROI_idx < 0: return
        f_x = self.na_ROIxy[i_ROI_idx,1]
        f_y = self.na_ROIxy[i_ROI_idx,0]
        self.oc_rect.xy = (f_x, f_y)
    #
    def get_ROI_idx(self, f_x, f_y):
        i_ret = -1
        i_col = int(f_x + 0.5)
        i_row = int(f_y + 0.5)
        if i_col >= 0 and i_col < self.na_ROI_mask.shape[1] and i_row >= 0 and i_row < self.na_ROI_mask.shape[0]:
            i_ret = self.na_ROI_mask[i_row, i_col] - 1
        return i_ret
    #
    def select_line(self, i_line_idx):
        if i_line_idx < 0: return
        for ii in self.l_lines_picked:
            self.l_lines_all[ii].set_color("blue")
            self.na_axes[1].draw_artist(self.l_lines_all[ii])
        self.l_lines_picked.clear()

        self.l_lines_all[i_line_idx].set_color("red")
        self.l_lines_picked.append(i_line_idx)
        self.na_axes[1].draw_artist(self.l_lines_all[i_line_idx])
    #
    def __cb_on_click(self, event):
        if not event.xdata or not event.ydata: return
        i_idx = -1
        if event.inaxes == self.na_axes[0]:
            i_idx = self.get_ROI_idx(event.xdata, event.ydata)
        elif event.inaxes == self.na_axes[1]:
            # search for index in self.l_edges closest to the event.ydata
            l_tmp = [abs(ii - event.ydata) for ii in self.l_edges]
            i_idx = l_tmp.index(min(l_tmp))
            if i_idx >= len(self.l_lines_all):
                i_idx = len(self.l_lines_all) - 1
        else:
            return
        self.select_ROI(i_idx)
        self.select_line(i_idx)
        self.oc_fig.canvas.draw_idle()
    #
#


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

    print("Input data file:\t%s" % s_fluo_data_in_fname)
    for s_key in d_fluo_data.keys():
        DVAR(d_fluo_data[s_key], s_var_name=s_key)

    CSimpleDataViewer(d_fluo_data)
    plt.savefig(s_out_fname, dpi=300, quality=100, bbox_inches='tight')
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR

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


