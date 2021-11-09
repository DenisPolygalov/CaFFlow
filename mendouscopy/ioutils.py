#!/usr/bin/env python3


import os
import re
import glob
import posixpath
import json
from json.decoder import JSONDecodeError


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

def enum_video_files_dir(target_source, s_wildcard, i_num_pos=-1, b_verbose=False):
    """
    See enum_video_files() for details.
    """
    # target_source = "some_dir8"
    # s_wildcard = "msCam*.avi" or "behavCam*.avi"
    l_file_names = glob.glob(os.path.join(target_source, s_wildcard))
    # l_file_names = ['some_dir8\msCam1.avi', 'some_dir8\msCam10.avi', 'some_dir8\mcCam2.avi', ...]
    l_file_numbers = []
    # l_file_numbers = [1, 10, 2, ...]

    if len(l_file_names) == 0:
        raise OSError("No matching files found in: %s" % target_source)

    for s_fname in l_file_names:
        if not os.path.isfile(s_fname):
            raise OSError("Not a regular file: %s" % s_fname)

        if not os.access(s_fname, os.R_OK):
            raise OSError("Access denied for file: %s" % s_fname)

        fstat_info = os.stat(s_fname)
        if fstat_info.st_size == 0:
            raise OSError("The file is empty: %s" % s_fname)

        # os.path.split(s_fname)[-1] will be only the file name, i.e. 'mcCam2.avi' etc.
        l_numbers_in_fname = re.findall(r'\d+', os.path.split(s_fname)[-1])

        try:
           s_num_pos = l_numbers_in_fname[i_num_pos]
        except IndexError:
            raise IndexError("Wrong number position (%d) for list: %s from file: %s" % (i_num_pos, repr(l_numbers_in_fname), s_fname))

        try:
            l_file_numbers.append(int(s_num_pos))
        except ValueError:
            raise ValueError("Wrong file number: %s" % s_fname)

    # sort numbers in file names
    l_idx = [i[0] for i in sorted(enumerate(l_file_numbers), key=lambda x:x[1])]
    l_sorted_file_names   = [l_file_names[i]   for i in l_idx]
    l_sorted_file_numbers = [l_file_numbers[i] for i in l_idx]

    # calculate difference between adjacent file numbers and check for missing files
    if len(l_sorted_file_numbers) >= 2:
        l_fnum_diff = [j - i for i, j in zip(l_sorted_file_numbers[:-1], l_sorted_file_numbers[1:])]
        if sum(l_fnum_diff) != len(l_fnum_diff):
            raise ValueError("Missing files (holes in numbering) found in: %s" % target_source)

    # another method
    if min(l_sorted_file_numbers) == 0:
        i_nfiles = max(l_sorted_file_numbers) + 1
    elif min(l_sorted_file_numbers) == 1:
        i_nfiles = max(l_sorted_file_numbers)
    else:
        raise ValueError("Unsupported file numbering method")

    if i_nfiles != len(l_sorted_file_names):
        raise ValueError("Missing files (length mismatch) found in: %s" % target_source)

    if b_verbose:
        for i, _ in enumerate(l_file_names):
            print("DEBUG: %s\t%d\t%s" % (l_file_names[i], l_file_numbers[i], l_sorted_file_names[i]))

    return tuple(l_sorted_file_names)
#

def enum_video_files_txt(target_source):
    """
    See enum_video_files() for details.
    """
    if not os.access(target_source, os.R_OK):
        raise OSError("Access denied for file: %s" % target_source)

    l_out_file_names = []
    with open(target_source, 'r') as f:
        for s_fname in f:
            s_fname = s_fname.strip()
            if len(s_fname) == 0: continue
            if s_fname.startswith('#'): continue
            if not os.path.isfile(s_fname): raise OSError("Not a regular file: %s" % s_fname)
            if not os.access(s_fname, os.R_OK): raise OSError("Access denied for file: %s" % s_fname)
            l_out_file_names.append(s_fname)

    if len(l_out_file_names) == 0:
        raise OSError("No input files found in: %s" % target_source)

    return tuple(l_out_file_names)
