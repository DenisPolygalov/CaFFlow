#!/usr/bin/env python3


import numpy as np
from scipy.signal import savgol_filter as scipy_savgol_filter
from scipy.stats import iqr as scipy_iqr
from scipy.signal import find_peaks as scipy_find_peaks
from scipy.signal import peak_prominences as scipy_peak_prominences

from .sliding import sliding_window_1d
from .segmentation import find_segments


"""
Copyright (C) 2021 Denis Polygalov,
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


def check_event_peaks_and_spans(na_dFF, na_dFF_evt_peaks, na_dFF_evt_spans):
    _, i_nROIs = na_dFF.shape
    for i_roi_id in range(i_nROIs):
        i_npeaks = na_dFF_evt_peaks[:,i_roi_id].sum()
        na_evt_seg = find_segments(na_dFF_evt_spans[:,i_roi_id], 0.5, 2, b_strict_argcheck=False)
        if i_npeaks != na_evt_seg.shape[0]:
            raise ValueError("number of peaks != number of spans")

        na_peak_idx = np.where(na_dFF_evt_peaks[:,i_roi_id])[0]
        if na_peak_idx.size == 0: continue

        for i_span_id in range(na_evt_seg.shape[0]):
            if na_peak_idx[i_span_id] < na_evt_seg[i_span_id,0] or \
               na_peak_idx[i_span_id] > na_evt_seg[i_span_id,1]:
                   raise ValueError("peak is not inside of the span")
#



def detect_events_by_iqr(na_dFF, na_dFF_evt_peaks, na_dFF_evt_spans, d_param):
    """
    Detect events in the fluorescence traces provided in the na_dFF (Frames x ROIs) matrix.
    The events peaks will be written as ones into output binary matrix na_dFF_evt_peaks,
    events spans will be written as sequence of ones into output binary matrix na_dFF_evt_spans.
    All the matrices have the same shape, but na_dFF_evt_peaks and na_dFF_evt_spans are np.int64
    Events detected by first filtering each trace with Savitzky-Golay filter and threshold
    resulting trace by using threshold calculated as median value of the trace + N times of
    interquartile range of a chunk of the trace calculated in a sliding window.
    Reference papers:
    https://doi.org/10.1126/science.aaf3319
    https://doi.org/10.1016/j.cell.2020.09.024
    """
    f_input_frame_rate_Hz = float(d_param['input_frame_rate'])
    f_flt_width_msec = float(d_param['savgol_filter_width_msec'])
    i_flt_polyorder = int(d_param['savgol_filter_polyorder'])
    f_iqr_detector_thr_n = float(d_param['iqr_detector_ampl_threshold'])
    f_iqr_detector_hsz_sec = float(d_param['iqr_detector_half_width_sec'])

    i_iqr_detector_hsz = int(f_iqr_detector_hsz_sec * f_input_frame_rate_Hz)
    if (i_iqr_detector_hsz % 2) != 0:
        i_iqr_detector_hsz += 1 # make sure the value is even

    i_flt_win_len = int((f_flt_width_msec/1000) * f_input_frame_rate_Hz)
    if (i_flt_win_len % 2) == 0:
        i_flt_win_len += 1 # make sure the value is odd

    if na_dFF.ndim != 2:
        raise ValueError("The na_dFF.ndim must be 2")
    if na_dFF.shape[0] <= (2 * na_dFF.shape[1]):
        raise ValueError("The na_dFF.shape is unrealistic: %s. It must be (dFF_values, ROIs)" % str(na_dFF.shape))

    _, i_nROIs = na_dFF.shape
    for ii in range(i_nROIs):
        na_dFF1d_filtered = scipy_savgol_filter(na_dFF[:,ii], i_flt_win_len, i_flt_polyorder, mode='mirror')
        na_dFF1d_padded = np.pad(na_dFF1d_filtered, (i_iqr_detector_hsz, i_iqr_detector_hsz + 1), 'reflect')
        na_dFF_slided = sliding_window_1d(na_dFF1d_padded, 2 * i_iqr_detector_hsz)
        f_trace_median = np.median(na_dFF1d_filtered)
        na_dFF1d_iqr_thr = f_trace_median + f_iqr_detector_thr_n * scipy_iqr(na_dFF_slided[1:-1], axis=1)
        na_dFF_evt_spans[np.where(na_dFF1d_filtered > na_dFF1d_iqr_thr), ii] = 1

        na_evt_seg = find_segments(na_dFF_evt_spans[:,ii], 0.5, 2, b_strict_argcheck=False)
        i_nseg, _ = na_evt_seg.shape
        for i_seg_idx in range(i_nseg):
            i_beg_idx = na_evt_seg[i_seg_idx,0]
            i_end_idx = na_evt_seg[i_seg_idx,1]
            na_fluo_seg = na_dFF1d_filtered[i_beg_idx:i_end_idx]
            if na_fluo_seg.max() >= f_trace_median:
                na_dFF_evt_peaks[i_beg_idx + np.argmax(na_fluo_seg), ii] = 1

    # check correctness of the content of two output arrays
    check_event_peaks_and_spans(na_dFF, na_dFF_evt_peaks, na_dFF_evt_spans)
#


def detect_events_by_find_peaks(na_dFF, na_dFF_evt_peaks, na_dFF_evt_spans, d_param):
    """
    Detect events in the fluorescence traces provided in the na_dFF (Frames x ROIs) matrix.
    The events peaks will be written as ones into output binary matrix na_dFF_evt_peaks,
    events spans will be written as sequence of ones into output binary matrix na_dFF_evt_spans.
    All the matrices have the same shape, but na_dFF_evt_peaks and na_dFF_evt_spans are np.int64
    Events detected by first filtering each trace with Savitzky-Golay filter.
    Peaks in the filtered trace then detected by using scipy.signal.find_peaks() function:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html
    For each detected peak it's "prominence" (span) calculated then by using:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html
    Reference paper in which *similar* algorithm was used:
    https://doi.org/10.1016/j.neuron.2018.01.016
    """
    f_input_frame_rate_Hz = float(d_param['input_frame_rate'])
    f_flt_width_msec = float(d_param['savgol_filter_width_msec'])
    i_flt_polyorder = int(d_param['savgol_filter_polyorder'])
    f_fp_distance_sec = float(d_param['find_peaks_distance_sec'])
    i_fp_distance = int(f_fp_distance_sec * f_input_frame_rate_Hz)
    f_fp_prominence_nstd = float(d_param['find_peaks_prominence_nstd'])
    f_fp_wlen_msec = float(d_param['find_peaks_wlen_msec'])

    i_fp_wlen = int((f_fp_wlen_msec/1000) * f_input_frame_rate_Hz)
    i_flt_win_len = int((f_flt_width_msec/1000) * f_input_frame_rate_Hz)
    if (i_flt_win_len % 2) == 0:
        i_flt_win_len += 1 # make sure the value is odd

    if na_dFF.ndim != 2:
        raise ValueError("The na_dFF.ndim must be 2")
    if na_dFF.shape[0] <= (2 * na_dFF.shape[1]):
        raise ValueError("The na_dFF.shape is unrealistic: %s. It must be (dFF_values, ROIs)" % str(na_dFF.shape))

    _, i_nROIs = na_dFF.shape
    for ii in range(i_nROIs):
        na_dFF1d_filtered = scipy_savgol_filter(na_dFF[:,ii], i_flt_win_len, i_flt_polyorder, mode='mirror')
        f_prominence = f_fp_prominence_nstd * np.std(na_dFF1d_filtered)
        na_peak_idx, _ = scipy_find_peaks(na_dFF1d_filtered, distance=i_fp_distance, prominence=f_prominence)
        # filter peaks by amplitude: remove all peaks where peaks's
        # amplitude is less than median value of the whole trace
        na_peak_vals = na_dFF[na_peak_idx,ii]
        f_trace_median = np.median(na_dFF[:,ii])
        na_peak_idx = na_peak_idx[np.where(na_peak_vals >= f_trace_median)]
        # embed peak's indices into the output array
        na_dFF_evt_peaks[na_peak_idx, ii] = 1

        na_Promi, na_Lbases, na_Rbases = scipy_peak_prominences(na_dFF1d_filtered, na_peak_idx, wlen=i_fp_wlen)
        for i_pk_idx in range(na_Promi.size):
            na_dFF_evt_spans[na_Lbases[i_pk_idx]:na_Rbases[i_pk_idx], ii] = 1

    # check correctness of the content of two output arrays
    check_event_peaks_and_spans(na_dFF, na_dFF_evt_peaks, na_dFF_evt_spans)
#

