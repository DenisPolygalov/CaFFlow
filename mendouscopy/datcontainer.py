#!/usr/bin/env python3


import os
import sys
import json
import numpy as np


"""
Copyright (C) 2018-2020 Lilia Evgeniou, Denis Polygalov,
Laboratory for Circuit and Behavioral Physiology,
RIKEN Center for Brain Science, Saitama, Japan.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, a copy is available at
http://www.fsf.org/
"""


class CDatContainer(object):
    def __init__(self, s_target_dir):
        self.s_target_dir = s_target_dir
        self.d_DAT = {}
        self.d_DAT['target_dir'] = self.s_target_dir
        self.d_DAT['camNum'] = []
        self.d_DAT['frameNum'] = []
        self.d_DAT['sysClock'] = []
        self.d_DAT['buffer'] = []

        s_sett_fname = os.path.join(self.s_target_dir, "settings_and_notes.dat")
        if os.path.isfile(s_sett_fname):
            self.d_DAT.update(self.__load_settings_and_notes(s_sett_fname))
        else:
            s_sett_fname = os.path.join(self.s_target_dir, "rec_info.json")
            if os.path.isfile(s_sett_fname):
                self.d_DAT.update(self.__load_rec_info(s_sett_fname))
            else:
                raise ValueError("Unable to find any settings or recording information file")

        # parsing timestamp.dat file
        s_ts_fname = os.path.join(self.s_target_dir, "timestamp.dat")

        with open(file=s_ts_fname, mode="r") as h_files:

            for idx, s_line in enumerate(h_files):
                s_line = s_line.strip()
                if s_line == '': continue

                # check that all lines are 4 tokens separated by tabs
                l_tokens = s_line.split('\t')
                if len(l_tokens) != 4:
                    raise ValueError("Unexpected file format in file %s at line %s: %s" % (s_ts_fname, idx, s_line))

                # check that first line is:
                # "camNum\tframeNum\tsysClock\tbuffer\n"
                if idx == 0:
                    if s_line != "camNum\tframeNum\tsysClock\tbuffer":
                        raise ValueError("Unexpected file format in file %s at line 0: %s" % (s_ts_fname, s_line))
                    else:
                        continue  # We know that this is the correct file, with the correct column names

                # check that after the first line, all lines are 4 integers and add them to appropriate lists
                try:
                    self.d_DAT['camNum'].append(int(l_tokens[0]))
                    self.d_DAT['frameNum'].append(int(l_tokens[1]))
                    self.d_DAT['sysClock'].append(int(l_tokens[2]))
                    self.d_DAT['buffer'].append(int(l_tokens[3]))
                except ValueError:
                    raise ValueError("Unexpected file format in file %s at line %s: %s" % (s_ts_fname, idx, s_line))

        self.d_DAT['camNum']   = np.array(self.d_DAT['camNum'],   dtype=np.int64)
        self.d_DAT['frameNum'] = np.array(self.d_DAT['frameNum'], dtype=np.int64)
        self.d_DAT['sysClock'] = np.array(self.d_DAT['sysClock'], dtype=np.int64)
        self.d_DAT['buffer']   = np.array(self.d_DAT['buffer'],   dtype=np.int64)

    def __load_settings_and_notes(self, s_sett_fname):
        # parsing settings_and_notes.dat file
        # this method will either return valid dictionary or raise exception

        # make a list of lists: list of "\t"-separated strings in a line; 4 lines in larger list
        with open(s_sett_fname) as h_file:
            l_tmp = h_file.read().splitlines()
        l_settings_and_notes = [s_line.split("\t") for s_line in l_tmp]

        # [['animal', 'excitation', 'msCamExposure', 'recordLength'],
        #  ['name', '60', '255', '0'],
        #  ['behav_ROI_x', 'behav_ROI_y', 'behav_ROI_w', 'behav_ROI_h'],
        #  ['8', '242', '624', '101'],
        #  ['elapsedTime', 'Note']]

        if len(l_settings_and_notes) < 4:
            raise ValueError("Unexpected file format: %s" % repr(l_settings_and_notes))

        # keys of d_DAT dictionary from first line
        l_param_keys = l_settings_and_notes[0]
        # items of d_DAT dictionary from second line (changes numeric values to integers)
        l_param_items = [int(item) if item.isnumeric() else item for item in l_settings_and_notes[1]]

        # dictionary with l_param_keys as keys corresponding to the l_param_items as the items (with same index)
        d_sett = {key:l_param_items[item] for item, key in enumerate(l_param_keys)}

        # keys of d_behav_ROI
        l_behav_ROI_keys = ["bhv_roi_x", "bhv_roi_y", "bhv_roi_w", "bhv_roi_h"]
        # items of d_behav_ROI from fourth line
        l_behav_ROI_items = [int(item) for item in l_settings_and_notes[3]]

        # dictionary with l_behav_ROI_keys as keys corresponding to the l_behav_ROI_items as the items (with same index)
        d_behav_ROI = {key: l_behav_ROI_items[item] for item, key in enumerate(l_behav_ROI_keys)}
        d_sett.update(d_behav_ROI)
        return d_sett

    def __load_rec_info(self, s_sett_fname):
        # parsing rec_info.json file
        # this method will either return valid dictionary or raise exception
        with open(s_sett_fname) as json_file:
            data = json.load(json_file)
            if not isinstance(data, dict):
                raise ValueError("Unexpected file format: %s" % s_sett_fname)
            for i_idx, vstream in enumerate(data['VSTREAM_LIST']):
                if vstream is None:
                    data['VSTREAM_LIST'][i_idx] = np.nan
            return data
#

if __name__ == '__main__':
    # check if argument passed by user
    if len(sys.argv) < 2:
        print("Not enough arguments")
        sys.exit(-1)

    # check if target directory (argument) does exist and it is actually directory (not a file for example)
    if not os.path.isdir(sys.argv[1]):
        print("Argument is not a directory")
        sys.exit(-2)

    # instantiate (create) an object of class CDatContainer
    oc_dat_container = CDatContainer(sys.argv[1])
    # d_DAT dictionary is the data exchange interface for this class
    print(oc_dat_container.d_DAT)
#

