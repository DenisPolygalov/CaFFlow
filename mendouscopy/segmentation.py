#!/usr/bin/env python3


import numpy as np


"""
Copyright (C) 2020 Denis Polygalov,
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


def find_segments(na_x, f_thr_amp, i_thr_len, b_strict_argcheck=True):
    """
    Return M x 2 matrix of INDICES of input vector na_x, where values of na_x
    are equal or above than the amplitude threshold value 'f_thr_amp' AND
    longer or equal than the length threshold 'i_thr_len' value.
    The 'i_thr_len' value must be specified in number of elements
    of na_x starting from 1: (1,2,3,4, ... na_x.size - 1).
    """
    if na_x.ndim > 2:
        raise ValueError("Input data must be a vector")

    if na_x.ndim == 2 and na_x.shape[0] > 1 and na_x.shape[1] > 1:
        raise ValueError("Input data must be a vector")

    if np.any(np.iscomplex(na_x)):
        raise ValueError("Input data must be vector of real values")

    if not np.isscalar(f_thr_amp):
        raise ValueError("f_thr_amp must be a scalar")

    if not np.isscalar(i_thr_len):
        raise ValueError("i_thr_len must be a scalar")

    f_thr_amp = float(f_thr_amp)
    i_thr_len = int(i_thr_len)

    if np.count_nonzero(na_x > f_thr_amp) == 0:
        if b_strict_argcheck:
            raise ValueError("Amplitude threshold (f_thr_amp) is too high")
        return np.array([], dtype=np.int64).reshape(0,2)

    if np.count_nonzero(na_x < f_thr_amp) == 0:
        if b_strict_argcheck:
            raise ValueError("Amplitude threshold (f_thr_amp) is too low")
        return np.array([], dtype=np.int64).reshape(0,2)

    if i_thr_len < 1:
        raise ValueError("Length threshold (i_thr_len) is too short (less than 1)")

    if i_thr_len >= na_x.size:
        raise ValueError("Length threshold (i_thr_len) is too long (longer than na_x.size)")

    # special case when thr_amp is exactly equal to min(X)
    if np.count_nonzero(na_x >= f_thr_amp) == na_x.size:
        return np.array([0, na_x.size]).reshape(1,2)

    # filter X by amplitude
    na_dx = np.diff( (na_x >= f_thr_amp).astype(np.int64) )

    if na_x[0] <= f_thr_amp and na_x[-1] <= f_thr_amp:  # 0 0 1 1 1 1 0 0
        # begs = find(d_X > 0) + 1;
        begs = np.where(na_dx > 0)[0] + 1
        # ends = find(d_X < 0);
        ends = np.where(na_dx < 0)[0] + 1

    elif na_x[0] > f_thr_amp and na_x[-1] > f_thr_amp:  # 1 1 0 0 0 0 1 1
        # begs = [1; find(d_X > 0) + 1];
        begs = np.where(na_dx > 0)[0] + 1
        begs = np.insert(begs, 0, 0)
        # ends = [find(d_X < 0); length(X)];
        ends = np.where(na_dx < 0)[0] + 1
        ends = np.insert(ends, ends.size, ends.size-1)

    elif na_x[0] > f_thr_amp and na_x[-1] <= f_thr_amp: # 1 1 0 1 1 0 0 0
        # begs = [1; find(d_X > 0) + 1];
        begs = np.where(na_dx > 0)[0] + 1
        begs = np.insert(begs, 0, 0)
        # ends = find(d_X < 0);
        ends = np.where(na_dx < 0)[0] + 1

    elif na_x[0] <= f_thr_amp and na_x[-1] > f_thr_amp: # 0 0 0 1 1 0 1 1
        # begs = find(d_X > 0) + 1;
        begs = np.where(na_dx > 0)[0] + 1
        # ends = [find(d_X < 0); length(X)];
        ends = np.where(na_dx < 0)[0] + 1
        ends = np.insert(ends, ends.size, ends.size-1)
    else:
        raise ValueError('algorithm error (1)'); # should never happen

    if begs.size != ends.size:
        raise ValueError("algorithm error (2)")

    # filter segments by length (remove short segments)
    # d_I = (ends - begs + 1) >= thr_len;
    # S = [begs(d_I), ends(d_I)];
    d_I = np.where(ends - begs + 1 >= i_thr_len)
    return np.transpose(np.stack((begs[d_I], ends[d_I])))
#

