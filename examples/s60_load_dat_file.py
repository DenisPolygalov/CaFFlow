#!/usr/bin/env python3


import os
import sys


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


def main():
    """
    Loads the .dat files
    (settings_and_notes.dat and timestamp.dat)
    then prints relevant information using classes
    and functions imported from mendouscopy.
    """
    # instantiate (create) an object of class CDatContainer
    oc_dat_container = CDatContainer(".")
    for s_key in oc_dat_container.d_DAT.keys():
        DVAR(oc_dat_container.d_DAT[s_key], s_var_name=s_key)
    # prints a sample of the frame information
    # (for the first 5 frames)
    for i in range(10):
        print(oc_dat_container.d_DAT['camNum'][i],
            oc_dat_container.d_DAT['frameNum'][i],
            oc_dat_container.d_DAT['sysClock'][i],
            oc_dat_container.d_DAT['buffer'][i]
        )
    #
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.debug import DVAR
    from mendouscopy.player import moshow
    from mendouscopy.datcontainer import CDatContainer
    main()
#

