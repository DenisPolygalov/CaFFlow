#!/usr/bin/env python3


import cv2 as cv
import numpy as np
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec


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


class CSimpleDataViewer(object):
    def __init__(self, d_fluo_data):
        self.l_lines_all = []
        self.l_lines_picked = []
        self.l_edges = []
        self.f_rect_sz = 15
        self.f_rect_hsz = self.f_rect_sz/2
        self.oc_fig, self.na_axes = plt.subplots(1, 2, figsize=(14,8))

        self.na_ROI_mask = d_fluo_data['ROI_mask']

        self.na_ROI_mask_f32 = self.na_ROI_mask.copy().astype(np.float32)
        self.na_ROI_mask_f32[np.where(self.na_ROI_mask_f32 == 0)] = np.nan

        na_dFF = d_fluo_data['dFF']
        self.i_nframes, self.i_nROIs = na_dFF.shape

        self.na_ROIxy = np.zeros([self.i_nROIs,2], dtype=np.float32)
        for ii in range(self.i_nROIs):
            self.na_ROIxy[ii,0] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][0] - self.f_rect_hsz
            self.na_ROIxy[ii,1] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][1] - self.f_rect_hsz

        t_xy = (self.na_ROIxy[0,1], self.na_ROIxy[0,0])
        self.oc_rect = patches.Rectangle(t_xy, self.f_rect_sz, self.f_rect_sz, linewidth=2, edgecolor='k', facecolor='none')
        self.na_axes[0].imshow(self.na_ROI_mask_f32, cmap=cm.jet)
        self.na_axes[0].set_aspect('equal', 'box')
        self.na_axes[0].add_patch(self.oc_rect)

        f_vert_shift = 0.0
        self.l_edges.append(f_vert_shift)

        for ii in range(self.i_nROIs):
            l_tmp = self.na_axes[1].plot(na_dFF[...,ii] + f_vert_shift, 'b', pickradius=5)
            self.l_lines_all.append(l_tmp[0])
            f_vert_shift += np.abs(na_dFF[...,ii].max() - na_dFF[...,ii].min())
            self.l_edges.append(f_vert_shift)
        self.na_axes[1].get_yaxis().set_visible(False)
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
            if self.na_ROI_mask[i_row, i_col] > 0:
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