#

def enum_video_files(target_source, s_wildcard, i_num_pos=-1, b_verbose=False):
    """
    Return a tuple of strings pointed to a set of input *.avi files.
    The 'target_source' can be a path to a directory containing the set,
    or a file name of a text file. The text file then contain a list of
    paths to avi files.
    Example:
    >>> t_files = enum_video_files("H14_M31_S15", "msCam*.avi")
    >>> t_files = enum_video_files("subject_12/4_6_2017/H14_M31_S15", "msCam*.avi")
    >>> t_files = enum_video_files("H14_M31_S15", "behavCam*.avi")
    >>> t_files = enum_video_files("file_list.txt", None)
    Note that no additional sorting will be applied in the case of
    loading from a text file. Files names will be loaded as is
    """
    if os.path.isdir(target_source):
        return enum_video_files_dir(target_source, s_wildcard, i_num_pos=i_num_pos, b_verbose=b_verbose)
    #
    elif os.path.isfile(target_source):
        return enum_video_files_txt(target_source)
    #
    else:
        raise ValueError("Unknown target type: %s" % repr(target_source))
    #
#

def load_Miniscope_json(s_fname: str) -> dict:
    if not os.path.isfile(s_fname):
        raise IOError("Input file is not accessible: %s" % s_fname)
    try:
        with open(s_fname, 'r') as h_file:
            d_json = json.load(h_file)
    except JSONDecodeError as e:
        print("ERROR: unable to decode JSON object generated by Miniscope: %s" % s_fname)
        raise
    except TypeError as e:
        print("ERROR: loaded JSON object is of wrong type: %s" % s_fname)
        raise
    return d_json
#

def load_Miniscope_session(s_rec_ses_dir: str, rec_ses_version=4, b_verbose=False) -> dict:
    if rec_ses_version != 4:
        raise NotImplementedError("Recording session format other than version 4 is not supported")

    # Load content of metaData.json file of the whole recording session.
    d_rses_metaData = load_Miniscope_json(os.path.join(s_rec_ses_dir, "metaData.json"))

    i_nscopes = len(d_rses_metaData['miniscopes'])
    i_ncams = len(d_rses_metaData['cameras'])
    if b_verbose:
        print("INFO: number of Miniscopes found: %i" % i_nscopes)
        print("INFO: number of behavior cameras found: %i" % i_ncams)

    if i_nscopes > 1:
        raise NotImplementedError("Processing of multi-Miniscope recording sessions is not supported")
    if i_ncams > 1:
        raise NotImplementedError("Processing of multi-camera recording sessions is not supported")

    # Load metaData.json of each "miniscope"
    # So it seems like multiple Miniscopes supported...
    for idx, s_ms_dirname in enumerate(d_rses_metaData['miniscopes']):
        d_ms_metaData = load_Miniscope_json(os.path.join(s_rec_ses_dir, s_ms_dirname, "metaData.json"))
        s_path = os.path.join(s_rec_ses_dir, s_ms_dirname)
        d_ms_metaData['dataDirectory'] = s_path.replace(os.sep, posixpath.sep)
        d_rses_metaData['miniscopes'][idx] = d_ms_metaData

    # Load metaData.json of each "camera"
    # A "camera" here is any video source "other than Miniscope"
    for s_cam_dirname in d_rses_metaData['cameras']:
        d_cam_metaData = load_Miniscope_json(os.path.join(s_rec_ses_dir, s_cam_dirname, "metaData.json"))
        s_path = os.path.join(s_rec_ses_dir, s_cam_dirname)
        d_cam_metaData['dataDirectory'] = s_path.replace(os.sep, posixpath.sep)
        d_rses_metaData['cameras'][idx] = d_cam_metaData

    return d_rses_metaData
#
