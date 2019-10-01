#!/usr/bin/env python3


import os
import sys
import hashlib
import configparser
import urllib.request


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


def download_file(s_src_URL, s_dst_path):
    print("INFO: download file...")
    with urllib.request.urlopen(s_src_URL) as oc_resp, open(s_dst_path, 'wb') as h_ofile:
        h_ofile.write(oc_resp.read())
    if os.path.isfile(s_dst_path):
        return True
    return False
#


def check_file(s_src_URL, s_dst_path):
    if os.path.isfile(s_dst_path):
        print("INFO: requested file found locally: %s" % s_dst_path)
        return True
    if not download_file(s_src_URL, s_dst_path):
        print("ERROR: unable to download file from URL: %s" % s_src_URL)
        return False
    return True
#


def calc_md5(s_fname):
    hash_md5 = hashlib.md5()
    with open(s_fname, "rb") as h_file:
        for chunk in iter(lambda: h_file.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
#


def check_dir(s_dst_dir):
    if not os.path.isdir(s_dst_dir):
        os.mkdir(s_dst_dir)
    if not os.path.isdir(s_dst_dir):
        raise IOError("Unable to create output directory: %s" % s_dst_dir)
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)

    s_work_dir = "output"
    check_dir(s_work_dir)

    # load global configuration file
    oc_global_cfg = configparser.ConfigParser()
    oc_global_cfg.read('v10n.ini')
    l_sections = oc_global_cfg.sections()

    for _, s_section in enumerate(l_sections):
        print("INFO: process section: %s" % s_section)
        check_dir(os.path.join(s_work_dir, s_section))

        s_origin = oc_global_cfg[s_section]['origin']
        s_src_URL = oc_global_cfg[s_section]['src_URL']
        s_src_md5 = oc_global_cfg[s_section]['src_md5']
        s_dst_file = oc_global_cfg[s_section]['dst_file']
        s_ini_file = oc_global_cfg[s_section]['ini_file']
        s_dst_path = os.path.join(s_work_dir, s_section, s_dst_file)

        print("INFO: src file: %s" % s_src_URL)
        print("INFO: dst file: %s" % s_dst_path)

        if not check_file(s_src_URL, s_dst_path):
            raise RuntimeError("unable to retrieve remote file")

        s_dst_md5 = calc_md5(s_dst_path)
        if s_src_md5 != s_dst_md5:
            raise RuntimeError("ERROR: md5sum mismatch: expected: %s retrieved: %s" % (s_src_md5, s_dst_md5))

        if not os.path.isfile(s_ini_file):
            raise RuntimeError("Unable to access ini file for CaFFlow: %s" % s_ini_file)

        print()
#