class CPerROIDataViewer(object):
    def __init__(self, d_fluo_data, event_peaks=None, event_spans=None, snr_threshold=3):
        (self.s_major_ver, self.s_minor_ver, self.s_subminor_ver) = (cv.__version__).split('.')
        self.f_snr_threshold = snr_threshold
        self.b_draw_thr_rois = False
        self.f_rect_sz = 15
        self.f_rect_hsz = self.f_rect_sz/2
        self.oc_fig = plt.figure(figsize=(14,8))
        oc_gspec = GridSpec(2, 2, height_ratios=[3, 1], figure=self.oc_fig)
        self.na_axes = np.zeros([2,2], dtype=object)
        self.na_axes[0,0] = self.oc_fig.add_subplot(oc_gspec[0,0])
        self.na_axes[0,1] = self.oc_fig.add_subplot(oc_gspec[0,1], sharex=self.na_axes[0,0], sharey=self.na_axes[0,0])
        self.na_axes[1,0] = self.oc_fig.add_subplot(oc_gspec[1,:])

        self.na_IPROJ_fet = d_fluo_data['IPROJ_fet']
        self.na_IPROJ_max = d_fluo_data['IPROJ_max']
        self.na_IPROJ_std = d_fluo_data['IPROJ_std']
        self.na_ROI_mask = d_fluo_data['ROI_mask']
        self.na_dFF = d_fluo_data['dFF']
        self.na_dFF_SNR = d_fluo_data['dFF_SNR']
        self.i_nframes, self.i_nROIs = self.na_dFF.shape

        self.i_bgr_id = 0 # current background image id
        self.i_numbgr = 3 # number of background images (IPROJ_max, IPROJ_fet, etc).

        self.na_event_peaks = None
        self.na_event_spans = None

        # note that self.na_ROIxy is not a center of the ROI, but shifted self.f_rect_hsz pixels!
        self.na_ROIxy = np.zeros([self.i_nROIs,2], dtype=np.float32)
        for ii in range(self.i_nROIs):
            self.na_ROIxy[ii,0] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][0] - self.f_rect_hsz
            self.na_ROIxy[ii,1] = d_fluo_data['ROI_data'][ii]['ROI_CoidXY'][1] - self.f_rect_hsz

        self.na_ROI_contours = np.zeros_like(self.na_ROI_mask, dtype=self.na_ROI_mask.dtype)
        self.convert_ROI_mask2contours()
        self.na_ROI_filled_mask = np.zeros_like(self.na_ROI_mask, dtype=self.na_ROI_mask.dtype)
        self.na_ROI_thresh_mask = np.zeros_like(self.na_ROI_mask, dtype=self.na_ROI_mask.dtype)
        self.convert_ROI_mask2filled_mask()

        t_xy = (self.na_ROIxy[0,1], self.na_ROIxy[0,0])
        self.oc_rect_l = patches.Rectangle(t_xy, self.f_rect_sz, self.f_rect_sz, linewidth=2, edgecolor='orange', facecolor='none')
        self.oc_rect_r = patches.Rectangle(t_xy, self.f_rect_sz, self.f_rect_sz, linewidth=2, edgecolor='orange', facecolor='none')

        self.na_axes[0,0].imshow(self.na_IPROJ_fet, cmap=cm.gray, alpha=1.0)
        self.na_axes[0,0].imshow(self.na_ROI_filled_mask, cmap=cm.coolwarm, alpha=0.5)
        self.na_axes[0,0].set_aspect('equal', 'box')
        self.na_axes[0,0].add_patch(self.oc_rect_l)
        self.na_axes[0,0].set_title("local")

        self.na_axes[0,1].imshow(self.na_IPROJ_fet, cmap=cm.jet, alpha=1.0)
        self.na_axes[0,1].set_aspect('equal', 'box')
        self.na_axes[0,1].add_patch(self.oc_rect_r)
        self.na_axes[0,1].set_title("local")

        self.na_axes[1,0].plot(self.na_dFF[...,0], 'b', pickradius=5)
        self.na_axes[1,0].hlines(np.median(self.na_dFF[:,0]), 0, self.na_dFF.shape[0], colors='b', linestyles='dashed')

        if type(event_peaks) is np.ndarray:
            if event_peaks.ndim != 2:
                raise ValueError("The event_peaks array must be 2D array")
            if self.na_dFF.shape[0] != event_peaks.shape[0] or self.na_dFF.shape[1] != event_peaks.shape[1]:
                raise ValueError("Shapes of dFF array and event_peaks array must be the same")
            self.na_event_peaks = event_peaks
            na_epeak_idx = np.where(self.na_event_peaks[:,0])[0]
            self.na_axes[1,0].plot(na_epeak_idx, self.na_dFF[na_epeak_idx,0], 'ro')

        if type(event_spans) is np.ndarray:
            if event_spans.ndim != 2:
                raise ValueError("The event_spans array must be 2D array")
            if self.na_dFF.shape[0] != event_spans.shape[0] or self.na_dFF.shape[1] != event_spans.shape[1]:
                raise ValueError("Shapes of dFF array and event_spans array must be the same")
            self.na_event_spans = event_spans
            na_espan_idx = np.where(self.na_event_spans[:,0])[0]
            na_event_ymax = self.na_dFF[na_espan_idx,0]
            na_event_ymin = np.zeros_like(na_event_ymax)
            self.na_axes[1,0].vlines(na_espan_idx, na_event_ymin, na_event_ymax, 'm')

        self.na_axes[1,0].set_xlim(0, self.i_nframes)
        self.na_axes[1,0].set_ylim(-5, 1.05 * self.na_dFF.max())
        plt.tight_layout()
    #
    def connect(self):
        # Return value is a connection id that can be used with mpl_disconnect()
        self.i_btn_conn_id = self.oc_fig.canvas.mpl_connect('button_press_event', self.__cb_on_click)
        self.i_key_conn_id = self.oc_fig.canvas.mpl_connect('key_press_event', self.__cb_on_key_press)
    #
    def convert_ROI_mask2contours(self):
        i_nROIs = self.na_ROI_mask.max()
        na_canvas = np.zeros(self.na_ROI_mask.shape, dtype=np.uint8)
        for i_roi_id in range(i_nROIs):
            na_canvas[np.where(self.na_ROI_mask == (i_roi_id + 1))] = i_roi_id + 1
            if self.s_major_ver == '3':
                _, l_contours, _ = cv.findContours(na_canvas, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
            elif self.s_major_ver == '4':
                l_contours, _ = cv.findContours(na_canvas, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
            else:
                warnings.warn("Unexpected OpenCV version. Go ahead as with 4.x but things might become slippery...")
                l_contours, _ = cv.findContours(na_canvas, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

            cv.drawContours(self.na_ROI_contours, l_contours, len(l_contours)-1, (1,0,0), 2)
            na_canvas.fill(0)
    #
    def convert_ROI_mask2filled_mask(self):
        self.na_ROI_filled_mask[...] = self.na_ROI_mask[...]
        self.na_ROI_filled_mask[np.where(self.na_ROI_mask > 0)] = 1
        for i_roi_id in range(self.i_nROIs):
            i_ROI_CoM_x = int(self.na_ROIxy[i_roi_id,1] + self.f_rect_hsz)
            i_ROI_CoM_y = int(self.na_ROIxy[i_roi_id,0] + self.f_rect_hsz)
            self.na_ROI_filled_mask[i_ROI_CoM_y, i_ROI_CoM_x] = 2

        na_over_thr_mask = self.na_ROI_mask.copy()
        i_discarded_roi_cnt = 0
        for ii in range(self.i_nROIs):
            i_roi_id = ii + 1
            if self.na_dFF_SNR[ii] <= self.f_snr_threshold:
                print("Threshold ROI: id=%i SNR=%.4f (discarded)" % (i_roi_id, self.na_dFF_SNR[ii]))
                na_over_thr_mask[na_over_thr_mask == (i_roi_id)] = 0
                i_discarded_roi_cnt += 1
            else:
                print("Threshold ROI: id=%i SNR=%.4f" % (i_roi_id, self.na_dFF_SNR[ii]))
        self.na_ROI_thresh_mask[na_over_thr_mask > 0] = 1
        print("Discarded %i ROI out of %i" % (i_discarded_roi_cnt, self.i_nROIs))

        for i_roi_id in range(self.i_nROIs):
            if self.na_dFF_SNR[i_roi_id] <= self.f_snr_threshold: continue
            i_ROI_CoM_x = int(self.na_ROIxy[i_roi_id,1] + self.f_rect_hsz)
            i_ROI_CoM_y = int(self.na_ROIxy[i_roi_id,0] + self.f_rect_hsz)
            self.na_ROI_thresh_mask[i_ROI_CoM_y, i_ROI_CoM_x] = 2
    #
    def select_ROI(self, i_ROI_idx):
        if i_ROI_idx < 0: return
        f_x = self.na_ROIxy[i_ROI_idx,1]
        f_y = self.na_ROIxy[i_ROI_idx,0]
        self.oc_rect_l.xy = (f_x, f_y)
        self.oc_rect_r.xy = (f_x, f_y)
    #
    def get_ROI_idx(self, f_x, f_y):
        i_ret = -1
        i_col = int(f_x + 0.5)
        i_row = int(f_y + 0.5)
        if i_col >= 0 and i_col < self.na_ROI_mask.shape[1] and i_row >= 0 and i_row < self.na_ROI_mask.shape[0]:
            if self.na_ROI_mask[i_row, i_col] > 0:
                i_ret = self.na_ROI_mask[i_row, i_col] - 1
        return i_ret
    #
    def plot_dFF_trace(self, i_trace_idx):
        self.na_axes[1,0].clear()
        self.na_axes[1,0].plot(self.na_dFF[...,i_trace_idx], 'b', pickradius=5)
        self.na_axes[1,0].hlines(np.median(self.na_dFF[:,i_trace_idx]), 0, self.na_dFF.shape[0], colors='b', linestyles='dashed')

        if type(self.na_event_peaks) is np.ndarray:
            na_epeak_idx = np.where(self.na_event_peaks[:,i_trace_idx])[0]
            self.na_axes[1,0].plot(na_epeak_idx, self.na_dFF[na_epeak_idx, i_trace_idx], 'ro')

        if type(self.na_event_spans) is np.ndarray:
            na_espan_idx = np.where(self.na_event_spans[:,i_trace_idx])[0]
            na_event_ymax = self.na_dFF[na_espan_idx, i_trace_idx]
            na_event_ymin = np.zeros_like(na_event_ymax)
            self.na_axes[1,0].vlines(na_espan_idx, na_event_ymin, na_event_ymax, 'm')

        self.na_axes[1,0].set_xlim(0, self.i_nframes)
        self.na_axes[1,0].set_ylim(-5, 1.05 * self.na_dFF.max())
        self.na_axes[1,0].draw_artist(self.na_axes[1,0].lines[0])
    #
    def __cb_on_click(self, event):
        if not event.xdata or not event.ydata: return
        i_idx = -1
        if event.inaxes == self.na_axes[0,0] or event.inaxes == self.na_axes[0,1]:
            i_idx = self.get_ROI_idx(event.xdata, event.ydata)
            if i_idx < 0: return
        else:
            return
        self.select_ROI(i_idx)
        self.plot_dFF_trace(i_idx)
        self.oc_fig.canvas.draw_idle()
        print("ROI: id=%i SNR=%.4f" % (i_idx+1, self.na_dFF_SNR[i_idx]))
    #
    def __cb_on_key_press(self, event):
        if event.key == 'b':
            self.i_bgr_id += 1
            if self.i_bgr_id >= self.i_numbgr:
                self.i_bgr_id = 0

            if self.i_bgr_id == 0:
                self.na_axes[0,0].imshow(self.na_IPROJ_fet, cmap=cm.gray, alpha=1.0)
                if self.b_draw_thr_rois:
                    self.na_axes[0,0].imshow(self.na_ROI_thresh_mask, cmap=cm.coolwarm, alpha=0.5)
                else:
                    self.na_axes[0,0].imshow(self.na_ROI_filled_mask, cmap=cm.coolwarm, alpha=0.5)
                self.na_axes[0,0].set_title("local")
                self.na_axes[0,1].imshow(self.na_IPROJ_fet, cmap=cm.jet, alpha=1.0)
                self.na_axes[0,1].set_title("local")

            elif self.i_bgr_id == 1:
                self.na_axes[0,0].imshow(self.na_IPROJ_max, cmap=cm.gray, alpha=1.0)
                if self.b_draw_thr_rois:
                    self.na_axes[0,0].imshow(self.na_ROI_thresh_mask, cmap=cm.coolwarm, alpha=0.5)
                else:
                    self.na_axes[0,0].imshow(self.na_ROI_filled_mask, cmap=cm.coolwarm, alpha=0.5)
                self.na_axes[0,0].set_title("maximum")
                self.na_axes[0,1].imshow(self.na_IPROJ_max, cmap=cm.jet, alpha=1.0)
                self.na_axes[0,1].set_title("maximum")

            elif self.i_bgr_id == 2:
                self.na_axes[0,0].imshow(self.na_IPROJ_std, cmap=cm.gray, alpha=1.0)
                if self.b_draw_thr_rois:
                    self.na_axes[0,0].imshow(self.na_ROI_thresh_mask, cmap=cm.coolwarm, alpha=0.5)
                else:
                    self.na_axes[0,0].imshow(self.na_ROI_filled_mask, cmap=cm.coolwarm, alpha=0.5)
                self.na_axes[0,0].set_title("std")
                self.na_axes[0,1].imshow(self.na_IPROJ_std, cmap=cm.jet, alpha=1.0)
                self.na_axes[0,1].set_title("std")
            else:
                pass
            self.oc_fig.canvas.draw_idle()

        if event.key == 't':
            if self.b_draw_thr_rois:
                self.b_draw_thr_rois = False
                if self.i_bgr_id == 0:
                    self.na_axes[0,0].imshow(self.na_IPROJ_fet, cmap=cm.gray, alpha=1.0)
                elif self.i_bgr_id == 1:
                    self.na_axes[0,0].imshow(self.na_IPROJ_max, cmap=cm.gray, alpha=1.0)
                elif self.i_bgr_id == 2:
                    self.na_axes[0,0].imshow(self.na_IPROJ_std, cmap=cm.gray, alpha=1.0)

                self.na_axes[0,0].imshow(self.na_ROI_filled_mask, cmap=cm.coolwarm, alpha=0.5)
                self.na_axes[0,0].set_aspect('equal', 'box')
                self.na_axes[0,0].add_patch(self.oc_rect_l)
            else:
                self.b_draw_thr_rois = True
                if self.i_bgr_id == 0:
                    self.na_axes[0,0].imshow(self.na_IPROJ_fet, cmap=cm.gray, alpha=1.0)
                elif self.i_bgr_id == 1:
                    self.na_axes[0,0].imshow(self.na_IPROJ_max, cmap=cm.gray, alpha=1.0)
                elif self.i_bgr_id == 2:
                    self.na_axes[0,0].imshow(self.na_IPROJ_std, cmap=cm.gray, alpha=1.0)

                self.na_axes[0,0].imshow(self.na_ROI_thresh_mask, cmap=cm.coolwarm, alpha=0.5)
                self.na_axes[0,0].set_aspect('equal', 'box')
                self.na_axes[0,0].add_patch(self.oc_rect_l)
            self.oc_fig.canvas.draw_idle()
    #
#

